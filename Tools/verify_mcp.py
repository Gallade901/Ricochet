"""Exercise the actual MCP stdio server, including both tools."""
import asyncio
import ast
import json
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]

async def main():
    params = StdioServerParameters(command=sys.executable,
                                   args=[str(ROOT / "Tools/ue_mcp.py")], cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {tool.name for tool in (await session.list_tools()).tools}
            assert names == {"create_blueprint_script", "list_editor_scripts"}, names
            target = ROOT / "Tools/editor_scripts/create_BP_TestCube.py"
            if not target.exists():
                response = await session.call_tool("create_blueprint_script", {})
                assert not response.isError, response
            response = await session.call_tool("list_editor_scripts", {})
            assert not response.isError, response
            ast.parse(target.read_text(encoding="utf-8"))
            # Invalid paths must be rejected without creating a file.
            invalid = await session.call_tool("create_blueprint_script", {"blueprint_name": "../escape"})
            assert invalid.isError
            duplicate = await session.call_tool("create_blueprint_script", {})
            assert duplicate.isError
            print(json.dumps({"initialize": "passed", "tools": sorted(names),
                              "list_call": "passed", "script_syntax": "passed",
                              "invalid_name_rejected": True, "overwrite_rejected": True}))
if __name__ == "__main__":
    asyncio.run(main())
