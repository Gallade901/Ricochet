# Ricochet Arena

## Technical rules
- Unreal Engine 5.8 only. Runtime gameplay exclusively in Blueprints.
- No project C++ and no third-party C++ plugins. Built-in Unreal editor plugins are permitted.
- Python is editor automation and MCP infrastructure only, never runtime gameplay.
- Prefer official Unreal Python APIs. Never edit binary .uasset files directly.
- Before destructive changes or modification of existing assets/configuration, create a backup or Git commit.
- Do not overwrite existing assets automatically. Preserve user changes.
- A generated Python file is not a created Blueprint. Verify execution, saved asset, generated class, component data and editor errors.
- Do not claim Blueprint graphs exist unless inspected/verified in the editor.
- Do not implement the full game until automation works and the first test Blueprint is created.

## Planned Blueprint architecture (not implemented)
Content root: /Game/RicochetArena.
- Core/BP_RA_GameMode: run state; victory after five completed waves; defeat on player death.
- Core/BP_WaveManager: wave index 1..5, spawn budget, living enemy count, rising difficulty.
- Player/BP_PlayerCharacter and BP_PlayerController: top-down movement and aim.
- Enemies/BP_Robot: health, AI, damage, chip drop on destruction.
- Weapons/BP_Weapon and Projectiles/BP_RicochetProjectile: firing and projectile movement.
- Projectile starts with HasRicocheted=false; qualifying wall hit sets true. Robot damage only when true.
- Arena/BP_RicochetWall: identifies surfaces eligible for ricochet.
- Pickups/BP_Microchip: collectible upgrade currency.
- Upgrades/BP_UpgradeTerminal: spend chips on weapon upgrades.
- UI: health, chips, wave number, win/lose state.
- Interfaces/components: damage interface; health and weapon stats components as needed.
Setting: abandoned science-fiction experimental ricochet weapons test arena.

## Automation
- MCP entry: Tools/ue_mcp.py, stdio, project .venv Python.
- create_blueprint_script writes scripts only; list_editor_scripts lists and parses them.
- Scripts live in Tools/editor_scripts; inspect before running in Unreal Editor.
- Test Blueprint uses StaticMeshActor (Actor subclass) and engine Cube mesh, no gameplay graph.
- Run Tools/verify_mcp.py for real stdio initialization, tool discovery and calls.
- Unreal verification evidence: Saved/Automation/BP_TestCube.json plus editor log.
- .codex/config.toml contains machine-specific absolute paths. Restart Codex after configuration.
