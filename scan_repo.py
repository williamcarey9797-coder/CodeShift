from pathlib import Path
import tree_sitter_java
from tree_sitter import Language,Parser
import networkx as nx
import re

java_language = Language(tree_sitter_java.language())
parser = Parser(java_language)

def scan_java_file(file_path : Path) -> dict:

    package_name = ""
    class_name = ""
    imports_list = []

    java_bytes = file_path.read_bytes()
    tree = parser.parse(java_bytes)

    for node in tree.root_node.children :
        if node.type == "package_declaration":
            package_name = java_bytes[node.start_byte:node.end_byte].decode('utf-8').replace("package","").replace(";","").strip()
            #print(node.type, '-->', package_name)

        elif node.type == "import_declaration":
            clean_import = java_bytes[node.start_byte:node.end_byte].decode('utf-8').replace("import","").replace(";","").strip()
            imports_list.append(clean_import)
           # print(node.type,'-->', imports_list)
        elif node.type in("class_declaration","interface_declaration",
                          "enum_declaration","record_declaration"):
            name_node = node.child_by_field_name('name')
            if name_node:
                class_name = java_bytes[name_node.start_byte:name_node.end_byte].decode('utf-8').replace("import","").replace(";","").strip()
               # print(node.type,'-->',class_name)
    return {'file_path' : str(file_path),'package' : package_name,'imports': imports_list,'class_name':class_name}

scanned_rooms = []

for java_file in Path("sample_repo").rglob('*.java'):
    room_data = scan_java_file(java_file)
    scanned_rooms.append(room_data)

#print(scanned_rooms)    

internal_classes = {}

for room in scanned_rooms:
    key = f"{room['package']}.{room['class_name']}"
    value = room['file_path']
    internal_classes[key] = value

for room in scanned_rooms:

    valid_deps = []
    
    for imp in room['imports']:
        if imp in internal_classes:
            valid_deps.append(imp)


    file_text = Path(room['file_path']).read_text(encoding='utf-8')
    for other_room in scanned_rooms:
        if other_room['package'] == room['package'] and other_room['class_name'] != room['class_name']:
            if re.search(rf"\b{other_room['class_name']}\b", file_text):
                full_other = f"{other_room['package']}.{other_room['class_name']}"
                if full_other not in valid_deps:
                    valid_deps.append(full_other)


    room['internal_deps'] = valid_deps        

    print(room['class_name'])
    print(room['internal_deps'])

graph = nx.DiGraph()

for room in scanned_rooms:
    full_name = f"{room['package']}.{room['class_name']}"
    graph.add_node(full_name)

    for dep in room['internal_deps']:
        graph.add_edge(dep,full_name)

clean_graph = nx.condensation(graph)

upgrade_groups = []
for group_number in nx.topological_sort(clean_graph):
    files_in_group = sorted(list(clean_graph.nodes[group_number]["members"]))
    upgrade_groups.append(files_in_group)

print("Safe Upgrade Order:", upgrade_groups)




