import unreal,json
from pathlib import Path
from editor_toolset.toolsets.blueprint import BlueprintTools as B
f=unreal.BlueprintFactory(); f.set_editor_property('parent_class',unreal.Character)
bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_CoreProbe','/Game/RicochetArena/TransientProbe',unreal.Blueprint,f)
g=B.get_graph(bp,'EventGraph')
for name,t in [('Microchips','int'),('NextFireTime','float'),('HasRicocheted','bool')]: B.add_variable(bp,name,t)
B.compile_blueprint(bp)
all_types=B.find_node_types(g,'')
keys=['EventTick','EventBeginPlay','EventActorBeginOverlap','IsInputKeyDown','GetHitResultUnderCursorbyChannel','GetPlayerController','AddMovementInput','GetActorLocation','GetActorForwardVector','SetActorRotation','FindLookatRotation','BreakHitResult','MakeVector','MakeRotator','MakeTransform','GetGameTimeinSeconds','SpawnActorfromClass','SetLifeSpan','DestroyActor','Add_IntInt','PrintString','GetMicrochips','SetMicrochips','GetNextFireTime','SetNextFireTime','GetHasRicocheted','SetHasRicocheted','OnProjectileBounce','GetWorldDeltaSeconds','ReflectVector','MirrorVectorbyNormal','DrawText','GetPlayerCharacter','SetActorLocation','GetForwardVector','ClampVectorSize','Normal','SelectFloat','ActorHasTag','GetVelocity','GetInstigator','IgnoreActorwhenMoving']
selected=[n for n in all_types if n.rsplit('|',1)[-1] in keys]
data={}
for n in selected:
 try:
  info=B.get_node_type_pins(g,n)
  data[n]={'in':[(p.name,p.type_id,p.value) for p in info.input_pins], 'out':[(p.name,p.type_id) for p in info.output_pins]}
 except Exception as e: data[n]=str(e)
data['event_names']=[str(e.name) for e in B.list_events(bp)]
data['more_types']=[n for n in all_types if any(s in n for s in ['Float|','Integer|','Normalization','Normalize','ProjectileBounce','EventTick','Overlap','DrawText']) and not n.startswith('Class|')]
Path(unreal.Paths.project_saved_dir()+'Automation/core_pins.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
