from pathlib import Path
import docker

client = docker.from_env()

def run_openrewrite(repo_path : str , offline : bool = False):

    abs_path = str(Path(repo_path).resolve())
    offline_flag = '-o ' if offline else '-U '
    rewrite_cmd = (
         f"mvn {offline_flag}org.openrewrite.maven:rewrite-maven-plugin:run "
    "-Drewrite.recipeArtifactCoordinates=org.openrewrite.recipe:rewrite-migrate-java:RELEASE "
    "-Drewrite.activeRecipes=org.openrewrite.java.migrate.UpgradeToJava21"
    )
    net_mode = 'none' if offline else 'bridge'

    container = client.containers.run(
        image = f'maven:3.9-eclipse-temurin-21',
        command = rewrite_cmd,
        volumes = {abs_path : {'bind': '/app','mode':'rw',},'maven-cache': {'bind': '/root/.m2','mode':'rw'}},
        working_dir = '/app',
        mem_limit = '1536m',
        network_mode = net_mode,
        detach = True
    )

    try:
        result = container.wait()
        logs = container.logs(stdout = True,stderr = True).decode('utf-8')
        return {'passed' : result['StatusCode'] == 0,'raw_logs': logs}

    finally:
        container.remove(force = True)       

if __name__ == '__main__':
    print(run_openrewrite('sample_repo',offline = True))         
    