"""Read-only asset verification in a fresh Unreal Editor process."""
import json
from pathlib import Path
import unreal

asset = "/Game/RicochetArena/Blueprints/Test/BP_TestCube"
blueprint = unreal.load_asset(asset)
assert isinstance(blueprint, unreal.Blueprint), "Missing saved Blueprint"
generated = blueprint.generated_class()
assert generated and unreal.MathLibrary.class_is_child_of(generated, unreal.StaticMeshActor)
defaults = unreal.get_default_object(generated)
mesh = defaults.get_editor_property("static_mesh_component").get_editor_property("static_mesh")
assert mesh and mesh.get_path_name() == "/Engine/BasicShapes/Cube.Cube"
status = str(blueprint.get_editor_property("status"))
assert "ERROR" not in status.upper(), status
report = {"asset": asset, "fresh_process_loaded": True,
          "generated_class": generated.get_path_name(),
          "mesh": mesh.get_path_name(), "blueprint_status": status}
path = Path(unreal.Paths.project_saved_dir()) / "Automation/BP_TestCube_reload.json"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report, indent=2), encoding="utf-8")
unreal.log("RICOCHET_RELOAD_VERIFIED " + json.dumps(report))
