import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
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


@app.get("/benchmark")
def get_benchmark():
    bench_file = Path("benchmark_results.json")
    if not bench_file.exists():
        raise HTTPException(status_code=404, detail="Benchmark results not found")
    return json.loads(bench_file.read_text(encoding="utf-8"))
