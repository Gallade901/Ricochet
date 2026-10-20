"""Project-local MCP: generate editor scripts, never execute Unreal implicitly."""
from pathlib import Path
import ast
import re
from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "Tools" / "editor_scripts"
mcp = FastMCP("RicochetArena")

@mcp.tool()
def create_blueprint_script(blueprint_name: str = "BP_TestCube",
                            package_path: str = "/Game/RicochetArena/Blueprints/Test") -> dict:
    """Write a new Unreal Python script for a cube Blueprint Actor. Does not run the editor or create graphs. Existing scripts are never overwritten."""
    if not re.fullmatch(r"BP_[A-Za-z][A-Za-z0-9_]*", blueprint_name):
        raise ValueError("Expected BP_ followed by an ASCII identifier")
    if not re.fullmatch(r"/Game/RicochetArena(?:/[A-Za-z][A-Za-z0-9_]*)*", package_path):
        raise ValueError("Package must be inside /Game/RicochetArena")
    source = (ROOT / "Tools" / "blueprint_template.py.txt").read_text(encoding="utf-8")
    source = source.replace("__BLUEPRINT_NAME__", blueprint_name).replace("__PACKAGE_PATH__", package_path)
    ast.parse(source)
    SCRIPTS.mkdir(parents=True, exist_ok=True)
    destination = SCRIPTS / ("create_" + blueprint_name + ".py")
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(source)
    return {"script": str(destination), "syntax_valid": True, "editor_executed": False}

@mcp.tool()
def list_editor_scripts() -> list[dict]:
    """List project editor Python scripts and their syntax status; does not execute them."""
    result = []
    for path in sorted(SCRIPTS.glob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"))
            status = "valid"
        except SyntaxError as error:
            status = str(error)
        result.append({"name": path.name, "path": str(path), "syntax": status})
    return result

if __name__ == "__main__":
    mcp.run(transport="stdio")
