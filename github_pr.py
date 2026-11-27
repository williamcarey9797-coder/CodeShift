import os
import subprocess
import uuid
from dotenv import load_dotenv
from github import Github

load_dotenv()


def open_migration_pr(
    repo_full_name: str,
    local_repo_path: str,
    summary: str,
    tests_passed: bool,
    approved: bool = False,
) -> dict:
    if not tests_passed:
        return {"pr_created": False, "reason": "Blocked: JUnit 5 tests did not pass."}
    if not approved:
        return {"pr_created": False, "reason": "Blocked: Human approval required before opening PR."}

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {"pr_created": False, "reason": "Missing GITHUB_TOKEN in .env file."}

    run_id = uuid.uuid4().hex[:8]
    branch = f"codeshift/java-21-upgrade-{run_id}"
    subprocess.run(["git", "-C", local_repo_path, "checkout", "-b", branch], check=True)
    subprocess.run(["git", "-C", local_repo_path, "add", "."], check=True)
    subprocess.run(
        ["git", "-C", local_repo_path, "commit", "-m", "chore(codeshift): automated Java 8 to Java 21 migration"],
        check=True,
    )
    subprocess.run(["git", "-C", local_repo_path, "push", "-u", "origin", branch], check=True)

    gh = Github(token)
    repo = gh.get_repo(repo_full_name)
    pr = repo.create_pull(
        title=f"CodeShift: Automated Java 8 -> Java 21 Migration ({run_id})",
        body=summary,
        head=branch,
        base="main",
    )
    subprocess.run(["git", "-C", local_repo_path, "checkout", "main"], check=True)
    return {"pr_created": True, "pr_url": pr.html_url, "branch": branch}


if __name__ == "__main__":
    print(open_migration_pr(
        repo_full_name="williamcarey9797-coder/CodeShift",
        local_repo_path="sample_repo",
        summary="Automated Java 8 -> 21 migration verified via JUnit 5.",
        tests_passed=True,
        approved=False,
    ))
