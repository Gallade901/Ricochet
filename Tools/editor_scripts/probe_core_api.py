import unreal, json
from pathlib import Path
from editor_toolset.toolsets.blueprint import BlueprintTools as B
bp = unreal.load_asset('/Game/TopDown/Blueprints/BP_TopDownCharacter')
g = B.get_graph(bp, 'EventGraph')
need = ['InputKey','GetInput','KeyDown','GetPlayerController','GetHitResult','SpawnActor','AddMovementInput','GetActor','SetActorRotation','MakeVector','MakeRotator','MakeTransform','GetWorldDelta','OnActor','OnComponent','Receive','SetTimer','GetVelocity','DestroyActor','SetLifeSpan','SetVelocity','AddActor','GetDistance','GetAllActors','CastTo','SetMicro','AddComponent']
all_types = B.find_node_types(g, '')
selected = [n for n in all_types if any(s.lower() in n.lower() for s in need)]
report = {'nodes':selected,'graph_editor':str(dir(unreal.BlueprintGraphEditor)),'dsl':B.read_graph_dsl(g)}
out=Path(unreal.Paths.project_saved_dir())/'Automation/core_probe.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('CORE_PROBE_OK')
