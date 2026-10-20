# Ricochet Arena automation

Project: C:/Users/MSI/Documents/Unreal Projects/Rikoshet/Rikoshet.uproject
Engine: C:/Program Files/Epic Games/UE_5.8 (verified 5.8.2).
External automation Python: .venv/Scripts/python.exe (3.10.6).
Unreal scripts run using Unreal's own embedded Python, not the external venv.

## Commands (PowerShell, project root)

    python --version
    py --list-paths
    python -m venv .venv
    ./.venv/Scripts/python.exe -m pip install "mcp[cli]>=1.12,<2"
    ./.venv/Scripts/python.exe -m pip check
    ./.venv/Scripts/python.exe Tools/verify_mcp.py
    ./Tools/run_editor_script.ps1 -Action create
    ./Tools/run_editor_script.ps1 -Action verify

The create command refuses to overwrite an existing Blueprint.
The verification command loads the saved asset without editing it.
InstalledNoZenLocalFallback is an engine-supplied DDC profile used because the first
launch could not connect to local Zen. It applies only to the command invocation.
Missing platform SDK messages during startup do not imply this Blueprint editor
automation needs C++ tooling. Packaging has not been tested.

## MCP

Tools/ue_mcp.py uses FastMCP from official MCP Python SDK 1.x.
create_blueprint_script generates a cube Blueprint editor script; it never executes Unreal.
list_editor_scripts lists scripts and checks syntax.
Existing script files and assets are never overwritten automatically.
Tools/verify_mcp.py checks actual stdio initialization, discovery, tool calls,
invalid-name rejection and overwrite rejection.
Tools/requirements-lock.txt records installed versions.

.codex/config.toml uses absolute paths for this computer.
Restart the Codex extension/session and trust this project if prompted.
Then inspect the MCP tool list for ricochet_unreal.
Protocol smoke testing does not establish that the current Codex session hot-loaded
the configuration.

## Unreal evidence

/Game/RicochetArena/Blueprints/Test/BP_TestCube
is a Blueprint subclass of StaticMeshActor, which derives from Actor.
It contains the inherited static mesh component assigned Engine/BasicShapes/Cube.
No gameplay graph nodes were generated.
Saved/Automation/BP_TestCube.json records creation validation.
Saved/Automation/BP_TestCube_reload.json records fresh-process validation.
Logs: Saved/Logs/RicochetAutomation_NoZen.log and Saved/Logs/Ricochet_verify.log.
Backups of .uproject and .gitignore are in Saved/AutomationBackups/20261020_204631.

## Optional manual editor execution

Open Rikoshet.uproject in UE 5.8. In Tools > Execute Python Script choose
Tools/editor_scripts/verify_BP_TestCube.py to verify the existing Blueprint.
For a new asset only, choose create_BP_TestCube.py.
Alternatively use the Output Log's Python input:

    exec(open(r"C:/Users/MSI/Documents/Unreal Projects/Rikoshet/Tools/editor_scripts/verify_BP_TestCube.py", encoding="utf-8").read())

In the Content Browser navigate to /Game/RicochetArena/Blueprints/Test,
open BP_TestCube and drag it into a test level for optional visual inspection.
The full game architecture is planned in AGENTS.md; gameplay is not implemented.
