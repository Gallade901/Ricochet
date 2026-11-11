"""Create isolated runtime regression checks; never overwrite existing assets."""
import sys
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).resolve().parent))
from progression_common import *
player=load(GAME+'/BP_RA_PlayerCharacter');chip=load(GAME+'/BP_RA_Microchip');bullet=load(GAME+'/BP_RA_RicochetProjectile');shop=load(BASE+'/WBP_RA_UpgradeShop')
mode=load(GAME+'/BP_RA_GameMode')
NATIVE['MouseCaptureAsInt']='/Script/Engine.KismetMathLibrary:Conv_ByteToInt'
test=make('BP_RA_InputPickupTest',unreal.Actor)
for name,kind,value in [('AllPassed','bool',True),('Stage','int',0),('Hardware','bool',False),('PressCount','int',0),('WasPressed','bool',False),('ShotsBefore','int',0),('PressTime','float',0.0)]:var(test,name,kind,value)
for name,bp in [('TestPlayer',player),('TestBullet',bullet),('TestChip',chip)]:objvar(test,name,bp.generated_class())
check=fn(test,'Check',[('Condition','bool'),('Label','string')]);start=fn(test,'StartChecks');step=fn(test,'StepChecks');end=fn(test,'FinishChecks');hardware=fn(test,'HardwareChecks')
B.compile_blueprint(test)
def C(g,cond,label):return F(test,'Check',Condition=cond,Label='"INPUT_PICKUP_PASS '+label+'"')
def spawn(g,bp,x,y,z):return f'({N(g,"SpawnActorfromClass")} :Class "{bp.generated_class().get_path_name()}" :SpawnTransform ({N(g,"MakeTransform")} :Location ({N(g,"MakeVector")} :X {x} :Y {y} :Z {z})) :CollisionHandlingOverride "AlwaysSpawn")'
write(check,f'''(fn Check (Condition Label)
 (if Condition ({N(check,'PrintString')} :InString Label :bPrintToLog true)
  (else {S(test,'AllPassed','false')} ({N(check,'PrintString')} :InString "INPUT_PICKUP_FAIL" :bPrintToLog true) ({N(check,'PrintString')} :InString Label :bPrintToLog true))))''')
g=start;p=V(test,'TestPlayer');text=[]
for i in range(3):
 text.append(f'''{F(player,'ToggleUpgradeShop',self='p')}
 {C(g,G(player,'ShopOpen','p'),'shop_opens_'+str(i))}
 {F(player,'ToggleUpgradeShop',self='p')}
 {C(g,'(not '+G(player,'ShopOpen','p')+')','shop_closes_'+str(i))}
 {C(g,'(== '+K('MouseCaptureAsInt',InByte='('+N(g,'GetViewportMouseCaptureMode')+')')+' 2)','initial_mouse_down_enabled_'+str(i))}''')
write(g,f'''(fn StartChecks ()
 (bind p ({core.node(g,'CastToBP_RA_PlayerCharacter')} :Object ({N(g,'GetPlayerCharacter')}))
 (:then
 {S(test,'TestPlayer','p')}
 {S(test,'Hardware','('+N(g,'Contains','Utilities|String')+' :SearchIn ('+N(g,'GetCommandLine')+') :Substring "InputHardware")')}
 {''.join(text)}
 {S(player,'Microchips','0',target='p')}
 (bind ch {spawn(g,chip,0,500,85)}){S(test,'TestChip','ch')}
 (bind b {spawn(g,bullet,-300,500,85)}){S(test,'TestBullet','b')}
 {C(g,K('IsObjectValid',Object='b'),'bullet_spawned_outside_chip')}
 {C(g,'(not '+G(bullet,'HasRicocheted','b')+')','bullet_starts_unricocheted')}
 {S(test,'Stage','1')})))''')
g=step;p=V(test,'TestPlayer');b=V(test,'TestBullet')
write(g,f'''(fn StepChecks ()
 (bind now ({N(g,'GetGameTimeInSeconds')}))
 (if (and (== {V(test,'Stage')} 1) (> now 0.45))
  {C(g,K('IsObjectValid',Object=b),'bullet_survives_chip_passage')}
  (if ({K('IsObjectValid',Object=b)[1:-1]})
   (bind (x y z) ({N(g,'BreakVector')} :InVec ({N(g,'GetActorLocation')} :self {b})))
   {C(g,'(> x 150.0)','bullet_passes_beyond_chip')}
   {C(g,'(not '+G(bullet,'HasRicocheted',b)+')','chip_does_not_count_as_wall')})
  {C(g,K('IsObjectValid',Object=V(test,'TestChip')),'bullet_does_not_collect_chip')}
  (bind pickup {spawn(g,chip,0,0,85)})
  {S(test,'Stage','2')})
 (if (and (== {V(test,'Stage')} 2) (> now 0.8))
  {C(g,'(== '+G(player,'Microchips',p)+' 1)','pawn_still_collects_chip_once')}
  {S(test,'Stage','3')}
  (if {V(test,'Hardware')}
   ({N(g,'PrintString')} :InString "INPUT_HARDWARE_READY" :bPrintToLog true)
   (else {F(test,'FinishChecks')})))
 (if (and (== {V(test,'Stage')} 3) {V(test,'Hardware')}) {F(test,'HardwareChecks')}))''')
g=end
write(g,f'''(fn FinishChecks ()
 {S(test,'Stage','4')}
 (if {V(test,'AllPassed')} ({N(g,'PrintString')} :InString "INPUT_PICKUP_RUNTIME_VERIFIED" :bPrintToLog true)
  (else ({N(g,'PrintString')} :InString "INPUT_PICKUP_RUNTIME_FAILED" :bPrintToLog true)))
 ({N(g,'QuitGame')} :QuitPreference "Quit" :bIgnorePlatformRestrictions true))''')
g=hardware;p=V(test,'TestPlayer')
write(g,f'''(fn HardwareChecks ()
 (bind pc ({N(g,'GetPlayerController','Game')}))
 (bind down ({N(g,'IsInputKeyDown')} :self pc :Key "LeftMouseButton"))
 (bind now ({N(g,'GetGameTimeInSeconds')}))
 (if (and down (not {V(test,'WasPressed')}))
  {S(test,'ShotsBefore',G(player,'ShotsFired',p))}{S(test,'PressTime','now')}
  {S(test,'PressCount','(+ '+V(test,'PressCount')+' 1)')}
  ({N(g,'PrintString')} :InString "INPUT_HARDWARE_PRESS" :bPrintToLog true))
 (if (and (not down) {V(test,'WasPressed')})
  {C(g,'(>= (- '+G(player,'ShotsFired',p)+' '+V(test,'ShotsBefore')+') 3)','held_mouse_fires_repeatedly')}
  ({N(g,'PrintString')} :InString "INPUT_HARDWARE_RELEASE" :bPrintToLog true)
  (if (>= {V(test,'PressCount')} 6) {F(test,'FinishChecks')}))
 {S(test,'WasPressed','down')})''')
events=B.get_graph(test,'EventGraph');write(events,f'''(event EventBeginPlay {F(test,'StartChecks')}) (event EventTick (DeltaSeconds) {F(test,'StepChecks')})''')
finish([test],'input_pickup_test_build')
path=BASE+'/Lvl_InputPickupAutomation';assert not unreal.EditorAssetLibrary.does_asset_exist(path)
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);assert levels.new_level(path)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();world.get_world_settings().set_editor_property('default_game_mode',mode.generated_class())
a=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
floor=a.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(0,0,-25));floor.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'));floor.set_actor_scale3d(unreal.Vector(40,40,0.5));floor.static_mesh_component.set_collision_profile_name('BlockAll')
a.spawn_actor_from_class(unreal.PlayerStart,unreal.Vector(0,0,96));a.spawn_actor_from_class(test.generated_class(),unreal.Vector(0,0,400))
a.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,500),unreal.Rotator(-60,0,0))
assert levels.save_current_level()
unreal.log('INPUT_PICKUP_TESTS_AUTHORED_VERIFIED')
