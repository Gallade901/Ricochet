"""Place the saved test robot on the backed-up arena and inspect saved graphs."""
import datetime
import json
import shutil
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as B

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = ROOT / 'Saved/Automation/Robot'
OUT.mkdir(parents=True, exist_ok=True)
robot_path = '/Game/RicochetArena/Robot/BP_RA_TestRobot'
arena = '/Game/RicochetArena/CoreMechanics/Lvl_RicochetPrototype'
robot = unreal.load_asset(robot_path)
assert isinstance(robot, unreal.Blueprint)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert levels.load_level(arena)
worlds = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert worlds.get_editor_world().get_path_name() == arena + '.Lvl_RicochetPrototype'
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
placed = [a for a in actors.get_all_level_actors()
          if unreal.MathLibrary.class_is_child_of(a.get_class(), robot.generated_class())]
if not placed:
    backup = ROOT / 'Saved/AutomationBackups' / ('RobotPlacement_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    backup.mkdir(parents=True)
    shutil.copy2(ROOT / 'Content/RicochetArena/CoreMechanics/Lvl_RicochetPrototype.umap', backup)
    instance = actors.spawn_actor_from_class(robot.generated_class(), unreal.Vector(-350, 250, 85))
    instance.set_actor_label('TestRobot_RicochetOnly_100HP')
    assert worlds.get_editor_world().get_path_name() == arena + '.Lvl_RicochetPrototype'
    assert levels.save_current_level()
    placed = [instance]
assert len(placed) == 1
report = {'engine': unreal.SystemLibrary.get_engine_version(), 'prototype_robot_count': len(placed),
          'prototype_robot_location': str(placed[0].get_actor_location()), 'blueprints': {}}
for path in [robot_path, '/Game/RicochetArena/Robot/WBP_RA_RobotHealth',
             '/Game/RicochetArena/CoreMechanics/BP_RA_RicochetProjectile']:
    bp = unreal.load_asset(path)
    assert isinstance(bp, unreal.Blueprint)
    assert bp.get_editor_property('status') == unreal.BlueprintStatus.BS_UP_TO_DATE
    graphs = {}
    for graph in B.list_graphs(bp):
        editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
        assert not editor.list_nodes_with_errors()
        graphs[graph.get_name()] = len(editor.list_all_nodes())
        (OUT / (bp.get_name() + '_' + graph.get_name() + '_verified.sexpr')).write_text(B.read_graph_dsl(graph), encoding='utf-8')
    report['blueprints'][bp.get_name()] = {'status': str(bp.get_editor_property('status')), 'graphs': graphs}
(OUT / 'fresh_load_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('ROBOT_PLACEMENT_AND_FRESH_LOAD_VERIFIED')
