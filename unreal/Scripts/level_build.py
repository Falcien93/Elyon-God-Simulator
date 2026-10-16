"""Spawn /Game/Maps/Day1_Garden in the Unreal editor. Idempotent."""

from garden_logic import plan_level, planned_labels, stale_labels

CLASS_NAMES = {
    "static": "StaticMeshActor",
    "directional_light": "DirectionalLight",
    "sky_light": "SkyLight",
    "sky_atmosphere": "SkyAtmosphere",
    "fog": "ExponentialHeightFog",
    "clouds": "VolumetricCloud",
    "player_start": "PlayerStart",
    "marker": "TargetPoint",
}


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
    pitch = spec.get("pitch", 0.0)
    yaw = spec.get("yaw", 0.0)
    actor.set_actor_rotation(_rot(ue, pitch, yaw, 0.0), True)
    scale = spec.get("scale")
    if scale:
        actor.set_actor_scale3d(_vec(ue, scale[0], scale[1], scale[2]))
    mesh = spec.get("mesh")
    if mesh:
        asset = ue.EditorAssetLibrary.load_asset(mesh)
        comp = actor.get_component_by_class(ue.StaticMeshComponent)
        comp.set_static_mesh(asset)
    if spec["kind"] == "marker":
        actor.set_editor_property("tags", [spec.get("state", "dawn")])


def _apply_light(ue, light):
    actors = _by_label(ue)
    sun = actors.get("Elyon.Sun")
    if sun:
        sun.set_actor_rotation(_rot(ue, light["sun_pitch"], light["sun_yaw"], 0.0), True)
        comp = sun.get_component_by_class(ue.DirectionalLightComponent)
        comp.set_editor_property("intensity", light["sun_intensity"])
        comp.set_editor_property("light_color", _byte_color(ue, light["sun_color"]))
    sky = actors.get("Elyon.SkyLight")
    if sky:
        comp = sky.get_component_by_class(ue.SkyLightComponent)
        comp.set_editor_property("intensity", light["skylight_intensity"])
        comp.set_editor_property("light_color", _byte_color(ue, light["sky_color"]))
        if hasattr(comp, "recapture_sky"):
            comp.recapture_sky()
    fog = actors.get("Elyon.Fog")
    if fog:
        comp = fog.get_component_by_class(ue.ExponentialHeightFogComponent)
        comp.set_editor_property("fog_density", light["fog_density"])
        comp.set_editor_property("fog_inscattering_luminance", _linear_color(ue, light["fog_color"]))
    marker = actors.get("Elyon.LetThereBeLight")
    if marker:
        marker.set_editor_property("tags", [light["name"]])


def _destroy_stale(ue, labels):
    actors = _by_label(ue)
    sub = _subsystem(ue)
    for label in labels:
        actor = actors.get(label)
        if actor:
            sub.destroy_actor(actor)


def build(dawn=True, ue=None):
    ue = _ue(ue)
    plan = plan_level(dawn)
    _ensure_map(ue, plan["map"])
    existing = list(_by_label(ue).keys())
    _destroy_stale(ue, stale_labels(existing, planned_labels(plan)))
    sub = _subsystem(ue)
    actors = _by_label(ue)
    for spec in plan["actors"]:
        actor = actors.get(spec["label"])
        if actor is None:
            cls = getattr(ue, CLASS_NAMES[spec["kind"]])
            actor = sub.spawn_actor_from_class(cls, _vec(ue, spec["x"], spec["y"], spec["z"]), _rot(ue, spec.get("pitch", 0.0), spec.get("yaw", 0.0), 0.0))
        _place(actor, ue, spec)
    _apply_light(ue, plan["light"])
    ue.EditorLevelLibrary.save_current_level()
    return plan


def let_there_be_light(dawn, ue=None):
    """Darkness when dawn is false. Dawn when dawn is true."""
    ue = _ue(ue)
    plan = plan_level(dawn)
    _apply_light(ue, plan["light"])
    ue.EditorLevelLibrary.save_current_level()
    return plan["light"]
