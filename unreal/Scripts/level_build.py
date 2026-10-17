"""Spawn /Game/Maps/Day1_Garden in the Unreal editor. Idempotent."""

from garden_logic import (
    AUTHORED_MATERIALS,
    MATERIAL_CANDIDATES,
    MESH_CANDIDATES,
    OVERVIEW,
    ROLE_MATERIAL,
    SEQUENCE_PATH,
    NANITE_ROLES,
    WATER_ROLES,
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
    "cine_camera": "CineCameraActor",
    "level_sequence": "LevelSequenceActor",
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


def _warn(ue, message):
    log_warning = getattr(ue, "log_warning", None)
    if log_warning:
        log_warning(message)


def _try_set(target, name, value, ue):
    """Optional cinematic properties. A missing name must not abort the level save."""
    try:
        target.set_editor_property(name, value)
    except Exception as exc:
        _warn(ue, f"Elyon skipped {name}: {exc}")


def _enum(ue, type_name, name):
    enum = getattr(ue, type_name, None)
    if enum is None:
        return None
    return getattr(enum, name, None)


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
    if desc.get("blend") == "translucent" and hasattr(ue, "BlendMode"):
        _try_set(material, "blend_mode", ue.BlendMode.BLEND_TRANSLUCENT, ue)
    library.recompile_material(material)
    ue.EditorAssetLibrary.save_asset(asset_path, False)
    return material


def _enable_nanite(ue, mesh_path):
    """Enable Nanite on project meshes for the forest, rocks, and terrain."""
    if not mesh_path or mesh_path.startswith("/Engine/") or not hasattr(ue, "MeshNaniteSettings"):
        return False
    try:
        asset = ue.EditorAssetLibrary.load_asset(mesh_path)
    except Exception as exc:
        _warn(ue, f"Elyon could not load {mesh_path} for Nanite: {exc}")
        return False
    if asset is None or not hasattr(asset, "set_editor_property"):
        return False
    settings = ue.MeshNaniteSettings()
    settings.set_editor_property("enabled", True)
    try:
        asset.set_editor_property("nanite_settings", settings)
    except Exception as exc:
        _warn(ue, f"Elyon could not enable Nanite on {mesh_path}: {exc}")
        return False
    save = getattr(ue.EditorAssetLibrary, "save_asset", None)
    if save:
        try:
            save(mesh_path, False)
        except Exception as exc:
            _warn(ue, f"Elyon could not save Nanite on {mesh_path}: {exc}")
    return True


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
    role = spec.get("role")
    if mesh:
        asset = ue.EditorAssetLibrary.load_asset(mesh)
        comp = actor.get_component_by_class(ue.StaticMeshComponent)
        comp.set_static_mesh(asset)
        if role in NANITE_ROLES:
            _try_set(comp, "disallow_nanite", False, ue)
            _enable_nanite(ue, mesh)
        if role in WATER_ROLES:
            _try_set(comp, "visible_in_ray_tracing", True, ue)
        material_path = spec.get("material")
        if material_path:
            material = _load_material(ue, material_path, available)
            if material is not None and hasattr(comp, "set_material"):
                comp.set_material(0, material)
    if spec["kind"] == "marker":
        actor.set_editor_property("tags", [spec.get("state", "dawn")])
    if spec["kind"] == "cine_camera":
        comp = actor.get_component_by_class(ue.CineCameraComponent)
        comp.set_editor_property("current_focal_length", 24.0)
        comp.set_editor_property("current_aperture", 8.0)
        # f/8 must not drive exposure. Physical camera exposure would crush a
        # piloted view. The unbound volume owns histogram auto exposure.
        lens = ue.PostProcessSettings()
        _try_set(lens, "override_auto_exposure_apply_physical_camera_exposure", True, ue)
        _try_set(lens, "auto_exposure_apply_physical_camera_exposure", False, ue)
        _try_set(comp, "post_process_settings", lens, ue)


def _apply_light(ue, light):
    actors = _by_label(ue)
    sun = actors.get("Elyon.Sun")
    if sun:
        sun.set_actor_rotation(_rot(ue, light["sun_pitch"], light["sun_yaw"], 0.0), True)
        comp = sun.get_component_by_class(ue.DirectionalLightComponent)
        comp.set_editor_property("intensity", light["sun_intensity"])
        comp.set_editor_property("light_color", _byte_color(ue, light["sun_color"]))
        comp.set_editor_property("atmosphere_sun_light", light["atmosphere_sun_light"])
        comp.set_editor_property("light_source_angle", light["light_source_angle"])
        comp.set_editor_property("cast_volumetric_shadow", light["cast_volumetric_shadow"])
        comp.set_editor_property("volumetric_scattering_intensity", light["volumetric_scattering_intensity"])
        comp.set_editor_property("enable_light_shaft_bloom", light["enable_light_shaft_bloom"])
        comp.set_editor_property("enable_light_shaft_occlusion", light["enable_light_shaft_occlusion"])
        comp.set_editor_property("bloom_scale", light["bloom_scale"])
        comp.set_editor_property("bloom_threshold", light["bloom_threshold"])
        comp.set_editor_property("bloom_max_brightness", light["bloom_max_brightness"])
        comp.set_editor_property("bloom_tint", _byte_color(ue, light["bloom_tint"]))
    sky = actors.get("Elyon.SkyLight")
    if sky:
        comp = sky.get_component_by_class(ue.SkyLightComponent)
        comp.set_editor_property("intensity", light["skylight_intensity"])
        comp.set_editor_property("light_color", _byte_color(ue, light["sky_color"]))
        source = _enum(ue, "SkyLightSourceType", "SLS_CAPTURED_SCENE")
        if source is not None:
            _try_set(comp, "source_type", source, ue)
        mobility = _enum(ue, "ComponentMobility", "MOVABLE")
        if mobility is not None:
            _try_set(comp, "mobility", mobility, ue)
        _try_set(comp, "real_time_capture", True, ue)
        _try_set(comp, "lower_hemisphere_is_black", False, ue)
        _try_set(comp, "volumetric_scattering_intensity", 1.2, ue)
        if hasattr(comp, "recapture_sky"):
            comp.recapture_sky()
    atmosphere = actors.get("Elyon.SkyAtmosphere")
    if atmosphere and hasattr(ue, "SkyAtmosphereComponent"):
        comp = atmosphere.get_component_by_class(ue.SkyAtmosphereComponent)
        _try_set(comp, "mie_anisotropy", light["mie_anisotropy"], ue)
        _try_set(comp, "mie_scattering_scale", light["mie_scattering_scale"], ue)
        _try_set(comp, "sky_luminance_factor", _linear_color(ue, light["sky_luminance_factor"]), ue)
        # UE 5.8 still spells this AerialPespective (no "r"). The corrected name is not a property.
        _try_set(comp, "aerial_pespective_view_distance_scale", light["aerial_pespective_view_distance_scale"], ue)
        _try_set(comp, "height_fog_contribution", 1.0, ue)
    fog = actors.get("Elyon.Fog")
    if fog:
        comp = fog.get_component_by_class(ue.ExponentialHeightFogComponent)
        comp.set_editor_property("fog_density", light["fog_density"])
        comp.set_editor_property("fog_height_falloff", light["fog_height_falloff"])
        comp.set_editor_property("start_distance", light["fog_start_distance"])
        comp.set_editor_property("fog_max_opacity", light["fog_max_opacity"])
        comp.set_editor_property("fog_inscattering_luminance", _linear_color(ue, light["fog_color"]))
        comp.set_editor_property("enable_volumetric_fog", light["enable_volumetric_fog"])
        comp.set_editor_property("volumetric_fog_albedo", _byte_color(ue, light["volumetric_fog_albedo"]))
        comp.set_editor_property("volumetric_fog_emissive", _linear_color(ue, light["volumetric_fog_emissive"]))
        comp.set_editor_property("volumetric_fog_scattering_distribution", light["volumetric_fog_scattering_distribution"])
        comp.set_editor_property("volumetric_fog_extinction_scale", light["volumetric_fog_extinction_scale"])
        comp.set_editor_property("volumetric_fog_distance", light["volumetric_fog_distance"])
        comp.set_editor_property("volumetric_fog_start_distance", light["volumetric_fog_start_distance"])
        comp.set_editor_property("directional_inscattering_exponent", light["directional_inscattering_exponent"])
        comp.set_editor_property("directional_inscattering_start_distance", light["directional_inscattering_start_distance"])
        comp.set_editor_property("directional_inscattering_luminance", _linear_color(ue, light["directional_inscattering"]))
    clouds = actors.get("Elyon.Clouds")
    if clouds and hasattr(ue, "VolumetricCloudComponent"):
        comp = clouds.get_component_by_class(ue.VolumetricCloudComponent)
        _try_set(comp, "layer_bottom_altitude", light["cloud_bottom_km"], ue)
        _try_set(comp, "layer_height", light["cloud_height_km"], ue)
    marker = actors.get("Elyon.LetThereBeLight")
    if marker:
        marker.set_editor_property("tags", [light["name"]])
    exposure = actors.get("Elyon.Exposure")
    if exposure:
        _apply_exposure(exposure, ue, light)


def _apply_exposure(actor, ue, light):
    """Histogram auto exposure in EV100. Keep bloom, fringe, vignette, and flares quiet."""
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
    _try_set(settings, "override_auto_exposure_histogram_log_min", True, ue)
    _try_set(settings, "auto_exposure_histogram_log_min", light["exposure_histogram_min_ev"], ue)
    _try_set(settings, "override_auto_exposure_histogram_log_max", True, ue)
    _try_set(settings, "auto_exposure_histogram_log_max", light["exposure_histogram_max_ev"], ue)
    _try_set(settings, "override_auto_exposure_apply_physical_camera_exposure", True, ue)
    _try_set(settings, "auto_exposure_apply_physical_camera_exposure", False, ue)
    _try_set(settings, "override_auto_exposure_speed_up", True, ue)
    _try_set(settings, "auto_exposure_speed_up", 8.0, ue)
    _try_set(settings, "override_auto_exposure_speed_down", True, ue)
    _try_set(settings, "auto_exposure_speed_down", 8.0, ue)
    settings.set_editor_property("override_bloom_intensity", True)
    settings.set_editor_property("bloom_intensity", light["bloom_intensity"])
    settings.set_editor_property("override_vignette_intensity", True)
    settings.set_editor_property("vignette_intensity", light["vignette_intensity"])
    settings.set_editor_property("override_scene_fringe_intensity", True)
    settings.set_editor_property("scene_fringe_intensity", light["scene_fringe_intensity"])
    settings.set_editor_property("override_lens_flare_intensity", True)
    settings.set_editor_property("lens_flare_intensity", light["lens_flare_intensity"])
    settings.set_editor_property("override_white_temp", True)
    settings.set_editor_property("white_temp", light["white_temp"])
    _try_set(settings, "override_screen_space_reflection_intensity", True, ue)
    _try_set(settings, "screen_space_reflection_intensity", 70.0, ue)
    _try_set(settings, "override_screen_space_reflection_quality", True, ue)
    _try_set(settings, "screen_space_reflection_quality", 50.0, ue)
    actor.set_editor_property("settings", settings)


def _destroy_stale(ue, labels):
    actors = _by_label(ue)
    sub = _subsystem(ue)
    for label in labels:
        actor = actors.get(label)
        if actor:
            sub.destroy_actor(actor)


def _frame_editor(ue, key):
    library = getattr(ue, "EditorLevelLibrary", None)
    if library is None or not hasattr(library, "set_level_viewport_camera_info"):
        return
    try:
        library.set_level_viewport_camera_info(
            _vec(ue, key["x"], key["y"], key["z"]),
            _rot(ue, key["pitch"], key["yaw"], 0.0),
        )
    except Exception as exc:
        _warn(ue, f"Elyon could not move the editor camera: {exc}")


def frame_overview(ue=None):
    """Put the perspective viewport above the garden, looking north and down."""
    ue = _ue(ue)
    _frame_editor(ue, OVERVIEW)
    return OVERVIEW


def _channel(ue, section, name):
    """UE 5.8 names this get_channel. Older builds used get_channel_by_name."""
    extensions = ue.MovieSceneSectionExtensions
    getter = getattr(extensions, "get_channel", None)
    if getter is None:
        getter = extensions.get_channel_by_name
    return getter(section, name)


def _build_flythrough(ue, camera, keys):
    """Key the god camera on a level sequence. Failure leaves the still camera in place."""
    if camera is None or not keys or not hasattr(ue, "LevelSequence") or not hasattr(ue, "AssetToolsHelpers"):
        return None
    try:
        assets = ue.EditorAssetLibrary
        if assets.does_asset_exist(SEQUENCE_PATH):
            assets.delete_asset(SEQUENCE_PATH)
        tools = ue.AssetToolsHelpers.get_asset_tools()
        sequence = tools.create_asset(
            "LS_GodFlythrough",
            "/Game/Cinematics",
            ue.LevelSequence,
            ue.LevelSequenceFactoryNew(),
        )
        fps = 24
        end_frame = int(round(keys[-1]["t"] * fps))
        if hasattr(sequence, "set_display_rate") and hasattr(ue, "FrameRate"):
            sequence.set_display_rate(ue.FrameRate(fps, 1))
        if hasattr(sequence, "set_playback_start"):
            sequence.set_playback_start(0)
        if hasattr(sequence, "set_playback_end"):
            sequence.set_playback_end(end_frame)
        binding = ue.MovieSceneSequenceExtensions.add_possessable(sequence, camera)
        track = binding.add_track(ue.MovieScene3DTransformTrack)
        section = track.add_section()
        # UE 5.8 SetRange takes display-rate int32 frames. FrameNumber fails to nativize.
        section.set_range(0, end_frame)
        channels = {
            "x": _channel(ue, section, "Location.X"),
            "y": _channel(ue, section, "Location.Y"),
            "z": _channel(ue, section, "Location.Z"),
            "pitch": _channel(ue, section, "Rotation.Y"),
            "yaw": _channel(ue, section, "Rotation.Z"),
        }
        for key in keys:
            frame = ue.FrameNumber(int(round(key["t"] * fps)))
            channels["x"].add_key(frame, key["x"])
            channels["y"].add_key(frame, key["y"])
            channels["z"].add_key(frame, key["z"])
            channels["pitch"].add_key(frame, key["pitch"])
            channels["yaw"].add_key(frame, key["yaw"])
        origin = ue.FrameNumber(0)
        for axis in ("Scale.X", "Scale.Y", "Scale.Z"):
            _channel(ue, section, axis).add_key(origin, 1.0)
        # UE 5.8 removed master tracks. The camera cut is a normal sequence track.
        # The level camera is possessed so the cut uses the actor already in the garden.
        cut_track = sequence.add_track(ue.MovieSceneCameraCutTrack)
        cut = cut_track.add_section()
        if not hasattr(cut, "set_camera_binding_id") and hasattr(cut, "cast"):
            cut = cut.cast(ue.MovieSceneCameraCutSection)
        cut.set_range(0, end_frame)
        binding_id = ue.MovieSceneSequenceExtensions.get_binding_id(sequence, binding)
        cut.set_camera_binding_id(binding_id)
        assets.save_asset(SEQUENCE_PATH, False)
        actor = _by_label(ue).get("Elyon.GodFlythrough")
        if actor is not None and hasattr(actor, "set_sequence"):
            actor.set_sequence(sequence)
        if actor is not None and hasattr(ue, "MovieSceneSequencePlaybackSettings"):
            playback = ue.MovieSceneSequencePlaybackSettings()
            playback.set_editor_property("auto_play", True)
            actor.set_editor_property("playback_settings", playback)
        return sequence
    except Exception as exc:
        _warn(ue, f"Elyon god flythrough sequence was not created: {exc}")
        return None


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
    _build_flythrough(ue, _by_label(ue).get("Elyon.GodCamera"), plan["flight"])
    frame_overview(ue)
    ue.EditorLevelLibrary.save_current_level()
    return plan


def let_there_be_light(dawn, ue=None):
    """Darkness when dawn is false. Dawn when dawn is true."""
    ue = _ue(ue)
    plan = plan_level(dawn)
    _apply_light(ue, plan["light"])
    ue.EditorLevelLibrary.save_current_level()
    return plan["light"]
