from pathlib import Path 
import docker 

client = docker.from_env()
def run_junit_tests(repo_path : str, offline : bool = False) -> dict:
    
    abs_path = str(Path(repo_path).resolve())
    maven_cmd =  "mvn -o test" if offline else "mvn test"
    net_mode = "none" if offline else "bridge"

    container = client.containers.run(
        image="maven:3.9-eclipse-temurin-21", 
        command = maven_cmd,
        volumes={abs_path: {"bind": "/app", "mode": "rw"}, "maven-cache": {"bind": "/root/.m2", "mode": "rw"}}, 
        working_dir="/app", 
        mem_limit="1536m", 
        network_mode=net_mode, 
        detach=True
    )

    try: 
        result = container.wait()
        logs = container.logs(stdout = True,stderr = True).decode(encoding = 'utf-8')
        failures = [line for line in logs.splitlines() if '[ERROR]' in line or 'FAILURE' in line] 
        return {'passed': result['StatusCode'] == 0,'failures': failures,'raw_logs':logs}

    finally :
        container.remove(force = True)

if __name__ == "__main__":
    print(run_junit_tests("sample_repo", offline=False))

