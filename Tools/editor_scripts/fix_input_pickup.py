"""Patch existing saved assets through UE editor; preserve all existing nodes."""
import sys,datetime,shutil,json
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).resolve().parent))
from progression_common import *
root=Path(unreal.Paths.project_dir()).resolve();out=root/'Saved/Automation/InputPickupFix';out.mkdir(parents=True,exist_ok=True)
# Never save another editor's unsaved packages.
dirty=unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()+unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
assert not dirty, [p.get_name() for p in dirty]
player=load(GAME+'/BP_RA_PlayerCharacter');chip=load(GAME+'/BP_RA_Microchip')
backup=root/'Saved/AutomationBackups'/('InputPickupFix_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
for bp in [player,chip]:
 relative=Path('Content')/(bp.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset')
 target=backup/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/relative,target)
(out/'backup_path.txt').write_text(str(backup),encoding='utf-8')
components=[]
for h in unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem).k2_gather_subobject_data_for_blueprint(chip):
 o=unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h))
 if isinstance(o,unreal.SphereComponent) and o.get_name().startswith('PickupSphere'):
  o.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
  o.set_collision_response_to_all_channels(unreal.CollisionResponseType.ECR_IGNORE)
  o.set_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN,unreal.CollisionResponseType.ECR_OVERLAP)
  o.set_editor_property('generate_overlap_events',True);components.append(o.get_name())
assert len(components)==1,components
# Append nodes after the actual close branch; never replace the existing graph.
g=B.get_graph(player,'ToggleUpgradeShop');e=unreal.BlueprintGraphEditor.get_graph_editor(g)
nodes=e.list_all_nodes();old_names=[n.get_name() for n in nodes]
game_only=[n for n in nodes if 'SetInputModeGameOnly' in n.get_node_title().replace(' ','').replace('_','')];assert len(game_only)==1
assert not [n for n in nodes if n.get_node_title().replace(' ','').replace('_','')=='SetViewportMouseCaptureMode'],'Already patched; inspect rather than duplicate'
source=pin(game_only[0],'then',True);previous=list(source.list_connected_pins())
capture=e.add_call_function_node('/Script/Engine.GameplayStatics:SetViewportMouseCaptureMode')
assert capture
capture.set_node_pos(unreal.IntPoint(1500,0))
assert pin(capture,'MouseCaptureMode').set_pin_value('CapturePermanently_IncludingInitialMouseDown')
focus=e.add_call_function_node('/Script/UMG.WidgetBlueprintLibrary:SetFocusToGameViewport');assert focus
focus.set_node_pos(unreal.IntPoint(1800,0))
for dest in previous: assert source.break_single_pin_link(dest)
wire(game_only[0],'then',capture,'execute');wire(capture,'then',focus,'execute')
for dest in previous: assert pin(focus,'then',True).try_create_connection(dest)
assert set(old_names).issubset({n.get_name() for n in e.list_all_nodes()})
finish([chip,player],'input_pickup_patch')
(out/'patch.json').write_text(json.dumps({'backup':str(backup),'pickup_components':components,'existing_player_nodes_preserved':True,'capture_mode':'CapturePermanently_IncludingInitialMouseDown'},indent=2),encoding='utf-8')
unreal.log('INPUT_PICKUP_PATCH_VERIFIED')
