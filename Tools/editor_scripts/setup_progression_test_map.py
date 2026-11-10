import sys
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).resolve().parent))
from progression_common import *
mode=load(GAME+'/BP_RA_GameMode')
test=load(BASE+'/BP_RA_ProgressionTest')
path=BASE+'/Lvl_ProgressionAutomation'
exists=unreal.EditorAssetLibrary.does_asset_exist(path)
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);assert (levels.load_level(path) if exists else levels.new_level(path))
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_path_name()==path+'.Lvl_ProgressionAutomation'
world.get_world_settings().set_editor_property('default_game_mode',mode.generated_class())
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert not [a for a in actors.get_all_level_actors() if a.get_class()==test.generated_class()], 'Map already configured; use runtime checks'
floor=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(0,0,-25))
floor.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
floor.static_mesh_component.set_collision_profile_name('BlockAll');floor.set_actor_scale3d(unreal.Vector(40,40,0.5))
actors.spawn_actor_from_class(unreal.PlayerStart,unreal.Vector(0,0,96))
actors.spawn_actor_from_class(test.generated_class(),unreal.Vector(0,0,400))
bounds=actors.spawn_actor_from_class(unreal.NavMeshBoundsVolume,unreal.Vector(0,0,100))
bounds.set_actor_scale3d(unreal.Vector(20,20,3));assert bounds.get_actor_bounds(False)[1].x > 1000
obstacle=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(-350,0,150))
obstacle.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
obstacle.static_mesh_component.set_collision_profile_name('BlockAll')
obstacle.set_actor_scale3d(unreal.Vector(0.5,4,3))
obstacle.set_actor_label('NavigationTestObstacle')
setup_navigation(world,bounds)
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()==path+'.Lvl_ProgressionAutomation'
assert levels.save_current_level()
unreal.log('PROGRESSION_TESTS_AUTHORED_VERIFIED')
