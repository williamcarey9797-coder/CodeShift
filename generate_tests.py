from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from test_runner import run_junit_tests

load_dotenv()
model = ChatGroq(model="openai/gpt-oss-120b", temperature=0)

def generate_baseline_tests(repo_path: str, source_files: list[str]) -> bool:
    code_bundle = "\n\n".join(
        f"// File: {f}\n{Path(f).read_text(encoding='utf-8')}" for f in source_files
    )

    prompt = f"""Write a JUnit 5 test class named GeneratedBehaviorTest in package com.example.app.
Test the public methods of the Java classes below using @Test and assertEquals.
Return ONLY raw Java code. Do NOT include markdown backticks (```) or explanations.

{code_bundle}"""

    response = model.invoke(prompt)
    clean_test = response.content.replace("```java", "").replace("```", "").strip()

    test_file = Path(repo_path) / "src/test/java/com/example/app/GeneratedBehaviorTest.java"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(clean_test, encoding="utf-8")

    check = run_junit_tests(repo_path, offline=True)
    if not check["passed"]:
        print("AI generated:\n", clean_test)
        print("Failures:\n", check["failures"])
        test_file.unlink(missing_ok=True)
        return False
    return True

if __name__ == "__main__":
    print("Baseline test generated & verified:", generate_baseline_tests(
        "sample_repo",
        ["sample_repo/src/main/java/com/example/app/User.java"]
    ))
