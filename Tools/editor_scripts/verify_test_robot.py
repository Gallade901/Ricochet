"""Fresh-load checks and separate Blueprint-only robot collision regression map."""
import json
import sys
from pathlib import Path
import unreal
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_core_mechanics as core
from build_core_mechanics import B, cdo, var, function, node, getter, setter, write
from build_test_robot import member

GAME = '/Game/RicochetArena/CoreMechanics'
BASE = '/Game/RicochetArena/Robot'
OUT = Path(unreal.Paths.project_saved_dir()) / 'Automation/Robot'
OUT.mkdir(parents=True, exist_ok=True)
core.BASE = BASE
core.OUT = OUT
for path in [GAME + '/BP_RA_RicochetProjectile', GAME + '/BP_RA_RicochetWall',
             GAME + '/BP_RA_GameMode', BASE + '/BP_RA_TestRobot', BASE + '/WBP_RA_RobotHealth']:
    bp = unreal.load_asset(path)
    assert isinstance(bp, unreal.Blueprint), path
    core.ASSETS[bp.get_name()] = bp
    assert bp.get_editor_property('status') == unreal.BlueprintStatus.BS_UP_TO_DATE
    for graph in B.list_graphs(bp):
        assert not unreal.BlueprintGraphEditor.get_graph_editor(graph).list_nodes_with_errors()
robot = core.ASSETS['BP_RA_TestRobot']
widget = core.ASSETS['WBP_RA_RobotHealth']
projectile = core.ASSETS['BP_RA_RicochetProjectile']
wall = core.ASSETS['BP_RA_RicochetWall']
assert cdo(robot).get_editor_property('MaxHealth') == 100.0
assert cdo(projectile).get_editor_property('Damage') == 25.0
assert not cdo(projectile).get_editor_property('HasRicocheted')

harness_exists = unreal.EditorAssetLibrary.does_asset_exist(BASE + '/BP_RA_RobotRuntimeTest')
harness_map_exists = unreal.EditorAssetLibrary.does_asset_exist(BASE + '/Lvl_RobotAutomation')
assert harness_exists == harness_map_exists, 'Partial test harness: inspect before rebuilding'
if not harness_exists:
    test = core.make('BP_RA_RobotRuntimeTest', unreal.Actor)
    for name, kind, default in [('AllPassed', 'bool', True), ('Finished', 'bool', False), ('Elapsed', 'float', 0.0)]:
        var(test, name, kind, default)
    for name in ['DirectTarget', 'BounceTarget']:
        B.add_object_variable(test, name, robot.generated_class())
    check = function(test, 'RobotCheck', [('Condition', 'bool'), ('Label', 'string')])
    start = function(test, 'StartRobotTest')
    finish = function(test, 'FinishRobotTest')
    B.compile_blueprint(test)

    def call(g, name, **args):
        return '(' + node(g, name) + ' ' + ' '.join(':' + k + ' ' + v for k, v in args.items()) + ')'

    def assertion(g, condition, label):
        return call(g, 'RobotCheck', Condition=condition, Label='"ROBOT_TEST_PASS ' + label + '"')

    def get(g, name, target):
        return call(g, 'Get' + name, self=target)

    def spawn(g, cls, x, y, z):
        return call(g, 'SpawnActorfromClass', Class='"' + cls.generated_class().get_path_name() + '"',
                    SpawnTransform=call(g, 'MakeTransform', Location=call(g, 'MakeVector', X=str(x), Y=str(y), Z=str(z))),
                    CollisionHandlingOverride='"AlwaysSpawn"')

    write(check, f'''(fn RobotCheck (Condition Label)
      (if Condition
        ({node(check, 'PrintString')} :InString Label :bPrintToLog true)
        (else
          {setter(check, 'AllPassed', 'false')}
          ({node(check, 'PrintString')} :InString "ROBOT_TEST_FAIL" :bPrintToLog true)
          ({node(check, 'PrintString')} :InString Label :bPrintToLog true))))''')
    write(start, f'''(fn StartRobotTest ()
      (bind direct {spawn(start, robot, 600, -600, 85)})
      (bind bounced {spawn(start, robot, 1100, 600, 85)})
      {setter(start, 'DirectTarget', 'direct')}
      {setter(start, 'BounceTarget', 'bounced')}
      {assertion(start, '(== ' + get(start, 'CurrentHealth', 'direct') + ' 100.0)', 'starts_at_100_hp')}
      {call(start, 'ReceiveProjectileDamage', self='direct', IncomingDamage='999.0', Source='self')}
      {assertion(start, '(== ' + get(start, 'CurrentHealth', 'direct') + ' 100.0)', 'rejects_non_projectile_source')}
      (bind directBullet {spawn(start, projectile, 0, -600, 96)})
      (bind bounceBullet {spawn(start, projectile, 1200, 600, 96)}))''')

    write(finish, f'''(fn FinishRobotTest ()
      (bind direct {getter(finish, 'DirectTarget')})
      (bind bounced {getter(finish, 'BounceTarget')})
      {assertion(finish, '(== ' + get(finish, 'CurrentHealth', 'direct') + ' 100.0)', 'physical_direct_hit_no_damage')}
      {assertion(finish, '(== ' + get(finish, 'CurrentHealth', 'bounced') + ' 75.0)', 'physical_ricochet_hit_deals_25')}
      {assertion(finish, '(== ' + get(finish, 'LastDamage', 'bounced') + ' 25.0)', 'no_duplicate_impact_damage')}
      {assertion(finish, '(== ' + get(finish, 'HealthFraction', 'bounced') + ' 0.75)', 'health_fraction_updates')}
      (bind directProxy {spawn(finish, projectile, -1000, 1600, 96)})
      {call(finish, 'ReceiveProjectileDamage', self='bounced', IncomingDamage='999.0', Source='directProxy')}
      {assertion(finish, '(== ' + get(finish, 'CurrentHealth', 'bounced') + ' 75.0)', 'receiver_rejects_unbounced_projectile')}
      (bind widgetObject ({node(finish, 'GetUserWidgetObject')} :self ({member(robot, 'HealthBar')[1:-1]} :self bounced)))
      (bind hpWidget ({node(finish, 'CastToWBP_RA_RobotHealth')} :Object widgetObject)
        (:then
          {assertion(finish, '(== ' + get(finish, 'DisplayPercent', 'hpWidget') + ' 0.75)', 'umg_bar_shows_75_percent')}
          ({node(finish, 'SetHasRicocheted')} :self directProxy :HasRicocheted true)
          {call(finish, 'ReceiveProjectileDamage', self='bounced', IncomingDamage='999.0', Source='directProxy')}
          {assertion(finish, '(== ' + get(finish, 'CurrentHealth', 'bounced') + ' 50.0)', 'damage_capped_to_projectile_damage')}
          {call(finish, 'ReceiveProjectileDamage', self='bounced', IncomingDamage='25.0', Source='directProxy')}
          {call(finish, 'ReceiveProjectileDamage', self='bounced', IncomingDamage='25.0', Source='directProxy')}
          {assertion(finish, '(== ' + get(finish, 'CurrentHealth', 'bounced') + ' 0.0)', 'health_reaches_zero')}
          {assertion(finish, get(finish, 'IsDead', 'bounced'), 'death_state_set')}
          {assertion(finish, '(== ' + get(finish, 'DisplayPercent', 'hpWidget') + ' 0.0)', 'umg_bar_empty_at_death')}
          {call(finish, 'ReceiveProjectileDamage', self='bounced', IncomingDamage='25.0', Source='directProxy')}
          {assertion(finish, '(== ' + get(finish, 'CurrentHealth', 'bounced') + ' 0.0)', 'dead_robot_ignores_more_damage')}
          (if {getter(finish, 'AllPassed')}
            ({node(finish, 'PrintString')} :InString "ROBOT_RUNTIME_VERIFIED" :bPrintToLog true)
            (else ({node(finish, 'PrintString')} :InString "ROBOT_RUNTIME_FAILED" :bPrintToLog true)))
          ({node(finish, 'QuitGame')} :QuitPreference "Quit" :bIgnorePlatformRestrictions true))
        (:CastFailed
          ({node(finish, 'PrintString')} :InString "ROBOT_TEST_FAIL health_widget_missing" :bPrintToLog true)
          ({node(finish, 'QuitGame')} :QuitPreference "Quit" :bIgnorePlatformRestrictions true))))''')
    B.compile_blueprint(test)
    events = B.get_graph(test, 'EventGraph')
    write(events, f'''(event EventBeginPlay ({node(events, 'StartRobotTest')}))
      (event EventTick (DeltaSeconds)
        (if (not {getter(events, 'Finished')})
          {setter(events, 'Elapsed', '(+ ' + getter(events, 'Elapsed') + ' DeltaSeconds)')}
          (if (>= {getter(events, 'Elapsed')} 0.9)
            {setter(events, 'Finished', 'true')}
            ({node(events, 'FinishRobotTest')}))))''')
    B.compile_blueprint(test, warnings_as_errors=True)
    assert unreal.EditorAssetLibrary.save_loaded_asset(test, False)

    # New isolated level only; never modify or save the user's currently active map.
    level_path = BASE + '/Lvl_RobotAutomation'
    assert not unreal.EditorAssetLibrary.does_asset_exist(level_path)
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    assert levels.new_level(level_path)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert world.get_path_name() == level_path + '.Lvl_RobotAutomation'
    world.get_world_settings().set_editor_property('default_game_mode', core.ASSETS['BP_RA_GameMode'].generated_class())
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    floor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, -25))
    floor.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    floor.static_mesh_component.set_collision_profile_name('BlockAll')
    floor.set_actor_scale3d(unreal.Vector(40, 40, 0.5))
    actors.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(0, 0, 96))
    target_wall = actors.spawn_actor_from_class(wall.generated_class(), unreal.Vector(1600, 600, 150))
    target_wall.set_actor_scale3d(unreal.Vector(0.5, 8, 3))
    actors.spawn_actor_from_class(test.generated_class(), unreal.Vector(0, 0, 400))
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name() == level_path + '.Lvl_RobotAutomation'
    assert levels.save_current_level()

# Also verify the saved prototype map contains exactly the placed test robot.
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
arena = GAME + '/Lvl_RicochetPrototype'
assert levels.load_level(arena)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_path_name() == arena + '.Lvl_RicochetPrototype'
placed = [a for a in actors.get_all_level_actors() if unreal.MathLibrary.class_is_child_of(a.get_class(), robot.generated_class())]
assert len(placed) == 1, len(placed)
report = {'fresh_load': True, 'prototype_robot_count': len(placed),
          'prototype_robot_location': str(placed[0].get_actor_location()),
          'test_map': BASE + '/Lvl_RobotAutomation', 'all_graphs_compiled': True}
(OUT / 'fresh_load_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('ROBOT_FRESH_LOAD_AND_TEST_HARNESS_VERIFIED')
