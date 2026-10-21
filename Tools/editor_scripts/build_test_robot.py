"""UE 5.8 editor authoring only: robot, screen-space health widget, ricochet damage.

All runtime behavior is compiled Blueprint; no runtime Python or native project code.
Existing projectile and prototype map are backed up before modification.
"""
import datetime
import json
import shutil
import sys
from pathlib import Path
import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_core_mechanics as core
from build_core_mechanics import B, A, cdo, var, function, node, getter, setter, write

ROOT = Path(unreal.Paths.project_dir()).resolve()
GAME = '/Game/RicochetArena/CoreMechanics'
BASE = '/Game/RicochetArena/Robot'
OUT = ROOT / 'Saved/Automation/Robot'
OUT.mkdir(parents=True, exist_ok=True)
core.BASE = BASE
core.OUT = OUT


def member(bp, name):
    identifier = 'RobotMember|' + bp.get_name() + '|Get' + name
    core.LOCAL_NODES[identifier] = ('get', bp, name)
    return '(' + identifier + ')'


def material(name, color, metallic=0.0, emission=False):
    assert not unreal.EditorAssetLibrary.does_asset_exist(BASE + '/' + name)
    asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, BASE, unreal.Material, unreal.MaterialFactoryNew())
    rgb = unreal.MaterialEditingLibrary.create_material_expression(asset, unreal.MaterialExpressionConstant3Vector)
    rgb.set_editor_property('constant', unreal.LinearColor(*color, 1))
    unreal.MaterialEditingLibrary.connect_material_property(rgb, '', unreal.MaterialProperty.MP_BASE_COLOR)
    if emission:
        unreal.MaterialEditingLibrary.connect_material_property(rgb, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    metal = unreal.MaterialEditingLibrary.create_material_expression(asset, unreal.MaterialExpressionConstant)
    metal.set_editor_property('r', metallic)
    unreal.MaterialEditingLibrary.connect_material_property(metal, '', unreal.MaterialProperty.MP_METALLIC)
    unreal.MaterialEditingLibrary.recompile_material(asset)
    return asset


def make_widget():
    assert not unreal.EditorAssetLibrary.does_asset_exist(BASE + '/WBP_RA_RobotHealth')
    tool = unreal.get_default_object(unreal.UMGToolSet.static_class())
    widget = tool.call_method('CreateWidgetBlueprint', args=(BASE, 'WBP_RA_RobotHealth', unreal.UserWidget.static_class()))
    assert isinstance(widget, unreal.WidgetBlueprint)
    core.ASSETS[widget.get_name()] = widget
    def add(cls, name, parent=None):
        return tool.call_method('AddWidget', args=(widget, cls.static_class(), name, parent, -1)).widget
    size = add(unreal.SizeBox, 'HealthPanel')
    size.set_width_override(160.0)
    size.set_height_override(42.0)
    column = add(unreal.VerticalBox, 'PanelLayout', size)
    title = add(unreal.TextBlock, 'RobotTitle', column)
    title.set_text('TEST ROBOT')
    title.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(0.8, 0.94, 1, 1)))
    title.set_editor_property('justification', unreal.TextJustify.CENTER)
    bar_size = add(unreal.SizeBox, 'BarHeight', column)
    bar_size.set_height_override(12.0)
    progress = add(unreal.ProgressBar, 'HealthProgress', bar_size)
    tool.call_method('ToggleWidgetAsVariable', args=(widget, progress, True))
    progress.set_percent(1.0)
    progress.set_fill_color_and_opacity(unreal.LinearColor(0.1, 0.9, 0.25, 1))
    var(widget, 'DisplayPercent', 'float', 1.0)
    update = function(widget, 'UpdateHealth', [('Current', 'float'), ('Maximum', 'float')])
    B.compile_blueprint(widget)
    write(update, f'''(fn UpdateHealth (Current Maximum)
      (bind safeMax (select (> Maximum 0.0) Maximum 1.0))
      (bind ratio (/ Current safeMax))
      (bind percent (select (< ratio 0.0) 0.0 (select (> ratio 1.0) 1.0 ratio)))
      {setter(update, 'DisplayPercent', 'percent')}
      ({node(update, 'SetPercent', 'Progress')} :self {member(widget, 'HealthProgress')} :InPercent percent))''')
    B.compile_blueprint(widget, warnings_as_errors=True)
    return widget


def build():
    assert unreal.SystemLibrary.get_engine_version().startswith('5.8.')
    projectile = unreal.load_asset(GAME + '/BP_RA_RicochetProjectile')
    assert projectile
    core.ASSETS[projectile.get_name()] = projectile
    arena_path = GAME + '/Lvl_RicochetPrototype'
    # Exact source paths, copied as opaque files; .uasset/.umap contents never edited.
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = ROOT / 'Saved/AutomationBackups' / ('RobotBuild_' + stamp)
    backup.mkdir(parents=True)
    for relative in ['Content/RicochetArena/CoreMechanics/BP_RA_RicochetProjectile.uasset',
                     'Content/RicochetArena/CoreMechanics/Lvl_RicochetPrototype.umap']:
        source = ROOT / relative
        assert source.is_file(), source
        shutil.copy2(source, backup / source.name)
    (OUT / 'backup_path.txt').write_text(str(backup), encoding='utf-8')
    original = {g.get_name(): B.read_graph_dsl(g) for g in B.list_graphs(projectile)}
    assert 'ActorHasTag' in original['RegisterWallHit'] and 'RicochetWall' in original['RegisterWallHit']
    (OUT / 'projectile_before.json').write_text(json.dumps(original, indent=2), encoding='utf-8')

    health_widget = make_widget()
    robot = core.make('BP_RA_TestRobot', unreal.Actor)
    var(robot, 'MaxHealth', 'float', 100.0)
    var(robot, 'CurrentHealth', 'float', 100.0)
    var(robot, 'IsDead', 'bool', False)
    var(robot, 'LastDamage', 'float', 0.0)
    var(robot, 'HealthFraction', 'float', 1.0)
    var(robot, 'ChipDropValue', 'int', 5)  # Reserved for a future drop implementation.
    cdo(robot).set_editor_property('tags', [unreal.Name('RicochetRobot')])
    collider = A.add_component(robot, unreal.BoxComponent.static_class(), 'RobotCollision')
    collider.set_editor_property('box_extent', unreal.Vector(48, 52, 85))
    collider.set_collision_profile_name('BlockAllDynamic')
    collider.set_collision_object_type(unreal.CollisionChannel.ECC_WORLD_DYNAMIC)
    core.root_component(robot, collider)
    body_mat = material('M_RA_RobotBody', (0.08, 0.21, 0.3), 0.7)
    metal_mat = material('M_RA_RobotMetal', (0.28, 0.32, 0.36), 0.8)
    eye_mat = material('M_RA_RobotEye', (1.0, 0.16, 0.015), 0.0, True)
    pieces = [('Body', 'Cube', (0.66, 0.75, 0.82), (0, 0, 8), body_mat),
              ('Head', 'Cube', (0.5, 0.58, 0.43), (0, 0, 72), body_mat),
              ('LeftArm', 'Cube', (0.28, 0.22, 0.75), (0, -51, 2), metal_mat),
              ('RightArm', 'Cube', (0.28, 0.22, 0.75), (0, 51, 2), metal_mat),
              ('LeftLeg', 'Cube', (0.38, 0.27, 0.45), (0, -21, -58), metal_mat),
              ('RightLeg', 'Cube', (0.38, 0.27, 0.45), (0, 21, -58), metal_mat),
              ('Eye', 'Cube', (0.04, 0.43, 0.09), (-26, 0, 74), eye_mat)]
    for name, shape, scale, loc, mat in pieces:
        visual = core.mesh(collider, name, shape, scale, loc)
        visual.set_material(0, mat)
    health = A.add_component(robot, unreal.WidgetComponent.static_class(), 'HealthBar')
    health.set_editor_property('relative_location', unreal.Vector(0, 0, 125))
    health.set_editor_property('widget_class', health_widget.generated_class())
    health.set_editor_property('space', unreal.WidgetSpace.SCREEN)
    health.set_editor_property('draw_size', unreal.IntPoint(160, 42))
    health.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)

    init = function(robot, 'InitializeHealth')
    refresh = function(robot, 'RefreshHealthBar')
    receive = function(robot, 'ReceiveProjectileDamage', [('IncomingDamage', 'float'), ('Source', unreal.Actor)])
    die = function(robot, 'Die')
    function(robot, 'HandleRobotDestroyed')
    # New guard prevents multiple damage applications in one collision/substep.
    assert 'ImpactConsumed' not in B.list_variables(projectile)
    var(projectile, 'ImpactConsumed', 'bool', False)
    B.compile_blueprint(robot)
    B.compile_blueprint(projectile)

    write(refresh, f'''(fn RefreshHealthBar ()
      (bind maximum {getter(refresh, 'MaxHealth')})
      {setter(refresh, 'HealthFraction', '(/ ' + getter(refresh, 'CurrentHealth') + ' (select (> maximum 0.0) maximum 1.0))')}
      (bind widget ({node(refresh, 'GetUserWidgetObject')} :self {member(robot, 'HealthBar')}))
      (bind bar ({node(refresh, 'CastToWBP_RA_RobotHealth')} :Object widget)
        (:then
          ({node(refresh, 'UpdateHealth')} :self bar
            :Current {getter(refresh, 'CurrentHealth')} :Maximum maximum))
        (:CastFailed)))''')
    write(init, f'''(fn InitializeHealth ()
      (bind maximum {getter(init, 'MaxHealth')})
      {setter(init, 'MaxHealth', '(select (> maximum 0.0) maximum 1.0)')}
      {setter(init, 'CurrentHealth', getter(init, 'MaxHealth'))}
      {setter(init, 'IsDead', 'false')}
      ({node(init, 'RefreshHealthBar')}))''')
    write(die, f'''(fn Die ()
      (if (not {getter(die, 'IsDead')})
        {setter(die, 'IsDead', 'true')}
        ({node(die, 'SetActorEnableCollision')} :bNewActorEnableCollision false)
        ({node(die, 'HandleRobotDestroyed')})
        ({node(die, 'SetLifeSpan')} :InLifespan 1.0)))''')
    B.compile_blueprint(robot)
    write(receive, f'''(fn ReceiveProjectileDamage (IncomingDamage Source)
      (if (and (not {getter(receive, 'IsDead')}) (> IncomingDamage 0.0))
        (bind bullet ({node(receive, 'CastToBP_RA_RicochetProjectile')} :Object Source)
          (:then
            (bind allowed ({node(receive, 'GetRobotDamage')} :self bullet))
            (if (> allowed 0.0)
              (bind damage (select (< IncomingDamage allowed) IncomingDamage allowed))
              {setter(receive, 'LastDamage', 'damage')}
              (bind remaining (- {getter(receive, 'CurrentHealth')} damage))
              {setter(receive, 'CurrentHealth', '(select (> remaining 0.0) remaining 0.0)')}
              ({node(receive, 'RefreshHealthBar')})
              (if (<= {getter(receive, 'CurrentHealth')} 0.0)
                ({node(receive, 'Die')}))))
          (:CastFailed))))''')
    events = B.get_graph(robot, 'EventGraph')
    damage_event = node(events, 'EventAnyDamage').removeprefix('AddEvent|')
    write(events, f'''(event EventBeginPlay ({node(events, 'InitializeHealth')}))
      (event {damage_event} (Damage DamageType InstigatedBy DamageCauser)
        ({node(events, 'ReceiveProjectileDamage')} :IncomingDamage Damage :Source DamageCauser))''')

    impact = B.get_graph(projectile, 'RegisterWallHit')
    write(impact, f'''(fn RegisterWallHit (HitActor)
      (if (not {getter(impact, 'ImpactConsumed')})
        (if ({node(impact, 'ActorHasTag')} :self HitActor :Tag "RicochetWall")
          {setter(impact, 'HasRicocheted', 'true')}
          {setter(impact, 'RicochetCount', '(+ ' + getter(impact, 'RicochetCount') + ' 1)')}
          (if (>= {getter(impact, 'RicochetCount')} {getter(impact, 'MaxRicochets')})
            ({node(impact, 'DestroyActor')}))
          (else
            {setter(impact, 'ImpactConsumed', 'true')}
            (if ({node(impact, 'ActorHasTag')} :self HitActor :Tag "RicochetRobot")
              (bind damage ({node(impact, 'GetRobotDamage')}))
              (if (> damage 0.0)
                ({node(impact, 'ApplyDamage')} :DamagedActor HitActor :BaseDamage damage :DamageCauser self)))
            ({node(impact, 'DestroyActor')})))))''')
    for bp in [health_widget, robot, projectile]:
        B.compile_blueprint(bp, warnings_as_errors=True)
    # Save only the explicitly modified projectile and newly authored assets.
    for asset in [health_widget, robot, projectile, body_mat, metal_mat, eye_mat]:
        assert unreal.EditorAssetLibrary.save_loaded_asset(asset, False)

    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    assert levels.load_level(arena_path)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    expected = arena_path + '.Lvl_RicochetPrototype'
    assert world.get_path_name() == expected
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    assert not [a for a in actors.get_all_level_actors() if unreal.MathLibrary.class_is_child_of(a.get_class(), robot.generated_class())]
    instance = actors.spawn_actor_from_class(robot.generated_class(), unreal.Vector(-350, 250, 85))
    instance.set_actor_label('TestRobot_RicochetOnly_100HP')
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name() == expected
    assert levels.save_current_level()
    report = {'robot': robot.get_path_name(), 'health_widget': health_widget.get_path_name(),
              'arena': arena_path, 'position': [-350, 250, 85], 'max_health': 100,
              'damage_per_ricochet': 25, 'drops_implemented': False, 'blueprints': {}}
    for bp in [health_widget, robot, projectile]:
        graphs = {}
        for graph in B.list_graphs(bp):
            editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
            assert not editor.list_nodes_with_errors()
            graphs[graph.get_name()] = len(editor.list_all_nodes())
            (OUT / (bp.get_name() + '_' + graph.get_name() + '_verified.sexpr')).write_text(B.read_graph_dsl(graph), encoding='utf-8')
        report['blueprints'][bp.get_name()] = {'status': str(bp.get_editor_property('status')), 'graphs': graphs}
    (OUT / 'build_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.log('ROBOT_BUILD_VERIFIED')


if __name__ == '__main__':
    build()
