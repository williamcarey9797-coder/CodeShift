from pathlib import Path
import docker

client = docker.from_env()
def run_maven_build(repo_path : str, java_version : int = 8, offline : bool = True) -> dict :
    
    abs_path = str(Path(repo_path).resolve())
    image = f"maven:3.9-eclipse-temurin-{java_version}"
    release_flag = f" -Dmaven.compiler.release={java_version}" if java_version >= 9 else ""
    maven_cmd = f"mvn -o test-compile{release_flag}" if offline else f"mvn test-compile{release_flag}"
    net_mode = "none" if offline else "bridge"

    container = client.containers.run(
        image = image,
        command = maven_cmd,
        volumes = {abs_path : {'bind': '/app','mode': 'rw'},'maven-cache':{'bind':'/root/.m2','mode':'rw'}},
        working_dir = '/app',
        mem_limit = '1536m',
        network_mode = net_mode,
        detach = True
    )

    try:
        result = container.wait()
        logs = container.logs(stdout = True,stderr= True).decode('utf-8')
        passed = result['StatusCode'] == 0
        errors = [line for line in logs.splitlines() if '[ERROR]' in line]
        return {'passed': passed,'java_version': java_version,'errors' : errors,'raw_logs': logs}

    finally : 
        container.remove(force = True)

if __name__ == '__main__':
    print(run_maven_build('sample_repo',java_version = 8,offline = True))
    print(run_maven_build('sample_repo',java_version = 21,offline = True))