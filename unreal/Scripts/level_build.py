"""Spawn /Game/Maps/Day1_Garden in the Unreal editor. Idempotent."""

from garden_logic import (
    AUTHORED_MATERIALS,
    MATERIAL_CANDIDATES,
    MESH_CANDIDATES,
    ROLE_MATERIAL,
    plan_level,
    planned_labels,
    resolve_candidate,
    stale_labels,
    _shape_scale,
)

CLASS_NAMES = {
    "static": "StaticMeshActor",
    "directional_light": "DirectionalLight",
    "sky_light": "SkyLight",
    "sky_atmosphere": "SkyAtmosphere",
    "fog": "ExponentialHeightFog",
    "clouds": "VolumetricCloud",
    "player_start": "PlayerStart",
    "marker": "TargetPoint",
    "post_process": "PostProcessVolume",
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


def _available_assets(ue):
    paths = []
    for group in list(MESH_CANDIDATES.values()) + list(MATERIAL_CANDIDATES.values()):
        paths.extend(group)
    found = set()
    for path in paths:
        if ue.EditorAssetLibrary.does_asset_exist(path):
            found.add(path)
    return found


def _author_material(ue, asset_path, desc):
    package, name = asset_path.rsplit("/", 1)
    tools = ue.AssetToolsHelpers.get_asset_tools()
    material = tools.create_asset(name, package, ue.Material, ue.MaterialFactoryNew())
    library = ue.MaterialEditingLibrary
    color_expr = library.create_material_expression(material, ue.MaterialExpressionConstant3Vector, -350, 0)
    red, green, blue, alpha = desc["color"]
    color_expr.set_editor_property("constant", ue.LinearColor(float(red), float(green), float(blue), float(alpha)))
    library.connect_material_property(color_expr, "", ue.MaterialProperty.MP_BASE_COLOR)
    rough_expr = library.create_material_expression(material, ue.MaterialExpressionConstant, -350, 180)
    rough_expr.set_editor_property("r", float(desc["roughness"]))
    library.connect_material_property(rough_expr, "", ue.MaterialProperty.MP_ROUGHNESS)
    library.recompile_material(material)
    ue.EditorAssetLibrary.save_asset(asset_path, False)
    return material


def _load_material(ue, path, available):
    if path in available or ue.EditorAssetLibrary.does_asset_exist(path):
        return ue.EditorAssetLibrary.load_asset(path)
    desc = AUTHORED_MATERIALS.get(path)
    if desc is None or not hasattr(ue, "MaterialEditingLibrary"):
        return None
    try:
        material = _author_material(ue, path, desc)
    except Exception as exc:
        log_warning = getattr(ue, "log_warning", None)
        if log_warning:
            log_warning(f"Elyon material {path} was not created: {exc}")
        return None
    available.add(path)
    return material


def _resolve_spec(spec, available):
    role = spec.get("role")
    if not role:
        return spec
    resolved = dict(spec)
    mesh = resolve_candidate(MESH_CANDIDATES[role], available)
    resolved["mesh"] = mesh
    resolved["scale"] = _shape_scale(role, spec.get("scatter_scale", 1.0), mesh)
    material_key = ROLE_MATERIAL.get(role)
    if material_key and mesh.startswith("/Engine/BasicShapes/"):
        resolved["material"] = resolve_candidate(MATERIAL_CANDIDATES[material_key], available)
    return resolved


def _place(actor, ue, spec, available):
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
        material_path = spec.get("material")
        if material_path:
            material = _load_material(ue, material_path, available)
            if material is not None and hasattr(comp, "set_material"):
                comp.set_material(0, material)
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
        comp.set_editor_property("fog_height_falloff", light["fog_height_falloff"])
        comp.set_editor_property("start_distance", light["fog_start_distance"])
        comp.set_editor_property("fog_max_opacity", light["fog_max_opacity"])
        comp.set_editor_property("fog_inscattering_luminance", _linear_color(ue, light["fog_color"]))
    marker = actors.get("Elyon.LetThereBeLight")
    if marker:
        marker.set_editor_property("tags", [light["name"]])
    exposure = actors.get("Elyon.Exposure")
    if exposure:
        _apply_exposure(exposure, ue, light)


def _apply_exposure(actor, ue, light):
    """Clamp auto exposure so golden hour stays out of the grey fog wash."""
    actor.set_editor_property("unbound", True)
    actor.set_editor_property("priority", 10.0)
    settings = ue.PostProcessSettings()
    settings.set_editor_property("override_auto_exposure_method", True)
    settings.set_editor_property("auto_exposure_method", ue.AutoExposureMethod.AEM_HISTOGRAM)
    settings.set_editor_property("override_auto_exposure_min_brightness", True)
    settings.set_editor_property("auto_exposure_min_brightness", light["exposure_min_ev"])
    settings.set_editor_property("override_auto_exposure_max_brightness", True)
    settings.set_editor_property("auto_exposure_max_brightness", light["exposure_max_ev"])
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property("auto_exposure_bias", light["exposure_bias"])
    actor.set_editor_property("settings", settings)


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
    available = _available_assets(ue)
    for spec in plan["actors"]:
        spec = _resolve_spec(spec, available)
        actor = actors.get(spec["label"])
        if actor is None:
            cls = getattr(ue, CLASS_NAMES[spec["kind"]])
            actor = sub.spawn_actor_from_class(cls, _vec(ue, spec["x"], spec["y"], spec["z"]), _rot(ue, spec.get("pitch", 0.0), spec.get("yaw", 0.0), 0.0))
        _place(actor, ue, spec, available)
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
