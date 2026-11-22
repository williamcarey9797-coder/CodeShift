from pathlib import Path
import docker

client = docker.from_env()
repo_path = str(Path("sample_repo").resolve())

container = client.containers.run(
    image="maven:3.9-eclipse-temurin-8",
    command="mvn test-compile",
    volumes={
    repo_path: {"bind": "/app", "mode": "rw"},
    "maven-cache": {"bind": "/root/.m2", "mode": "rw"},
},
    working_dir="/app",
    mem_limit="1536m",
    detach=True
)

try:
    result = container.wait()
    logs = container.logs(stdout=True, stderr=True).decode("utf-8")
    if result["StatusCode"] == 0:
        print("BUILD SUCCESS!")
    else:
        print("BUILD FAILED!")
    print(logs)
finally:
    container.remove(force=True)
