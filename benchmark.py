import json,shutil,time
from pathlib import Path
from deterministic import run_openrewrite
from verifier import run_maven_build 
from test_runner import run_junit_tests
from agent import workflow 

FILES = [
    "src/main/java/com/example/app/User.java",
    "src/main/java/com/example/app/OrderService.java",
    "src/main/java/com/example/app/OrderController.java",
]

def fresh_copy(base_repo: str, temp_name: str) -> Path:
    target = Path(temp_name)
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(base_repo, target)
    return target


def run_agent_on_folder(folder: Path) -> dict:
    return workflow.invoke({
        "repo_path": str(folder),
        "files_queue": [str(folder / f) for f in FILES],
        "current_file": "",
        "original_code": "",
        "errors": [],
        "retries": 0,
        "tokens_used": 0,
        "completed_files": [],
        "escalated_files": [],
    })



def run_benchmark(base_repo: str = "sample_repo") -> dict:
    results = {}

    # Strategy A: OpenRewrite-Only (0 LLM tokens)
    dir_a = fresh_copy(base_repo, "temp_bench_openrewrite")
    t0 = time.time()
    run_openrewrite(str(dir_a), offline=True)
    results["openrewrite_only"] = {
        "time_sec": round(time.time() - t0, 2),
        "tokens": 0,
        "build_passed": run_maven_build(str(dir_a), java_version=21, offline=True)["passed"],
        "tests_passed": run_junit_tests(str(dir_a), offline=True)["passed"],
        "escalated": 0,
    }
    shutil.rmtree(dir_a, ignore_errors=True)

    # Strategy B: LLM-Only (No OpenRewrite)
    dir_b = fresh_copy(base_repo, "temp_bench_llm")
    t0 = time.time()
    final_b = run_agent_on_folder(dir_b)
    results["llm_only"] = {
        "time_sec": round(time.time() - t0, 2),
        "tokens": final_b["tokens_used"],
        "build_passed": run_maven_build(str(dir_b), java_version=21, offline=True)["passed"],
        "tests_passed": run_junit_tests(str(dir_b), offline=True)["passed"],
        "escalated": len(final_b["escalated_files"]),
    }
    shutil.rmtree(dir_b, ignore_errors=True)

    # Strategy C: CodeShift Hybrid (OpenRewrite + LangGraph AI + JUnit 5)
    dir_c = fresh_copy(base_repo, "temp_bench_hybrid")
    t0 = time.time()
    run_openrewrite(str(dir_c), offline=True)
    if (
        run_maven_build(str(dir_c), java_version=21, offline=True)["passed"]
        and run_junit_tests(str(dir_c), offline=True)["passed"]
    ):
        final_c = {"tokens_used": 0, "escalated_files": []}
    else:
        final_c = run_agent_on_folder(dir_c)

    results["codeshift_hybrid"] = {
        "time_sec": round(time.time() - t0, 2),
        "tokens": final_c["tokens_used"],
        "build_passed": run_maven_build(str(dir_c), java_version=21, offline=True)["passed"],
        "tests_passed": run_junit_tests(str(dir_c), offline=True)["passed"],
        "escalated": len(final_c["escalated_files"]),
    }
    shutil.rmtree(dir_c, ignore_errors=True)

    Path("benchmark_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results

if __name__ == "__main__":
    print(json.dumps(run_benchmark(), indent=2))

    
