"""Author isolated Blueprint runtime checks for purchases, AI and 5s/30s phase timing."""
import sys
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).resolve().parent))
from progression_common import *

player=load(GAME+'/BP_RA_PlayerCharacter'); projectile=load(GAME+'/BP_RA_RicochetProjectile')
chip=load(GAME+'/BP_RA_Microchip'); mode=load(GAME+'/BP_RA_GameMode')
shop=load(BASE+'/WBP_RA_UpgradeShop');ai=load(BASE+'/BP_RA_HunterRobot');director=load(BASE+'/BP_RA_RobotDirector')
test=make('BP_RA_ProgressionTest',unreal.Actor)
for name,kind,value in [('AllPassed','bool',True),('Stage','int',0),('PhaseStart','float',0.0),
                        ('HealthBeforePhase','float',0.0),('StoppedLocation','Vector',unreal.Vector()),('ReadyTime','float',0.0)]:
    var(test,name,kind,value)
for name,cls in [('TestPlayer',player.generated_class()),('CloseRobot',ai.generated_class()),('FarRobot',ai.generated_class()),
                 ('TestDirector',director.generated_class()),('OriginalMaterial',unreal.MaterialInterface)]:
    objvar(test,name,cls)
functions={name:fn(test,name, [('Condition','bool'),('Label','string')] if name=='CheckProgression' else ())
           for name in ['CheckProgression','StartChecks','BeforePhase','DuringPhase','AfterPhase','AfterCooldown','StepChecks']}
B.compile_blueprint(test)
def C(g,condition,label):
    return F(test,'CheckProgression',Condition=condition,Label='"PROGRESSION_PASS '+label+'"')
def spawn(g,bp,x,y,z):
    return f'''({N(g,'SpawnActorfromClass')} :Class "{bp.generated_class().get_path_name()}"
     :SpawnTransform ({N(g,'MakeTransform')} :Location ({N(g,'MakeVector')} :X {x} :Y {y} :Z {z}))
     :CollisionHandlingOverride "AlwaysSpawn")'''
check=functions['CheckProgression']
write(check,f'''(fn CheckProgression (Condition Label)
 (if Condition ({N(check,'PrintString')} :InString Label :bPrintToLog true)
  (else {S(test,'AllPassed','false')}
   ({N(check,'PrintString')} :InString "PROGRESSION_FAIL" :bPrintToLog true)
   ({N(check,'PrintString')} :InString Label :bPrintToLog true))))''')
g=functions['StartChecks']
write(g,f'''(fn StartChecks ()
 (bind p ({core.node(g,'CastToBP_RA_PlayerCharacter')} :Object ({N(g,'GetPlayerCharacter')}))
  (:then
   {S(test,'TestPlayer','p')}
   {S(test,'OriginalMaterial','('+N(g,'GetMaterial','Rendering|Material')+' :self '+G(player,'BodyVisual','p')+')')}
   {F(player,'TryActivateStealth',self='p')}
   {C(g,'(not '+G(player,'StealthActive','p')+')','cannot_activate_unpurchased')}
   {S(player,'Microchips','100',target='p')}
   {F(player,'ToggleUpgradeShop',self='p')}
   {C(g,G(player,'ShopOpen','p'),'shop_opens')}
   {C(g,'('+N(g,'IsGamePaused')+')','shop_pauses_game')}
   (bind ui ({core.node(g,'CastToWBP_RA_UpgradeShop')} :Object {G(player,'ShopWidget','p')})
    (:then
     {F(shop,'BuyDamage',self='ui')}
     {C(g,'(== '+G(player,'Microchips','p')+' 95)','damage_price_deducted')}
     {C(g,'(== '+G(player,'WeaponDamage','p')+' 35.0)','damage_upgraded')}
     {F(shop,'BuyRate',self='ui')}
     {C(g,'(== '+G(player,'Microchips','p')+' 90)','fire_rate_price_deducted')}
     {C(g,'(and (> '+G(player,'FireInterval','p')+' 0.15) (< '+G(player,'FireInterval','p')+' 0.16))','fire_interval_reduced')}
     {F(shop,'BuyStealth',self='ui')}
     {C(g,G(player,'StealthOwned','p'),'stealth_purchased')}
     {C(g,'(== '+G(player,'Microchips','p')+' 75)','stealth_costs_fifteen')}
     {F(player,'TryPurchaseUpgrade',self='p',Choice='2')}
     {C(g,'(== '+G(player,'Microchips','p')+' 75)','duplicate_ability_purchase_rejected')}
     {S(player,'Microchips','0',target='p')}
     {F(player,'TryPurchaseUpgrade',self='p',Choice='0')}
     {C(g,'(and (not '+G(player,'LastPurchaseSucceeded','p')+') (== '+G(player,'DamageUpgradeLevel','p')+' 1))','insufficient_funds_rejected')}
     {S(player,'Microchips','75',target='p')}
     {F(player,'TryPurchaseUpgrade',self='p',Choice='99')}
     {C(g,'(== '+G(player,'Microchips','p')+' 75)','invalid_upgrade_rejected')}
     {F(shop,'CloseShop',self='ui')}
     {C(g,'(not '+G(player,'ShopOpen','p')+')','shop_closes')}
     {C(g,'(not ('+N(g,'IsGamePaused')+'))','shop_resumes_game')}
     ({N(g,'SetGamePaused')} :bPaused false)
     {F(player,'TryFire',self='p')}
     (bind bullets ({N(g,'GetAllActorsOfClass')} :ActorClass "{projectile.generated_class().get_path_name()}"))
     {C(g,'(== ('+N(g,'Length','Utilities|Array')+' :TargetArray bullets) 1)','upgraded_weapon_fires')}
     (bind bullet ({N(g,'Get(acopy)','Utilities|Array')} bullets 0))
     {C(g,'(== '+G(projectile,'Damage','bullet')+' 35.0)','upgrade_reaches_spawned_projectile')}
     (bind near {spawn(g,ai,110,0,85)})
     (bind far {spawn(g,ai,-700,0,85)})
     {S(test,'CloseRobot','near')}{S(test,'FarRobot','far')}
     {S(ai,'AttackDamage','0.0',target='far')}
     (bind spawner {spawn(g,director,0,0,500)})
     {S(test,'TestDirector','spawner')}
     {S(director,'NextSpawnTime','0.1',target='spawner')}
     {S(director,'SpawnInterval','0.5',target='spawner')}
     {S(director,'MaxAliveRobots','3',target='spawner')}
     ({N(g,'SetGlobalTimeDilation')} :TimeDilation 2.0))
    (:CastFailed
     ({N(g,'PrintString')} :InString "PROGRESSION_FAIL shop_widget_missing" :bPrintToLog true)
     ({N(g,'QuitGame')} :QuitPreference "Quit" :bIgnorePlatformRestrictions true))))
  (:CastFailed
   ({N(g,'PrintString')} :InString "PROGRESSION_FAIL player_missing" :bPrintToLog true)
   ({N(g,'QuitGame')} :QuitPreference "Quit" :bIgnorePlatformRestrictions true))))''')

g=functions['BeforePhase'];p=V(test,'TestPlayer');far=V(test,'FarRobot')
write(g,f'''(fn BeforePhase ()
 (bind p {p})(bind far {far})
 {C(g,'(< '+G(player,'PlayerHealth','p')+' 100.0)','robot_attacks_player')}
 (bind location ({N(g,'GetActorLocation')} :self far))
 {C(g,'(> (.x location) -650.0)','robot_navigates_toward_player')}
 (bind robots ({N(g,'GetAllActorsOfClass')} :ActorClass "{ai.generated_class().get_path_name()}"))
 {C(g,'(== ('+N(g,'Length','Utilities|Array')+' :TargetArray robots) 3)','spawning_respects_alive_limit')}
 {S(director,'SpawningEnabled','false',target=V(test,'TestDirector'))}
 (for robot robots {S(ai,'AttackDamage','0.0',target='robot')})
 {S(test,'HealthBeforePhase',G(player,'PlayerHealth','p'))}
 {F(player,'TryActivateStealth',self='p')}
 {C(g,G(player,'StealthActive','p'),'stealth_activates')}
 {S(test,'PhaseStart','('+N(g,'GetGameTimeInSeconds')+')')}
 {S(test,'ReadyTime',G(player,'NextStealthReady','p'))}
 {S(test,'StoppedLocation','location')}
 {C(g,'(== '+G(player,'NextStealthReady','p')+' (+ '+V(test,'PhaseStart')+' 30.0))','cooldown_is_thirty_seconds')}
 (bind material ({N(g,'GetMaterial','Rendering|Material')} :self {G(player,'BodyVisual','p')}))
 {C(g,'(== material '+G(player,'PhaseMaterial','p')+')','phase_material_applied')}
 {F(player,'TryActivateStealth',self='p')}
 {C(g,'(== '+G(player,'NextStealthReady','p')+' '+V(test,'ReadyTime')+')','cannot_restart_active_ability')}
 {S(test,'Stage','1')})''')
g=functions['DuringPhase']
write(g,f'''(fn DuringPhase ()
 (bind p {V(test,'TestPlayer')})(bind far {V(test,'FarRobot')})
 {C(g,G(player,'StealthActive','p'),'stealth_still_active_before_five_seconds')}
 {C(g,'(not '+G(ai,'IsPursuing','far')+')','robots_drop_stealthed_target')}
 (bind moved (- ({N(g,'GetActorLocation')} :self far) {V(test,'StoppedLocation')}))
 {C(g,'(< ('+N(g,'VectorLength','Math|Vector')+' :A moved) 10.0)','robot_stops_moving_during_phase')}
 {F(player,'ReceiveRobotDamage',self='p',Amount='25.0')}
 {C(g,'(== '+G(player,'PlayerHealth','p')+' '+V(test,'HealthBeforePhase')+')','phase_blocks_melee_damage')}
 {S(test,'Stage','2')})''')
g=functions['AfterPhase']
write(g,f'''(fn AfterPhase ()
 (bind p {V(test,'TestPlayer')})
 {C(g,'(not '+G(player,'StealthActive','p')+')','phase_ends_after_five_seconds')}
 (bind material ({N(g,'GetMaterial','Rendering|Material')} :self {G(player,'BodyVisual','p')}))
 {C(g,'(== material '+V(test,'OriginalMaterial')+')','original_material_restored')}
 {F(player,'TryActivateStealth',self='p')}
 {C(g,'(not '+G(player,'StealthActive','p')+')','cooldown_blocks_early_activation')}
 {C(g,G(ai,'IsPursuing',V(test,'FarRobot')),'robots_resume_pursuit')}
 {S(test,'Stage','3')})''')
g=functions['AfterCooldown']
write(g,f'''(fn AfterCooldown ()
 (bind p {V(test,'TestPlayer')})
 {F(player,'TryActivateStealth',self='p')}
 {C(g,G(player,'StealthActive','p'),'ability_ready_again_after_thirty_seconds')}
 {F(player,'EndStealth',self='p')}
 {F(player,'ReceiveRobotDamage',self='p',Amount='1000.0')}
 {C(g,G(player,'PlayerDead','p'),'lethal_robot_damage_kills_player')}
 {F(player,'TryActivateStealth',self='p')}
 {C(g,'(not '+G(player,'StealthActive','p')+')','dead_player_cannot_activate')}
 {S(test,'Stage','4')}
 (if {V(test,'AllPassed')}
  ({N(g,'PrintString')} :InString "PROGRESSION_RUNTIME_VERIFIED" :bPrintToLog true)
  (else ({N(g,'PrintString')} :InString "PROGRESSION_RUNTIME_FAILED" :bPrintToLog true)))
 ({N(g,'QuitGame')} :QuitPreference "Quit" :bIgnorePlatformRestrictions true))''')
g=functions['StepChecks']
write(g,f'''(fn StepChecks ()
 (bind now ({N(g,'GetGameTimeInSeconds')}))
 (if (and (== {V(test,'Stage')} 0) (> now 3.5)) {F(test,'BeforePhase')}
  (elif (and (== {V(test,'Stage')} 1) (> now (+ {V(test,'PhaseStart')} 2.0))) {F(test,'DuringPhase')}
   (elif (and (== {V(test,'Stage')} 2) (> now (+ {V(test,'PhaseStart')} 5.3))) {F(test,'AfterPhase')}
    (elif (and (== {V(test,'Stage')} 3) (> now (+ {V(test,'PhaseStart')} 30.1))) {F(test,'AfterCooldown')})))))''')
# Extended economy and obstacle checks are kept as a reusable Blueprint DSL spec.
import re
parent=load(ROBOT+'/BP_RA_TestRobot')
source=(Path(__file__).parents[1]/'blueprint_specs/Progression_BeforePhase.sexpr').read_text(encoding='utf-8')
for key in set(re.findall(r'Local\|[^ \n()]+',source)):
    _,owner,name=key.split('|');bp=core.ASSETS[owner]
    core.LOCAL_NODES[key]=('get' if name.startswith('Get') else 'set' if name.startswith('Set') else 'call',bp,name[3:] if name.startswith(('Get','Set')) else name)
write(functions['BeforePhase'],source)
events=B.get_graph(test,'EventGraph')
write(events,f'''(event EventBeginPlay {F(test,'StartChecks')})
 (event EventTick (DeltaSeconds) {F(test,'StepChecks')})''')
finish([test],'test_build')

exec((Path(__file__).parent / 'setup_progression_test_map.py').read_text(encoding='utf-8'))
