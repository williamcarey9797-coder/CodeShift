# 1. Grab the Master Keychain to read files cleanly
from pathlib import Path

# 2. Grab the X-Ray Scanner (Parser) and Java Wiring Manual (tree_sitter_java)
import tree_sitter_java
from tree_sitter import Language, Parser

# 3. Load the Java manual into the scanner
java_language = Language(tree_sitter_java.language())
parser = Parser(java_language)

# 4. Read Sample.java as raw bytes and scan it into a Syntax Tree
java_bytes = Path("Sample.java").read_bytes()
tree = parser.parse(java_bytes)

# 5. Print only the Room Label (package) and Electrical Wires (imports)
for node in tree.root_node.children:
    if node.type in ("package_declaration", "import_declaration"):
        text = java_bytes[node.start_byte:node.end_byte].decode("utf-8")
        print(node.type, "-->", text)
