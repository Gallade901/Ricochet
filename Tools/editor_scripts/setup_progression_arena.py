import sys
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).resolve().parent))
from progression_common import *
ai=load(BASE+'/BP_RA_HunterRobot')
director=load(BASE+'/BP_RA_RobotDirector')
# Extend only the exact existing prototype level, after checking its package.
levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
path=GAME+'/Lvl_RicochetPrototype'
assert levels.load_level(path)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_path_name()==path+'.Lvl_RicochetPrototype'
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert not [a for a in actors.get_all_level_actors() if a.get_class()==director.generated_class()]
instance=actors.spawn_actor_from_class(director.generated_class(),unreal.Vector(0,0,400))
instance.set_actor_label('RobotDirector_ContinuousSpawn')
bounds=actors.spawn_actor_from_class(unreal.NavMeshBoundsVolume,unreal.Vector(0,0,100))
bounds.set_actor_label('ArenaNavigationBounds')
bounds.set_actor_scale3d(unreal.Vector(18,15,3))
assert bounds.get_actor_bounds(False)[1].x > 1000, 'Navigation volume has no bounds'
setup_navigation(world,bounds)
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()==path+'.Lvl_RicochetPrototype'
assert levels.save_current_level()
unreal.log('AI_NAVIGATION_AND_SPAWNING_VERIFIED')
