from pathlib import Path
from typing import TypedDict,List
from langgraph.graph import StateGraph,START,END
from langchain_groq import ChatGroq
from verifier import run_maven_build
from dotenv import load_dotenv

load_dotenv()
# temperature = 0 --> the AI's creativity slider to zero so it follows strict Java syntax rules and keeps your exact class/method names instead of inventing random code.
model = ChatGroq(model="openai/gpt-oss-120b", temperature=0)

class MigrationState(TypedDict):

    repo_path : str
    files_queue : List[str]
    current_file : str
    original_code : str
    errors : List[str]
    retries : int
    tokens_used : int
    completed_files : List[str]
    escalated_files : List[str]

def migrate_file_node(state : MigrationState) -> MigrationState:

    file_path = state['files_queue'][0]
    print(f"Trying {file_path} (retry #{state['retries']})...")
    code = Path(file_path).read_text(encoding = 'utf-8')
    backup = code if state['retries'] == 0 else state['original_code']

    if not state["errors"]:
        prompt = f"""Upgrade this Java 8 code to modern Java 21.
        Keep the exact same package name, class name, and method names so other files do not break.
        Return ONLY the raw Java code. Do NOT include markdown backticks (```) or explanations.

        {code}"""
    else:
        prompt = f"""Your previous Java 21 upgrade failed to compile with these errors:
        {state["errors"]}

        Fix those errors in the Java code below and return ONLY the raw Java code.
        Do NOT include markdown backticks (```) or explanations.

        {code}"""

    try:
        response = model.invoke(prompt)
        used = response.usage_metadata.get('total_tokens', 0) if response.usage_metadata else 0
        clean_code = response.content.split("</think>")[-1].replace("```java", "").replace("```", "").strip()
        Path(file_path).write_text(clean_code, encoding='utf-8')
    except Exception as e:
        print(f"API error on {file_path}: {e}")
        used = 0


    return {'current_file':file_path,'original_code' : backup,'tokens_used': state['tokens_used'] + used}

def verify_build_node(state : MigrationState) -> MigrationState:

    build = run_maven_build(state['repo_path'],java_version = 21, offline = True)
    if build["passed"]:
        return {
        "completed_files": state["completed_files"] + [state["current_file"]],
        "files_queue": state["files_queue"][1:],
        "errors": [],
        "retries": 0,
    }
    else:
        next_retries = state["retries"] + 1
        if next_retries >= 3:
            print(f"3 strikes reached! Rolling back {state['current_file']} and escalating.")
            Path(state["current_file"]).write_text(state["original_code"], encoding="utf-8")
            return {
            "escalated_files": state["escalated_files"] + [state["current_file"]],
            "files_queue": state["files_queue"][1:],
            "errors": [],
            "retries": 0,
        }
        return {
            "errors": build["errors"],
            "retries": next_retries,
    }

def route_next_step(state : MigrationState) -> MigrationState:

    if len(state['files_queue']) > 0 :
        return 'migrate_file_node'
    return END

graph = StateGraph(MigrationState)

graph.add_node('migrate_file_node',migrate_file_node)
graph.add_node('verify_build_node',verify_build_node)

graph.add_edge(START,'migrate_file_node')
graph.add_edge('migrate_file_node','verify_build_node')
graph.add_conditional_edges('verify_build_node',route_next_step)

workflow = graph.compile()

if __name__ == '__main__':
    initial_state : MigrationState = {
        "repo_path": "sample_repo",
        "files_queue": [
            "sample_repo/src/main/java/com/example/app/User.java",
            "sample_repo/src/main/java/com/example/app/OrderService.java",
            "sample_repo/src/main/java/com/example/app/OrderController.java",
        ],
        'current_file' : "",
        'original_code' : "",
        'errors' : [],
        'retries' : 0,
        'tokens_used' : 0,
        'completed_files' : [],
        'escalated_files' : []
    }
    final_state = workflow.invoke(initial_state)
    print('Completed:', final_state['completed_files'])
    print('Escalated:',final_state['escalated_files'])
    print('Tokens used:',final_state['tokens_used'])

    
    


