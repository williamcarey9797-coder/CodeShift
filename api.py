import json
from pathlib import Path
import difflib
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse,StreamingResponse
from github_pr import open_migration_pr
from pydantic import BaseModel
from deterministic import run_openrewrite
from verifier import run_maven_build
from test_runner import run_junit_tests
from agent import workflow


app = FastAPI(title="CodeShift API")


class MigrateRequest(BaseModel):
    repo_path: str = "sample_repo"


def validate_repo(repo_path: str) -> Path:
    target = Path(repo_path).resolve()
    if not target.exists() or not target.is_relative_to(Path.cwd().resolve()):
        raise HTTPException(status_code=400, detail="Invalid or unauthorized repository path")
    return target


@app.post("/migrate")
def migrate_repo(req: MigrateRequest):
    repo = validate_repo(req.repo_path)
    run_openrewrite(str(repo), offline=True)
    build_check = run_maven_build(str(repo), java_version=21, offline=True)

    if build_check["passed"]:
        tokens_used = 0
        escalated = []
    else:
        all_java = [str(p) for p in (repo / "src/main").rglob("*.java")]
        error_log = "\n".join(build_check["errors"])
        broken = [f for f in all_java if Path(f).name in error_log]
        final_state = workflow.invoke({
            "repo_path": str(repo),
            "files_queue": broken or all_java,
            "current_file": "",
            "original_code": "",
            "errors": [],
            "retries": 0,
            "tokens_used": 0,
            "completed_files": [],
            "escalated_files": [],
        })
        tokens_used = final_state["tokens_used"]
        escalated = final_state["escalated_files"]

    tests_passed = run_junit_tests(str(repo), offline=True)["passed"]
    return {
        "repo_path": req.repo_path,
        "tokens_used": tokens_used,
        "escalated_files": escalated,
        "tests_passed": tests_passed,
    }

@app.get("/migrate-stream")
def migrate_stream(repo_path: str = "sample_repo"):
    repo = validate_repo(repo_path)

    def event_stream():
        all_java = [p for p in (repo / "src/main").rglob("*.java")]
        before_snapshots = {str(p): p.read_text(encoding="utf-8") for p in all_java}

        yield f"data: {json.dumps({'step': 1, 'status': 'active', 'msg': 'Running OpenRewrite AST recipes in Docker...'})}\n\n"
        run_openrewrite(str(repo), offline=True)
        yield f"data: {json.dumps({'step': 1, 'status': 'done', 'msg': 'OpenRewrite AST pass complete (0 tokens)'})}\n\n"

        yield f"data: {json.dumps({'step': 2, 'status': 'active', 'msg': 'Compiling with JDK 21 to isolate residual failures...'})}\n\n"
        build_check = run_maven_build(str(repo), java_version=21, offline=True)
        error_log = "\n".join(build_check["errors"])
        broken = [str(p) for p in all_java if p.name in error_log]
        yield f"data: {json.dumps({'step': 2, 'status': 'done', 'msg': f'Isolated {len(broken)} residual file(s): {[Path(b).name for b in broken]}'})}\n\n"

        yield f"data: {json.dumps({'step': 3, 'status': 'active', 'msg': 'Running bounded LangGraph AI repair loop...'})}\n\n"
        if build_check["passed"]:
            tokens_used, escalated = 0, []
        else:
            final_state = workflow.invoke({
                "repo_path": str(repo),
                "files_queue": broken or [str(p) for p in all_java],
                "current_file": "",
                "original_code": "",
                "errors": [],
                "retries": 0,
                "tokens_used": 0,
                "completed_files": [],
                "escalated_files": [],
            })
            tokens_used = final_state["tokens_used"]
            escalated = final_state["escalated_files"]
        yield f"data: {json.dumps({'step': 3, 'status': 'done', 'msg': f'AI repair complete ({tokens_used} tokens, {len(escalated)} escalated)'})}\n\n"

        yield f"data: {json.dumps({'step': 4, 'status': 'active', 'msg': 'Executing JUnit 5 behavioral test suite in Docker...'})}\n\n"
        tests_passed = run_junit_tests(str(repo), offline=True)["passed"]
        yield f"data: {json.dumps({'step': 4, 'status': 'done', 'msg': 'JUnit 5 verification passed' if tests_passed else 'JUnit 5 verification failed'})}\n\n"

        diffs = []
        for p in all_java:
            after = p.read_text(encoding="utf-8")
            before = before_snapshots[str(p)]
            if before != after:
                diff_text = "".join(difflib.unified_diff(
                    before.splitlines(True), after.splitlines(True),
                    fromfile=f"java8/{p.name}", tofile=f"java21/{p.name}"
                ))
                diffs.append({"file": p.name, "diff": diff_text})

        receipt = {
            "done": True,
            "repo_path": repo_path,
            "tokens_used": tokens_used,
            "escalated_files": escalated,
            "tests_passed": tests_passed,
            "files_scanned": len(all_java),
            "ai_repaired_files": [Path(b).name for b in broken],
            "diffs": diffs,
        }
        yield f"data: {json.dumps(receipt)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/benchmark")
def get_benchmark():
    bench_file = Path("benchmark_results.json")
    if not bench_file.exists():
        raise HTTPException(status_code=404, detail="Benchmark results not found")
    return json.loads(bench_file.read_text(encoding="utf-8"))

class PRRequest(BaseModel):
    repo_full_name: str
    local_repo_path: str = "sample_repo"
    summary: str
    tests_passed: bool
    approved: bool = False


@app.get("/", response_class=HTMLResponse)
def serve_ui():
    return Path("index.html").read_text(encoding="utf-8")


@app.post("/pr")
def create_pr(req: PRRequest):
    validate_repo(req.local_repo_path)
    return open_migration_pr(
        repo_full_name=req.repo_full_name,
        local_repo_path=req.local_repo_path,
        summary=req.summary,
        tests_passed=req.tests_passed,
        approved=req.approved,
    )

