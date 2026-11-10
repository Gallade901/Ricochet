"""Editor-only Blueprint authoring adapters. Never used by runtime gameplay."""
import json
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as B, ContainerType
from editor_toolset.toolsets.blueprint_dsl import Transpiler
import build_core_mechanics as core

BASE = '/Game/RicochetArena/Progression'
GAME = '/Game/RicochetArena/CoreMechanics'
ROBOT = '/Game/RicochetArena/Robot'
OUT = Path(unreal.Paths.project_saved_dir()) / 'Automation/Progression'
OUT.mkdir(parents=True, exist_ok=True)
core.BASE = BASE
core.OUT = OUT
NATIVE = {'IsObjectValid': '/Script/Engine.KismetSystemLibrary:IsValid'}


def K(name, **args):
    assert name in NATIVE
    return '(Native|' + name + ''.join(' :' + k + ' ' + v for k,v in args.items()) + ')'


def create_node(g, identifier, position):
    if identifier.startswith('Native|'):
        n=unreal.BlueprintGraphEditor.get_graph_editor(g).add_call_function_node(NATIVE[identifier.split('|',1)[1]])
        assert n,identifier
        n.set_node_pos(position)
        return n
    return core.create_node(g,identifier,position)


def load(path):
    bp = unreal.load_asset(path)
    assert isinstance(bp, unreal.Blueprint), path
    core.ASSETS[bp.get_name()] = bp
    return bp


def make(name, parent):
    assert not unreal.EditorAssetLibrary.does_asset_exist(BASE + '/' + name), name
    bp = B.create(BASE, name, parent.static_class() if isinstance(parent, type) else parent)
    core.ASSETS[name] = bp
    return bp


def N(g, suffix, category=None):
    candidates = [n for n in B.find_node_types(g, suffix)
                  if n.rsplit('|', 1)[-1].lower() == suffix.lower()]
    if category:
        candidates = [n for n in candidates if n.lower().startswith(category.lower() + '|')]
    assert len(candidates) == 1, (suffix, category, candidates)
    return candidates[0]


def V(bp, name):
    key = 'Local|' + bp.get_name() + '|Get' + name
    core.LOCAL_NODES[key] = ('get', bp, name)
    return '(' + key + ')'


def S(bp, name, value, target=None):
    key = 'Local|' + bp.get_name() + '|Set' + name
    core.LOCAL_NODES[key] = ('set', bp, name)
    return '(' + key + (' :self ' + target if target else '') + ' :' + name + ' ' + value + ')'


def F(bp, name, **args):
    key = 'Local|' + bp.get_name() + '|' + name
    core.LOCAL_NODES[key] = ('call', bp, name)
    return '(' + key + ''.join(' :' + k + ' ' + v for k, v in args.items()) + ')'


def G(bp, name, target):
    return V(bp, name)[:-1] + ' :self ' + target + ')'


def fn(bp, name, inputs=(), outputs=()):
    assert not unreal.BlueprintEditorLibrary.find_graph(bp, name), name
    return core.function(bp, name, inputs, outputs)


def var(bp, name, kind, value=None):
    core.var(bp, name, kind, value)


def objvar(bp, name, cls):
    B.add_object_variable(bp, name, cls.static_class() if isinstance(cls, type) else cls)


def write(g, text):
    Transpiler(g, create_node, B.connect_pins, B._get_node_info,
               B.set_pin_value, lambda graph: B.find_nodes(graph),
               delete_node_fn=B.delete_node,
               find_node_types_fn=lambda f: B.find_node_types(g, f)).transpile(text)
    B.compile_blueprint(g.get_outer())
    (OUT / (g.get_outer().get_name() + '_' + g.get_name() + '.sexpr')).write_text(text, encoding='utf-8')


def pin(n, name, out=False):
    p = unreal.BlueprintEditorLibrary.find_output_pin(n, name) if out else unreal.BlueprintEditorLibrary.find_input_pin(n, name)
    assert p.is_valid(), (n.get_name(), name, out)
    return p


def wire(a, an, b, bn):
    assert pin(a, an, True).try_create_connection(pin(b, bn)), (an, bn)


def call_node(g, bp, name):
    n = unreal.BlueprintGraphEditor.get_graph_editor(g).add_call_function_node(bp.generated_class().get_path_name() + ':' + name)
    assert n, name
    return n


def finish(assets, report_name):
    report = {}
    for bp in assets:
        B.compile_blueprint(bp, warnings_as_errors=True)
        assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
        report[bp.get_name()] = {'status': str(bp.get_editor_property('status')),
                                'graphs': {g.get_name(): len(unreal.BlueprintGraphEditor.get_graph_editor(g).list_all_nodes()) for g in B.list_graphs(bp)}}
    (OUT / (report_name + '.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')


def setup_navigation(world, bounds):
    # RuntimeGeneration=Dynamic is configured in DefaultEngine.ini. Let the
    # navigation system create/register data with its supported agent config.
    nav=unreal.NavigationSystemV1.get_navigation_system(world)
    assert nav, 'Missing navigation system'
    nav.on_navigation_bounds_updated(bounds)
    return [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
            if isinstance(a,unreal.RecastNavMesh)]
