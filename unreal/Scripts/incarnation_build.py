"""Place the incarnation maps with editor Python. Idempotent.

The Day 1 garden map is not opened or saved here. Walk and underworld are
their own maps. Placeholder engine shapes only. The crucifixion beat is an
absence marker: no body, no spectacle.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from incarnation import PHASES, load_rules, plan_phase

CLASS_NAMES = {
    "static": "StaticMeshActor",
    "directional_light": "DirectionalLight",
    "fog": "ExponentialHeightFog",
    "player_start": "PlayerStart",
    "marker": "TargetPoint",
}

MESH = {
    "plane": "/Engine/BasicShapes/Plane",
    "sphere": "/Engine/BasicShapes/Sphere",
}

LABEL_PREFIX = "Elyon.Incarnation."


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


def _byte_color(ue, rgba):
    """FColor properties (light_color) take unreal.Color channels as 0-255 ints."""
    return ue.Color(*(int(round(float(channel) * 255.0)) for channel in rgba))


def _linear_color(ue, rgba):
    """FLinearColor properties take unreal.LinearColor channels as 0-1 floats."""
    red, green, blue, alpha = rgba
    return ue.LinearColor(float(red), float(green), float(blue), float(alpha))


def _static(label, mesh, x, y, z, scale, yaw=0.0, tags=None):
    sx, sy, sz = scale
    return {
        "label": label,
        "kind": "static",
        "mesh": MESH[mesh],
        "x": float(x),
        "y": float(y),
        "z": float(z),
        "yaw": float(yaw),
        "scale": (float(sx), float(sy), float(sz)),
        "tags": list(tags or []),
    }


def _marker(label, x, y, z, tags):
    return {
        "label": label,
        "kind": "marker",
        "x": float(x),
        "y": float(y),
        "z": float(z),
        "tags": list(tags),
    }


def plan_level(state, rules=None):
    """Actors for this phase. Sky and ascended do not open a map."""
    rules = rules or load_rules()
    phase = state["phase"]
    if phase not in PHASES:
        raise ValueError(f"unknown phase: {phase}")
    show = plan_phase(phase)
    if show is None:
        return {"map": None, "phase": phase, "light": None, "actors": []}
    presentation = rules["presentation"]
    light = presentation["lights"][show]
    if show == "underworld":
        map_path = presentation["underworldMap"]
    else:
        map_path = presentation["walkMap"]
    actors = [
        _static(LABEL_PREFIX + "Ground", "plane", 0.0, 0.0, 0.0, (40.0, 40.0, 1.0)),
        {
            "label": LABEL_PREFIX + "Sun",
            "kind": "directional_light",
            "x": 0.0,
            "y": 0.0,
            "z": 2000.0,
            "pitch": light["sun_pitch"],
            "yaw": light["sun_yaw"],
            "tags": [],
        },
        {"label": LABEL_PREFIX + "Fog", "kind": "fog", "x": 0.0, "y": 0.0, "z": 0.0, "tags": []},
    ]
    start = presentation["playerStart"]
    actors.append(
        {
            "label": LABEL_PREFIX + "PlayerStart",
            "kind": "player_start",
            "x": start["x"],
            "y": start["y"],
            "z": start["z"],
            "yaw": start["yaw"],
            "tags": ["human-form"],
        }
    )
    if show in ("walking", "returned"):
        pawn = presentation["pawn"]
        actors.append(
            _static(
                LABEL_PREFIX + "Pawn",
                "sphere",
                pawn["x"],
                pawn["y"],
                pawn["z"],
                (0.9, 0.9, 1.8),
                tags=["human-form"],
            )
        )
    if show == "crucifixion":
        actors.append(_marker(LABEL_PREFIX + "Absence", 0.0, 0.0, 40.0, ["absence"]))
    if show == "underworld":
        lost = state.get("lost") or []
        for index, figure in enumerate(lost):
            x = figure.get("x", (index - 1) * 220.0)
            y = figure.get("y", 180.0)
            actors.append(
                _marker(
                    LABEL_PREFIX + "Listener." + figure["id"],
                    x,
                    y,
                    40.0,
                    ["listener", figure["role"]],
                )
            )
    return {"map": map_path, "phase": phase, "light": light, "actors": actors}


def planned_labels(plan):
    return [actor["label"] for actor in plan["actors"]]


def stale_labels(existing, planned):
    keep = set(planned)
    return sorted(
        label for label in existing if label.startswith(LABEL_PREFIX) and label not in keep
    )


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
    actor.set_actor_rotation(
        _rot(ue, spec.get("pitch", 0.0), spec.get("yaw", 0.0), 0.0),
        True,
    )
    scale = spec.get("scale")
    if scale:
        actor.set_actor_scale3d(_vec(ue, scale[0], scale[1], scale[2]))
    mesh = spec.get("mesh")
    if mesh:
        asset = ue.EditorAssetLibrary.load_asset(mesh)
        comp = actor.get_component_by_class(ue.StaticMeshComponent)
        comp.set_static_mesh(asset)
    tags = spec.get("tags")
    if tags is not None and spec["kind"] in ("marker", "static", "player_start"):
        actor.set_editor_property("tags", list(tags))


def _apply_light(ue, light):
    actors = _by_label(ue)
    sun = actors.get(LABEL_PREFIX + "Sun")
    if sun:
        sun.set_actor_rotation(_rot(ue, light["sun_pitch"], light["sun_yaw"], 0.0), True)
        comp = sun.get_component_by_class(ue.DirectionalLightComponent)
        comp.set_editor_property("intensity", light["sun_intensity"])
        comp.set_editor_property("light_color", _byte_color(ue, light["sun_color"]))
    fog = actors.get(LABEL_PREFIX + "Fog")
    if fog:
        comp = fog.get_component_by_class(ue.ExponentialHeightFogComponent)
        comp.set_editor_property("fog_density", light["fog_density"])
        comp.set_editor_property("fog_inscattering_luminance", _linear_color(ue, light["fog_color"]))


def _destroy_stale(ue, labels):
    actors = _by_label(ue)
    sub = _subsystem(ue)
    for label in labels:
        actor = actors.get(label)
        if actor:
            sub.destroy_actor(actor)


def place(state, ue=None, rules=None):
    """Spawn or update this phase. Sky and ascended leave the open level alone."""
    plan = plan_level(state, rules)
    if plan["map"] is None:
        return plan
    ue = _ue(ue)
    _ensure_map(ue, plan["map"])
    existing = list(_by_label(ue).keys())
    _destroy_stale(ue, stale_labels(existing, planned_labels(plan)))
    sub = _subsystem(ue)
    actors = _by_label(ue)
    for spec in plan["actors"]:
        actor = actors.get(spec["label"])
        if actor is None:
            cls = getattr(ue, CLASS_NAMES[spec["kind"]])
            actor = sub.spawn_actor_from_class(
                cls,
                _vec(ue, spec["x"], spec["y"], spec["z"]),
                _rot(ue, spec.get("pitch", 0.0), spec.get("yaw", 0.0), 0.0),
            )
        _place(actor, ue, spec)
    _apply_light(ue, plan["light"])
    ue.EditorLevelLibrary.save_current_level()
    return plan


def main(ue=None):
    """Open a welcome walk on the wonder ending. Does not build the Day 1 garden."""
    from incarnation import begin, enter

    if ue is None:
        import unreal

        ue = unreal
    ue.EditorPythonScripting.set_keep_python_script_alive(True)
    state = begin(
        "wonder",
        {
            "faith": 70,
            "fear": 10,
            "prosperity": 40,
            "population": 12,
            "shelter": True,
            "stores": True,
        },
    )
    place(enter(state), ue=ue)


if __name__ == "__main__":
    main()
