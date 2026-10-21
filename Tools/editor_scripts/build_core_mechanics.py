"""Editor-only authoring. All runtime behavior is compiled Blueprint graphs.

Run with UE 5.8 -run=pythonscript -EnablePlugins=EditorToolset.
Uses Epic's bundled EditorToolset, never third-party native code.
"""
import datetime
import json
import shutil
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as B
from editor_toolset.toolsets.actor import ActorTools as A
from editor_toolset.toolsets.blueprint_dsl import Transpiler

ROOT = Path(unreal.Paths.project_dir()).resolve()
BASE = '/Game/RicochetArena/CoreMechanics'
OUT = ROOT / 'Saved/Automation/CoreMechanics'
OUT.mkdir(parents=True, exist_ok=True)
ASSETS = {}
PIN_AUDIT = {}
LOCAL_NODES = {}


def make(name, parent):
    path = BASE + '/' + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        raise RuntimeError('Refusing to overwrite existing asset: ' + path)
    bp = B.create(BASE, name, parent.static_class())
    ASSETS[name] = bp
    return bp


def cdo(bp):
    return unreal.get_default_object(bp.generated_class())


def var(bp, name, kind, default=None):
    B.add_variable(bp, name, kind)
    if default is not None:
        B.compile_blueprint(bp)
        cdo(bp).set_editor_property(name, default)
    unreal.BlueprintEditorLibrary.set_blueprint_variable_instance_editable(bp, name, True)


def function(bp, name, inputs=(), outputs=()):
    graph = B.add_function_graph(bp, name)
    for param, kind in inputs:
        if isinstance(kind, str):
            B.add_function_param(graph, param, kind, True)
        else:
            B.add_object_function_param(graph, param, kind.static_class(), True)
    for param, kind in outputs:
        B.add_function_param(graph, param, kind, False)
    return graph


def node(graph, suffix, category=None):
    # Action database updates are deferred in commandlets. Resolve new Blueprint
    # members/functions directly through the official graph editor instead.
    owner = graph.get_outer()
    for bp in [owner] + [b for b in ASSETS.values() if b != owner]:
        members = [str(n) for n in unreal.BlueprintEditorLibrary.list_member_variable_names(bp, False)]
        if suffix[:3] in ('Get', 'Set') and suffix[3:] in members:
            identifier = 'Local|' + bp.get_name() + '|' + suffix
            LOCAL_NODES[identifier] = ('get' if suffix.startswith('Get') else 'set', bp, suffix[3:])
            return identifier
        if suffix in [g.get_name() for g in B.list_graphs(bp)]:
            identifier = 'Local|' + bp.get_name() + '|' + suffix
            LOCAL_NODES[identifier] = ('call', bp, suffix)
            return identifier
    if suffix.startswith('CastTo') and suffix[6:] in ASSETS:
        identifier = 'Local|' + suffix
        LOCAL_NODES[identifier] = ('cast', ASSETS[suffix[6:]], '')
        return identifier
    candidates = B.find_node_types(graph, suffix)
    candidates = [n for n in candidates if n.rsplit('|', 1)[-1] == suffix]
    if category:
        candidates = [n for n in candidates if n.startswith(category + '|')]
    if len(candidates) != 1:
        raise RuntimeError(f'Node lookup {suffix}: {candidates}')
    name = candidates[0]
    if name not in PIN_AUDIT:
        info = B.get_node_type_pins(graph, name)
        PIN_AUDIT[name] = {'inputs': [(p.name, p.type_id) for p in info.input_pins],
                           'outputs': [(p.name, p.type_id) for p in info.output_pins]}
    return name


def getter(graph, name):
    return '(' + node(graph, 'Get' + name) + ')'


def setter(graph, name, expr):
    return '(' + node(graph, 'Set' + name) + ' :' + name + ' ' + expr + ')'


def write(graph, code):
    Transpiler(graph, create_node, B.connect_pins, B._get_node_info,
               B.set_pin_value, lambda g: B.find_nodes(g),
               delete_node_fn=B.delete_node,
               find_node_types_fn=lambda f: B.find_node_types(graph, f)).transpile(code)
    B.compile_blueprint(graph.get_outer())
    (OUT / (graph.get_outer().get_name() + '_' + graph.get_name() + '.sexpr')).write_text(code, encoding='utf-8')


def create_node(graph, identifier, position):
    if identifier not in LOCAL_NODES:
        return B.create_node(graph, identifier, position)
    kind, bp, name = LOCAL_NODES[identifier]
    editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    cls_path = bp.generated_class().get_path_name()
    if kind == 'get':
        result = editor.add_get_member_variable_node(name, cls_path)
    elif kind == 'set':
        result = editor.add_set_member_variable_node(name, cls_path)
    elif kind == 'call':
        result = editor.add_call_function_node(cls_path + ':' + name)
    else:
        result = B.create_node(graph, node(graph, 'CastToActor'), position)
        assert editor.retarget_node_class(result, unreal.Actor.static_class(), bp.generated_class())
    assert result, identifier
    result.set_node_pos(position)
    info = B._get_node_info(result)
    PIN_AUDIT[identifier] = {'inputs': [(p.name, p.type_id) for p in info.input_pins],
                              'outputs': [(p.name, p.type_id) for p in info.output_pins]}
    return result


def mesh(owner, name, shape, scale, location=(0, 0, 0)):
    comp = A.add_component(owner, unreal.StaticMeshComponent.static_class(), name)
    comp.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/' + shape))
    comp.set_editor_property('relative_scale3d', unreal.Vector(*scale))
    comp.set_editor_property('relative_location', unreal.Vector(*location))
    comp.set_editor_property('mobility', unreal.ComponentMobility.MOVABLE)
    comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return comp


def root_component(bp, component):
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    for handle in sds.k2_gather_subobject_data_for_blueprint(bp):
        data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
        if unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data) == component:
            assert sds.make_new_scene_root(sds.k2_gather_subobject_data_for_blueprint(bp)[0], handle, bp)
            return
    raise RuntimeError('Missing root handle')


def connect(source, output, target, input_name):
    a = unreal.BlueprintEditorLibrary.find_output_pin(source, output)
    b = unreal.BlueprintEditorLibrary.find_input_pin(target, input_name)
    assert a.is_valid() and b.is_valid(), (output, input_name)
    assert a.try_create_connection(b), (output, input_name)


def compile_all():
    for bp in ASSETS.values():
        B.compile_blueprint(bp, warnings_as_errors=True)


def build():
    assert unreal.SystemLibrary.get_engine_version().startswith('5.8.')
    # New content only; configuration changes are performed separately after verification.
    player = make('BP_RA_PlayerCharacter', unreal.Character)
    controller = make('BP_RA_PlayerController', unreal.PlayerController)
    projectile = make('BP_RA_RicochetProjectile', unreal.Actor)
    chip = make('BP_RA_Microchip', unreal.Actor)
    wall = make('BP_RA_RicochetWall', unreal.StaticMeshActor)
    mode = make('BP_RA_GameMode', unreal.GameModeBase)
    hud = make('BP_RA_HUD', unreal.HUD)

    # Character and camera. A fixed world camera orientation keeps WASD screen-aligned.
    var(player, 'Microchips', 'int', 0)
    var(player, 'FireInterval', 'float', 0.18)
    var(player, 'NextFireTime', 'float', -1.0)
    var(player, 'ShotsFired', 'int', 0)
    var(player, 'AimPoint', 'Vector', unreal.Vector(1000, 0, 96))
    pc = cdo(player)
    pc.set_editor_property('use_controller_rotation_yaw', False)
    pc.get_editor_property('character_movement').set_editor_property('orient_rotation_to_movement', False)
    pc.get_editor_property('character_movement').set_editor_property('max_walk_speed', 650.0)
    mesh(player, 'BodyVisual', 'Cylinder', (0.55, 0.55, 1.2), (0, 0, -30))
    mesh(player, 'WeaponVisual', 'Cube', (0.8, 0.12, 0.12), (45, 0, 5))
    arm = A.add_component(player, unreal.SpringArmComponent.static_class(), 'CameraBoom')
    arm.set_editor_property('target_arm_length', 1650.0)
    arm.set_editor_property('relative_rotation', unreal.Rotator(-70, 0, 0))
    arm.set_editor_property('absolute_rotation', True)
    arm.set_editor_property('do_collision_test', False)
    arm.set_editor_property('use_pawn_control_rotation', False)
    camera = A.add_component(arm, unreal.CameraComponent.static_class(), 'ArenaCamera')
    camera.set_editor_property('field_of_view', 65.0)
    camera.set_editor_property('relative_location', unreal.Vector(0, 0, 0))
    cdo(controller).set_editor_property('show_mouse_cursor', True)
    cdo(controller).set_editor_property('enable_click_events', False)

    # Projectile: swept sphere root, planar constant-speed physical bounce.
    var(projectile, 'HasRicocheted', 'bool', False)
    var(projectile, 'RicochetCount', 'int', 0)
    var(projectile, 'MaxRicochets', 'int', 8)
    var(projectile, 'Damage', 'float', 25.0)
    sphere = A.add_component(projectile, unreal.SphereComponent.static_class(), 'CollisionSphere')
    sphere.set_editor_property('sphere_radius', 8.0)
    sphere.set_editor_property('mobility', unreal.ComponentMobility.MOVABLE)
    sphere.set_collision_profile_name('BlockAllDynamic')
    sphere.set_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN, unreal.CollisionResponseType.ECR_IGNORE)
    root_component(projectile, sphere)
    mesh(sphere, 'ProjectileVisual', 'Sphere', (0.16, 0.16, 0.16))
    movement = A.add_component(projectile, unreal.ProjectileMovementComponent.static_class(), 'ProjectileMovement')
    movement.set_editor_property('initial_speed', 1800.0)
    movement.set_editor_property('max_speed', 1800.0)
    movement.set_editor_property('projectile_gravity_scale', 0.0)
    movement.set_editor_property('should_bounce', True)
    movement.set_editor_property('bounciness', 1.0)
    movement.set_editor_property('friction', 0.0)
    movement.set_editor_property('bounce_velocity_stop_simulating_threshold', 0.0)
    movement.set_editor_property('rotation_follows_velocity', True)
    movement.set_editor_property('constrain_to_plane', True)
    movement.set_editor_property('plane_constraint_normal', unreal.Vector(0, 0, 1))
    movement.set_editor_property('force_sub_stepping', True)
    cdo(projectile).set_editor_property('initial_life_span', 6.0)

    # Eligible walls are explicit; floors and arbitrary objects cannot enable damage.
    wc = cdo(wall)
    wc.set_editor_property('tags', [unreal.Name('RicochetWall')])
    wc.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    wc.static_mesh_component.set_collision_profile_name('BlockAll')

    var(chip, 'Value', 'int', 1)
    var(chip, 'Collected', 'bool', False)
    pickup = A.add_component(chip, unreal.SphereComponent.static_class(), 'PickupSphere')
    pickup.set_editor_property('sphere_radius', 75.0)
    pickup.set_collision_profile_name('OverlapOnlyPawn')
    pickup.set_editor_property('generate_overlap_events', True)
    root_component(chip, pickup)
    mesh(pickup, 'ChipVisual', 'Cube', (0.28, 0.28, 0.10))

    # Public Blueprint functions are also exercised by editor automation tests.
    move = function(player, 'MoveInDirection', [('Direction', 'Vector')])
    aim = function(player, 'AimAtPoint', [('Point', 'Vector')])
    add = function(player, 'AddMicrochips', [('Amount', 'int')])
    fire = function(player, 'TryFire')
    bounce = function(projectile, 'RegisterWallHit', [('HitActor', unreal.Actor)])
    damage = function(projectile, 'GetRobotDamage', outputs=[('Result', 'float')])
    collect = function(chip, 'TryCollect', [('Collector', unreal.Actor)])
    compile_all()

    write(move, f'''(fn MoveInDirection (Direction)
      ({node(move, 'AddMovementInput')} :WorldDirection
        ({node(move, 'ClampVectorSize')} :A Direction :Min 0.0 :Max 1.0) :ScaleValue 1.0))''')
    write(aim, f'''(fn AimAtPoint (Point)
      {setter(aim, 'AimPoint', 'Point')}
      (bind here ({node(aim, 'GetActorLocation')}))
      (bind facing ({node(aim, 'FindLookatRotation')} :Start here :Target Point))
      ({node(aim, 'SetActorRotation')} :NewRotation
        ({node(aim, 'MakeRotator')} :Yaw (.yaw facing))))''')
    write(add, f'''(fn AddMicrochips (Amount)
      (if (> Amount 0)
        {setter(add, 'Microchips', '(+ ' + getter(add, 'Microchips') + ' Amount)')}))''')
    write(fire, f'''(fn TryFire ()
      (bind now ({node(fire, 'GetGameTimeinSeconds')}))
      (if (>= now {getter(fire, 'NextFireTime')})
        {setter(fire, 'NextFireTime', '(+ now ' + getter(fire, 'FireInterval') + ')')}
        (bind origin ({node(fire, 'GetActorLocation')}))
        (bind forward ({node(fire, 'GetActorForwardVector')}))
        (bind projectile ({node(fire, 'SpawnActorfromClass')}
          :Class "{BASE}/BP_RA_RicochetProjectile.BP_RA_RicochetProjectile_C"
          :SpawnTransform ({node(fire, 'MakeTransform')}
            :Location (+ origin (* forward 85.0))
            :Rotation ({node(fire, 'GetActorRotation')}))
          :CollisionHandlingOverride "DontSpawnIfColliding" :Owner self))
        {setter(fire, 'ShotsFired', '(+ ' + getter(fire, 'ShotsFired') + ' 1)')}))''')
    write(bounce, f'''(fn RegisterWallHit (HitActor)
      (if ({node(bounce, 'ActorHasTag')} :self HitActor :Tag "RicochetWall")
        {setter(bounce, 'HasRicocheted', 'true')}
        {setter(bounce, 'RicochetCount', '(+ ' + getter(bounce, 'RicochetCount') + ' 1)')}
        (if (>= {getter(bounce, 'RicochetCount')} {getter(bounce, 'MaxRicochets')})
          ({node(bounce, 'DestroyActor')}))
        (else ({node(bounce, 'DestroyActor')}))))''')
    write(damage, f'''(fn GetRobotDamage ()
      (return (select {getter(damage, 'HasRicocheted')} {getter(damage, 'Damage')} 0.0)))''')
    # Compile function bodies before discovering their callable nodes in other assets.
    B.compile_blueprint(player, warnings_as_errors=True)
    B.compile_blueprint(projectile, warnings_as_errors=True)
    cast = node(collect, 'CastToBP_RA_PlayerCharacter')
    write(collect, f'''(fn TryCollect (Collector)
      (if (not {getter(collect, 'Collected')})
        (bind player ({cast} :Object Collector)
          (:then
            {setter(collect, 'Collected', 'true')}
            ({node(collect, 'AddMicrochips')} :self player :Amount {getter(collect, 'Value')})
            ({node(collect, 'DestroyActor')}))
          (:CastFailed))))''')

    # Event tick handles input only. Movement itself remains CharacterMovement driven.
    event = B.get_graph(player, 'EventGraph')
    key = node(event, 'IsInputKeyDown')
    def down(name):
        return f'({key} :self pc :Key "(KeyName={name})")'
    write(event, f'''(event EventTick (DeltaSeconds)
      (bind pc ({node(event, 'GetPlayerController', 'Game')}))
      (bind x (- (select {down('W')} 1.0 0.0) (select {down('S')} 1.0 0.0)))
      (bind y (- (select {down('D')} 1.0 0.0) (select {down('A')} 1.0 0.0)))
      ({node(event, 'MoveInDirection')} :Direction ({node(event, 'MakeVector')} :X x :Y y))
      (bind (hit valid) ({node(event, 'GetHitResultUnderCursorbyChannel')} :self pc :bTraceComplex false))
      (if valid
        (bind (blocking initial time distance location impact normal impactNormal physmat hitactor hitcomp hitbone bone item element face start end)
          ({node(event, 'BreakHitResult')} :Hit hit))
        ({node(event, 'AimAtPoint')} :Point impact))
      (if {down('LeftMouseButton')}
        ({node(event, 'TryFire')})))''')

    # Collision dispatches are real connected event nodes, not runtime Python callbacks.
    ce = B.get_graph(chip, 'EventGraph')
    write(ce, f'''(event Collision|EventActorBeginOverlap (OtherActor)
      ({node(ce, 'TryCollect')} :Collector OtherActor))''')
    pe = B.get_graph(projectile, 'EventGraph')
    bounced = B.add_component_bound_event(movement, 'OnProjectileBounce', pe)
    broken = B.create_node(pe, node(pe, 'BreakHitResult'), unreal.IntPoint(300, 100))
    handler = create_node(pe, node(pe, 'RegisterWallHit'), unreal.IntPoint(650, 0))
    connect(bounced, 'ImpactResult', broken, 'Hit')
    connect(bounced, 'then', handler, 'execute')
    connect(broken, 'HitActor', handler, 'HitActor')

    # Minimal Blueprint HUD: instructions plus live resource balance.
    he = B.get_graph(hud, 'EventGraph')
    draw = node(he, 'DrawText', 'HUD')
    cast_player = node(he, 'CastToBP_RA_PlayerCharacter')
    write(he, f'''(event EventReceiveDrawHUD (SizeX SizeY)
      ({draw} :Text "RICOCHET ARENA | WASD: move | LMB: fire | walls: ricochet"
        :ScreenX 25.0 :ScreenY 25.0 :Scale 1.4 :TextColor "(R=0.3,G=0.9,B=1.0,A=1.0)")
      ({draw} :Text "CHIPS:" :ScreenX 25.0 :ScreenY 65.0 :Scale 2.0
        :TextColor "(R=1.0,G=0.8,B=0.2,A=1.0)")
      (bind player ({cast_player} :Object ({node(he, 'GetPlayerCharacter')}))
        (:then
          ({draw} :Text ({node(he, 'GetMicrochips')} :self player)
            :ScreenX 135.0 :ScreenY 65.0 :Scale 2.0 :TextColor "(R=1.0,G=0.8,B=0.2,A=1.0)"))
        (:CastFailed)))''')

    compile_all()
    defaults = cdo(mode)
    defaults.set_editor_property('default_pawn_class', player.generated_class())
    defaults.set_editor_property('player_controller_class', controller.generated_class())
    defaults.set_editor_property('hud_class', hud.generated_class())
    for bp in ASSETS.values():
        assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
    make_arena(mode, wall, chip)
    audit = {}
    for name, bp in ASSETS.items():
        audit[name] = {'status': str(bp.get_editor_property('status')), 'graphs': {}}
        for graph in B.list_graphs(bp):
            editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
            nodes = editor.list_all_nodes()
            errors = editor.list_nodes_with_errors()
            assert not errors, (name, graph.get_name(), errors)
            audit[name]['graphs'][graph.get_name()] = len(nodes)
            (OUT / (name + '_' + graph.get_name() + '_verified.sexpr')).write_text(B.read_graph_dsl(graph), encoding='utf-8')
    (OUT / 'node_pin_audit.json').write_text(json.dumps(PIN_AUDIT, indent=2), encoding='utf-8')
    (OUT / 'build_report.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    unreal.log('CORE_MECHANICS_BUILD_VERIFIED')


def make_arena(mode, wall, chip):
    level_path = BASE + '/Lvl_RicochetPrototype'
    if unreal.EditorAssetLibrary.does_asset_exist(level_path):
        raise RuntimeError('Refusing to overwrite level')
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    assert levels.new_level(level_path)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    expected_world_path = level_path + '.Lvl_RicochetPrototype'
    assert world and world.get_path_name() == expected_world_path, (
        'Refusing to edit any world except the new test map',
        world.get_path_name() if world else None, expected_world_path)
    world.get_world_settings().set_editor_property('default_game_mode', mode.generated_class())
    def cube(label, location, scale):
        a = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*location))
        a.set_actor_label(label)
        a.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
        a.static_mesh_component.set_collision_profile_name('BlockAll')
        a.set_actor_scale3d(unreal.Vector(*scale))
        return a
    cube('ArenaFloor', (0, 0, -25), (32, 26, 0.5))
    for label, loc, scale in [
        ('North', (0, -1300, 150), (32, 0.5, 3)),
        ('South', (0, 1300, 150), (32, 0.5, 3)),
        ('East', (1600, 0, 150), (0.5, 26, 3)),
        ('West', (-1600, 0, 150), (0.5, 26, 3)),
        ('TestWallA', (450, 150, 150), (0.5, 9, 3)),
        ('TestWallB', (-550, -250, 150), (7, 0.5, 3)),
    ]:
        a = actors.spawn_actor_from_class(wall.generated_class(), unreal.Vector(*loc))
        a.set_actor_label('RicochetWall_' + label)
        a.set_actor_scale3d(unreal.Vector(*scale))
    actors.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(0, 0, 100))
    for x, y, amount in [(180, 0, 1), (250, -150, 2), (-250, 150, 3), (900, 450, 5), (-1000, -750, 10)]:
        a = actors.spawn_actor_from_class(chip.generated_class(), unreal.Vector(x, y, 40))
        a.set_editor_property('Value', amount)
    light = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 800), unreal.Rotator(-50, -30, 0))
    light.light_component.set_editor_property('intensity', 5.0)
    actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 500))
    active_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert active_world == world and active_world.get_path_name() == expected_world_path, (
        'Active world changed; refusing to save')
    assert levels.save_current_level()


if __name__ == '__main__':
    build()
