"""Blueprint pursuit/navigation, melee attacks, chip drops and bounded spawning."""
import sys
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).resolve().parent))
from progression_common import *

player=load(GAME+'/BP_RA_PlayerCharacter')
parent=load(ROBOT+'/BP_RA_TestRobot')
chip=load(GAME+'/BP_RA_Microchip')
unreal.BlueprintEditorLibrary.set_blueprint_variable_expose_on_spawn(chip,'Value',True)
B.compile_blueprint(chip,warnings_as_errors=True)
assert unreal.EditorAssetLibrary.save_loaded_asset(chip,False)
ai=make('BP_RA_HunterRobot',parent.generated_class())
director=make('BP_RA_RobotDirector',unreal.Actor)
for name,kind,value in [('MoveSpeed','float',220.0),('AttackRange','float',145.0),
                        ('AttackDamage','float',10.0),('AttackInterval','float',1.0),
                        ('NextAttackTime','float',0.0),('NextPathTime','float',0.0),
                        ('PathRefreshInterval','float',0.35),('IsPursuing','bool',False),
                        ('TargetWaypoint','Vector',unreal.Vector(0,0,85)),('PathReady','bool',False)]:
    var(ai,name,kind,value)
objvar(ai,'TargetPlayer',player.generated_class())
for name,kind,value in [('SpawnInterval','float',4.0),('NextSpawnTime','float',3.0),
                        ('MaxAliveRobots','int',6),('SpawnIndex','int',0),('SpawningEnabled','bool',True)]:
    var(director,name,kind,value)
B.add_variable(director,'SpawnPoints','Vector',container_type=ContainerType.ARRAY)
B.compile_blueprint(director)
core.cdo(director).set_editor_property('SpawnPoints',[
    unreal.Vector(-1200,-900,85),unreal.Vector(1200,-900,85),
    unreal.Vector(-1200,900,85),unreal.Vector(1200,900,85)])
advance=fn(ai,'AdvanceRobotAI',[('Delta','float')])
refresh=fn(ai,'RefreshRobotPath')
spawn=fn(director,'SpawnRobot')
tick=fn(director,'UpdateDirector')
drop=unreal.BlueprintEditorLibrary.add_function_override(ai,'HandleRobotDestroyed')
assert drop,'Cannot override inherited death hook'
B.compile_blueprint(ai)
B.compile_blueprint(director)

# Material/HP presentation and ricochet-only damage are inherited from the test robot.
# Component navigation overrides must belong to the child, never modify the parent.
sds=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
for handle in sds.k2_gather_subobject_data_for_blueprint(ai):
    data=unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
    obj=unreal.SubobjectDataBlueprintFunctionLibrary.get_object_for_blueprint(data,ai)
    if isinstance(obj,unreal.PrimitiveComponent) and 'BP_RA_HunterRobot' in obj.get_path_name():
        obj.set_editor_property('can_ever_affect_navigation',False)
        if isinstance(obj,unreal.BoxComponent):obj.set_editor_property('box_extent',unreal.Vector(30,30,80))

path_call=N(refresh,'FindPathtoLocationSynchronously','AI|Navigation')
path_valid=N(refresh,'IsValid','AI|Navigation')
write(refresh,f'''(fn RefreshRobotPath ()
  {S(ai,'PathReady','false')}
  (bind target {V(ai,'TargetPlayer')})
  (if {K('IsObjectValid',Object='target')}
    (bind start ({N(refresh,'GetActorLocation')}))
    (bind end ({N(refresh,'GetActorLocation')} :self target))
    (bind path ({path_call} :PathStart start :PathEnd end :PathfindingContext self))
    (if {K('IsObjectValid',Object='path')}
      (if ({path_valid} :self path)
        (bind points ({N(refresh,'GetPathPoints','Class|NavigationPath')} :self path))
        (if (> ({N(refresh,'Length','Utilities|Array')} :TargetArray points) 1)
          {S(ai,'TargetWaypoint','('+N(refresh,'Get(acopy)','Utilities|Array')+' points 1)')}
          {S(ai,'PathReady','true')})))))''')
write(advance,f'''(fn AdvanceRobotAI (Delta)
  {S(ai,'IsPursuing','false')}
  (if (not {G(parent,'IsDead','self')})
    (bind player ({core.node(advance,'CastToBP_RA_PlayerCharacter')} :Object ({N(advance,'GetPlayerCharacter')}))
      (:then
        {S(ai,'TargetPlayer','player')}
        (if (and (not {G(player,'StealthActive','player')}) (not {G(player,'PlayerDead','player')}))
          {S(ai,'IsPursuing','true')}
          (bind now ({N(advance,'GetGameTimeInSeconds')}))
          (bind here ({N(advance,'GetActorLocation')}))
          (bind target ({N(advance,'GetActorLocation')} :self player))
          (bind offset (- target here))
          (bind flat ({N(advance,'MakeVector')} :X (.x offset) :Y (.y offset)))
          (bind distance ({N(advance,'VectorLength','Math|Vector')} :A flat))
          (if (<= distance {V(ai,'AttackRange')})
            (if (>= now {V(ai,'NextAttackTime')})
              (bind (hit blocked) ({N(advance,'LineTraceByChannel','Collision')}
                :Start here :End target :bTraceComplex false :bIgnoreSelf true))
              (if (not blocked)
                {S(ai,'NextAttackTime','(+ now '+V(ai,'AttackInterval')+')')}
                {F(player,'ReceiveRobotDamage',self='player',Amount=V(ai,'AttackDamage'))}))
            (else
              (if (>= now {V(ai,'NextPathTime')})
                {S(ai,'NextPathTime','(+ now '+V(ai,'PathRefreshInterval')+')')}
                {F(ai,'RefreshRobotPath')})
              (if {V(ai,'PathReady')}
                (bind stepOffset (- {V(ai,'TargetWaypoint')} here))
                (bind flatStep ({N(advance,'MakeVector')} :X (.x stepOffset) :Y (.y stepOffset)))
                (bind stepDistance ({N(advance,'VectorLength','Math|Vector')} :A flatStep))
                (bind length (* {V(ai,'MoveSpeed')} Delta))
                (bind direction ({N(advance,'Normalize2D(Vector)','Math|Vector')} :A flatStep))
                ({N(advance,'AddActorWorldOffset')} :DeltaLocation
                  (* direction (select (< length stepDistance) length stepDistance)) :bSweep true)
                (bind facing ({N(advance,'FindLookatRotation')} :Start here :Target target))
                ({N(advance,'SetActorRotation')} :NewRotation ({N(advance,'MakeRotator')} :Yaw (.yaw facing))))))))
      (:CastFailed))))''')
write(drop,f'''(fn HandleRobotDestroyed ()
  (if (> {G(parent,'ChipDropValue','self')} 0)
    (bind location ({N(drop,'GetActorLocation')}))
    ({N(drop,'SpawnActorfromClass')}
      :Class "{GAME}/BP_RA_Microchip.BP_RA_Microchip_C"
      :SpawnTransform ({N(drop,'MakeTransform')} :Location location)
      :CollisionHandlingOverride "AlwaysSpawn")))''')
e=unreal.BlueprintGraphEditor.get_graph_editor(drop)
spawn_node=next(n for n in e.list_all_nodes() if n.get_class().get_name()=='K2Node_SpawnActorFromClass')
drop_value=e.add_get_member_variable_node('ChipDropValue',parent.generated_class().get_path_name())
self_node=B.create_node(drop,'Variables|Getareferencetoself',unreal.IntPoint(0,500))
wire(self_node,'self',drop_value,'self');wire(drop_value,'ChipDropValue',spawn_node,'Value')
events=B.get_graph(ai,'EventGraph')
write(events,f'''(event EventBeginPlay {F(parent,'InitializeHealth',self='self')})
 (event EventTick (DeltaSeconds) {F(ai,'AdvanceRobotAI',Delta='DeltaSeconds')})''')

write(spawn,f'''(fn SpawnRobot ()
  (bind points {V(director,'SpawnPoints')})
  (bind count ({N(spawn,'Length','Utilities|Array')} :TargetArray points))
  (if (> count 0)
    (bind index (select (< {V(director,'SpawnIndex')} count) {V(director,'SpawnIndex')} 0))
    (bind location ({N(spawn,'Get(acopy)','Utilities|Array')} points index))
    (bind robot ({N(spawn,'SpawnActorfromClass')}
      :Class "{BASE}/BP_RA_HunterRobot.BP_RA_HunterRobot_C"
      :SpawnTransform ({N(spawn,'MakeTransform')} :Location location)
      :CollisionHandlingOverride "AdjustIfPossibleButDontSpawnIfColliding"))
    {S(director,'SpawnIndex','(+ index 1)')}))''')
write(tick,f'''(fn UpdateDirector ()
  (bind now ({N(tick,'GetGameTimeInSeconds')}))
  (if (and {V(director,'SpawningEnabled')} (>= now {V(director,'NextSpawnTime')}))
    {S(director,'NextSpawnTime','(+ now '+V(director,'SpawnInterval')+')')}
    (bind player ({core.node(tick,'CastToBP_RA_PlayerCharacter')} :Object ({N(tick,'GetPlayerCharacter')}))
      (:then
        (if (not {G(player,'PlayerDead','player')})
          (bind robots ({N(tick,'GetAllActorsOfClass')} :ActorClass "{BASE}/BP_RA_HunterRobot.BP_RA_HunterRobot_C"))
          (if (< ({N(tick,'Length','Utilities|Array')} :TargetArray robots) {V(director,'MaxAliveRobots')})
            {F(director,'SpawnRobot')})))
      (:CastFailed))))''')
events=B.get_graph(director,'EventGraph')
write(events,f'''(event EventTick (DeltaSeconds) {F(director,'UpdateDirector')})''')
finish([ai,director],'ai_build')

exec((Path(__file__).parent / 'setup_progression_arena.py').read_text(encoding='utf-8'))
