"""Place Adam and Eve in the open Day 1 garden. Idempotent.

Run after level_build.build. The garden plan does not list these actors, so a
later garden rebuild drops them and run_all puts them back.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import characters_logic
import garden_logic

_WORLD = None


def _ue(ue):
    if ue is not None:
        return ue
    import unreal

    return unreal


def _subsystem(ue):
    return ue.get_editor_subsystem(ue.EditorActorSubsystem)


def _vec(ue, x, y, z):
    return ue.Vector(float(x), float(y), float(z))


def _rot(ue, pitch=0.0, yaw=0.0, roll=0.0):
    return ue.Rotator(float(pitch), float(yaw), float(roll))


def _by_label(ue):
    found = {}
    for actor in _subsystem(ue).get_all_level_actors():
        found[actor.get_actor_label()] = actor
    return found


def _ensure_map(ue, map_path):
    if ue.EditorAssetLibrary.does_asset_exist(map_path):
        ue.EditorLevelLibrary.load_level(map_path)
    else:
        ue.EditorLevelLibrary.new_level(map_path)


def _place(actor, ue, spec):
    actor.set_actor_label(spec["label"])
    actor.set_actor_location(_vec(ue, spec["x"], spec["y"], spec["z"]), False, True)
    actor.set_actor_rotation(_rot(ue, 0.0, spec.get("yaw", 0.0), 0.0), True)
    scale = spec["scale"]
    actor.set_actor_scale3d(_vec(ue, scale[0], scale[1], scale[2]))
    asset = ue.EditorAssetLibrary.load_asset(spec["mesh"])
    comp = actor.get_component_by_class(ue.StaticMeshComponent)
    comp.set_static_mesh(asset)
    actor.set_editor_property("tags", list(spec["tags"]))


def _apply(ue, world):
    ue = _ue(ue)
    _ensure_map(ue, world["map"])
    sub = _subsystem(ue)
    actors = _by_label(ue)
    for spec in characters_logic.actor_specs(world):
        actor = actors.get(spec["label"])
        if actor is None:
            actor = sub.spawn_actor_from_class(
                ue.StaticMeshActor,
                _vec(ue, spec["x"], spec["y"], spec["z"]),
                _rot(ue, 0.0, spec["yaw"], 0.0),
            )
            actors[spec["label"]] = actor
        _place(actor, ue, spec)
    return world


def spawn_people(ue=None, world=None):
    """Spawn or move Adam and Eve, then save the level."""
    global _WORLD
    world = characters_logic.new_garden() if world is None else world
    if world["map"] != garden_logic.MAP_PATH:
        raise ValueError(f"people belong on {garden_logic.MAP_PATH}")
    _WORLD = world
    ue = _ue(ue)
    _apply(ue, world)
    ue.EditorLevelLibrary.save_current_level()
    return world


def step_day(dt, ue=None, world=None):
    """Advance the day and move the spawned people. Does not save."""
    global _WORLD
    if world is None:
        world = _WORLD if _WORLD is not None else characters_logic.new_garden()
    _WORLD = world
    characters_logic.advance(world, dt)
    _apply(_ue(ue), world)
    return world


def address(who, heard="", payload=None, ue=None, world=None):
    """Record a dialogue hook. With no voice payload, the scripted line is used."""
    global _WORLD
    if world is None:
        world = _WORLD if _WORLD is not None else characters_logic.new_garden()
    _WORLD = world
    result = characters_logic.address(world, who, heard, payload)
    _apply(_ue(ue), world)
    return result


def main(ue=None):
    return spawn_people(ue=ue)


if __name__ == "__main__":
    main()
