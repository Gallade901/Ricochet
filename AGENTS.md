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

## Implemented core mechanics
- Runtime Blueprints: /Game/RicochetArena/CoreMechanics. See Tools/CORE_MECHANICS.md.
- Player: WASD via CharacterMovement, mouse aim, held-LMB fire, Microchips balance.
- Projectile: swept sphere, planar ProjectileMovement, no gravity, 6s lifespan, max 8 ricochets.
- Only RicochetWall-tagged actors enable HasRicocheted. GetRobotDamage returns zero until then.
- Microchip: automatic player overlap, Collected guard, per-instance Value.
- HUD displays controls and resources; GameMode assigns player, controller and HUD.
- Lvl_RicochetPrototype is the default playable map. Original TopDown assets preserved.
- Lvl_CoreAutomation and BP_RA_CoreRuntimeTest are tests; the test map quits automatically.
- Test robot health, ricochet-gated damage and death are implemented. Chip drops, waves and upgrades remain pending.

## Core automation safeguards
- build_core_mechanics.py uses Epic EditorToolset and official BlueprintGraphEditor APIs.
- EditorToolset is enabled only by automation command line. Runtime is Blueprint only.
- Authoring scripts refuse to overwrite saved assets; do not rerun against existing assets.
- Tools/test_core_runtime.ps1 repeats actual gameplay checks.
- Evidence: Saved/Automation/CoreMechanics and Saved/Logs/CoreRuntime.log.
- Back up existing assets before modifications, compile graphs and run relevant checks.

## Implemented test robot
- /Game/RicochetArena/Robot/BP_RA_TestRobot is placed once in Lvl_RicochetPrototype at (-350,250,85).
- Stationary primitive robot model, MaxHealth 100, CurrentHealth, IsDead and screen-space WBP_RA_RobotHealth.
- The robot is a WorldDynamic Actor with blocking collision, not a Pawn ignored by projectiles.
- Projectile RegisterWallHit retains wall bounce logic and applies damage to RicochetRobot-tagged actors only after GetRobotDamage > 0.
- Robot ReceiveAnyDamage independently checks the projectile source and ricochet state; clamps damage and health; ignores hits after death.
- ImpactConsumed prevents repeat damage per projectile impact. Default damage is 25 (four bounced hits to kill).
- Die disables collision, calls HandleRobotDestroyed, and removes the actor after one second.
- ChipDropValue is reserved for future drops; no chip drop is implemented.
- Tools/test_robot_runtime.ps1 repeats 13 gameplay checks. Existing 12 core gameplay checks also pass.
- Robot authoring requires built-in EditorToolset and UMGToolSet only during automation; no runtime Python dependency.
- Robot build/placement scripts back up existing projectile and map files before editor-based modification.
- Evidence: Saved/Automation/Robot and Saved/Logs/RobotRuntime.log; usage: Tools/TEST_ROBOT.md.
