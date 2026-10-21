import unreal,json
from pathlib import Path
from editor_toolset.toolsets.blueprint import BlueprintTools as B
bp=unreal.load_asset('/Game/RicochetArena/CoreMechanics/BP_RA_RicochetProjectile')
actor=unreal.get_default_object(bp.generated_class())
result={'graphs':{g.get_name(): B.read_graph_dsl(g) for g in B.list_graphs(bp)}, 'umg_classes':[n for n in dir(unreal) if 'UMGTool' in n]}
result['components']=[{'name':c.get_name(),'class':c.get_class().get_name()} for c in actor.get_components_by_class(unreal.ActorComponent)]
result['umg_api']=str(dir(unreal.UMGToolSet)) if hasattr(unreal,'UMGToolSet') else ''
if hasattr(unreal,'UMGToolSet'):
 tool=unreal.get_default_object(unreal.UMGToolSet.static_class())
 w=tool.call_method('CreateWidgetBlueprint', args=('/Game/RicochetArena/Robot','WBP_Probe',unreal.UserWidget.static_class()))
 info=tool.call_method('AddWidget',args=(w,unreal.ProgressBar.static_class(),'HealthProgress',None,-1))
 result['widget_probe']=str(info)
 result['widget_props']=str(dir(info.widget))
Path(unreal.Paths.project_saved_dir()+'Automation/robot_probe.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
unreal.log('ROBOT_PROBE_VERIFIED')
