"""Fresh-process graph inspection and authoring of a separate Blueprint runtime test."""
import json
import sys
from pathlib import Path
import unreal
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_core_mechanics as core
from build_core_mechanics import B, A, BASE, OUT, cdo, var, function, node, getter, setter, write

names = ['BP_RA_PlayerCharacter', 'BP_RA_PlayerController', 'BP_RA_RicochetProjectile',
         'BP_RA_Microchip', 'BP_RA_RicochetWall', 'BP_RA_GameMode', 'BP_RA_HUD']
report = {}
for name in names:
    bp = unreal.load_asset(BASE + '/' + name)
    assert isinstance(bp, unreal.Blueprint), name
    core.ASSETS[name] = bp
    assert bp.get_editor_property('status') == unreal.BlueprintStatus.BS_UP_TO_DATE
    graphs = {}
    for graph in B.list_graphs(bp):
        editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
        assert not editor.list_nodes_with_errors()
        graphs[graph.get_name()] = len(editor.list_all_nodes())
    report[name] = graphs

player = core.ASSETS[names[0]]
projectile = core.ASSETS['BP_RA_RicochetProjectile']
chip = core.ASSETS['BP_RA_Microchip']
wall = core.ASSETS['BP_RA_RicochetWall']
assert cdo(player).get_editor_property('FireInterval') > 0
assert cdo(player).get_editor_property('Microchips') == 0
assert not cdo(projectile).get_editor_property('HasRicocheted')
assert cdo(projectile).get_editor_property('MaxRicochets') == 8
OUT.joinpath('fresh_load_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

test = core.make('BP_RA_CoreRuntimeTest', unreal.Actor)
var(test, 'AllPassed', 'bool', True)
var(test, 'Finished', 'bool', False)
var(test, 'Elapsed', 'float', 0.0)
for name, bp in [('TestPlayer', player), ('TestProjectile', projectile)]:
    B.add_object_variable(test, name, bp.generated_class())
check = function(test, 'Check', [('Condition', 'bool'), ('Label', 'string')])
start = function(test, 'StartTest')
finish = function(test, 'FinishTest')
B.compile_blueprint(test)
write(check, f'''(fn Check (Condition Label)
  (if Condition
    ({node(check, 'PrintString')} :InString Label :bPrintToLog true)
    (else
      {setter(check, 'AllPassed', 'false')}
      ({node(check, 'PrintString')} :InString "CORE_TEST_FAIL" :bPrintToLog true)
      ({node(check, 'PrintString')} :InString Label :bPrintToLog true))))''')

def call(g, name, **args):
    return '(' + node(g, name) + ' ' + ' '.join(':' + k + ' ' + v for k, v in args.items()) + ')'

def assertion(g, condition, label):
    return call(g, 'Check', Condition=condition, Label='"CORE_TEST_PASS ' + label + '"')

spawn = node(start, 'SpawnActorfromClass')
transform = node(start, 'MakeTransform')
vector = node(start, 'MakeVector')
write(start, f'''(fn StartTest ()
  (bind pc ({node(start, 'GetPlayerCharacter')}))
  (bind p ({node(start, 'CastToBP_RA_PlayerCharacter')} :Object pc)
    (:then
      {setter(start, 'TestPlayer', 'p')}
      {call(start, 'AimAtPoint', self='p', Point=f'({vector} :X 0.0 :Y 1000.0 :Z 100.0)')}
      (bind rotation ({node(start, 'GetActorRotation')} :self p))
      {assertion(start, '(and (> (.yaw rotation) 85.0) (< (.yaw rotation) 95.0))', 'aim_yaw')}
      {call(start, 'TryFire', self='p')}
      {call(start, 'TryFire', self='p')}
      {assertion(start, '(== (' + node(start, 'GetShotsFired') + ' :self p) 1)', 'fire_cooldown')}
      {call(start, 'AddMicrochips', self='p', Amount='-5')}
      {assertion(start, '(== (' + node(start, 'GetMicrochips') + ' :self p) 0)', 'reject_negative_resources')}
      (bind resource ({spawn} :Class "{BASE}/BP_RA_Microchip.BP_RA_Microchip_C"
        :SpawnTransform ({transform} :Location ({vector} :X -1000.0 :Y 800.0 :Z 40.0))
        :CollisionHandlingOverride "AlwaysSpawn"))
      ({node(start, 'SetValue')} :self resource :Value 7)
      {call(start, 'TryCollect', self='resource', Collector='self')}
      {assertion(start, '(not (' + node(start, 'GetCollected') + ' :self resource))', 'reject_non_player_pickup')}
      {call(start, 'TryCollect', self='resource', Collector='p')}
      {assertion(start, '(== (' + node(start, 'GetMicrochips') + ' :self p) 7)', 'collect_value_once')}
      (bind bullet ({spawn} :Class "{BASE}/BP_RA_RicochetProjectile.BP_RA_RicochetProjectile_C"
        :SpawnTransform ({transform} :Location ({vector} :X 1100.0 :Y -800.0 :Z 100.0))
        :CollisionHandlingOverride "AlwaysSpawn"))
      {setter(start, 'TestProjectile', 'bullet')}
      {assertion(start, '(== (' + node(start, 'GetRobotDamage') + ' :self bullet) 0.0)', 'no_damage_before_ricochet')})
    (:CastFailed
      {setter(start, 'AllPassed', 'false')}
      ({node(start, 'PrintString')} :InString "CORE_TEST_FAIL player_missing" :bPrintToLog true))))''')

tp = getter(finish, 'TestPlayer')
tb = getter(finish, 'TestProjectile')
write(finish, f'''(fn FinishTest ()
  (bind p {tp})
  (bind bullet {tb})
  (bind loc ({node(finish, 'GetActorLocation')} :self p))
  {assertion(finish, '(> (.x loc) 100.0)', 'character_moves')}
  {assertion(finish, '(== (' + node(finish, 'GetMicrochips') + ' :self p) 12)', 'automatic_overlap_pickup')}
  {assertion(finish, '(' + node(finish, 'GetHasRicocheted') + ' :self bullet)', 'wall_sets_ricochet_flag')}
  {assertion(finish, '(== (' + node(finish, 'GetRicochetCount') + ' :self bullet) 1)', 'single_bounce_count')}
  (bind velocity ({node(finish, 'GetVelocity', 'Transformation')} :self bullet))
  {assertion(finish, '(< (.x velocity) -1700.0)', 'physical_reflection_keeps_speed')}
  {assertion(finish, '(== (' + node(finish, 'GetRobotDamage') + ' :self bullet) 25.0)', 'damage_after_ricochet')}
  (if {getter(finish, 'AllPassed')}
    ({node(finish, 'PrintString')} :InString "CORE_RUNTIME_VERIFIED" :bPrintToLog true)
    (else ({node(finish, 'PrintString')} :InString "CORE_RUNTIME_FAILED" :bPrintToLog true)))
  ({node(finish, 'QuitGame')} :QuitPreference "Quit" :bIgnorePlatformRestrictions true))''')
B.compile_blueprint(test, warnings_as_errors=True)
events = B.get_graph(test, 'EventGraph')
write(events, f'''(event EventBeginPlay ({node(events, 'StartTest')}))
(event EventTick (DeltaSeconds)
  (if (not {getter(events, 'Finished')})
    {setter(events, 'Elapsed', '(+ ' + getter(events, 'Elapsed') + ' DeltaSeconds)')}
    (if (< {getter(events, 'Elapsed')} 0.7)
      ({node(events, 'MoveInDirection')} :self {getter(events, 'TestPlayer')}
        :Direction ({node(events, 'MakeVector')} :X 1.0))
      (else
        {setter(events, 'Finished', 'true')}
        ({node(events, 'FinishTest')})))))''')
B.compile_blueprint(test, warnings_as_errors=True)
assert unreal.EditorAssetLibrary.save_loaded_asset(test, False)

# A separate, new level for automated gameplay tests; never save the user's world.
path = BASE + '/Lvl_CoreAutomation'
assert not unreal.EditorAssetLibrary.does_asset_exist(path)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert levels.new_level(path)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_path_name() == path + '.Lvl_CoreAutomation'
world.get_world_settings().set_editor_property('default_game_mode', core.ASSETS['BP_RA_GameMode'].generated_class())
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
floor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, -25))
floor.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
floor.set_actor_scale3d(unreal.Vector(40, 40, 0.5))
floor.static_mesh_component.set_collision_profile_name('BlockAll')
actors.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(0, 0, 96))
target = actors.spawn_actor_from_class(wall.generated_class(), unreal.Vector(1600, -800, 150))
target.set_actor_scale3d(unreal.Vector(0.5, 10, 3))
pickup = actors.spawn_actor_from_class(chip.generated_class(), unreal.Vector(200, 0, 40))
pickup.set_editor_property('Value', 5)
actors.spawn_actor_from_class(test.generated_class(), unreal.Vector(0, 0, 400))
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name() == path + '.Lvl_CoreAutomation'
assert levels.save_current_level()
unreal.log('CORE_FRESH_LOAD_AND_TEST_HARNESS_VERIFIED')
