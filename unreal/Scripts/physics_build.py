"""Arm Chaos bodies, the Water plugin river, wind, and the God hand after the garden exists."""

import math

import garden_logic
import physics_logic as logic

_TICK_REGISTERED = False
_BASE_YAW = {}
_SESSION = None
_SEATED = False

WATER_MATERIAL = "/Game/StarterContent/Materials/M_Water_Lake"


def apply(ue):
    """Idempotent physics pass. Call it after level_build.build, which deletes unknown Elyon labels."""
    _spawn_dynamic(ue)
    _arm_all(ue)
    _apply_water(ue)
    _apply_wind(ue)
    _try_simple_grass_wind(ue)
    _ensure_god_camera(ue)
    _register_tick(ue)
    _bend(ue, [])
    _save(ue)


def apply_contact_bend(ue, contacts):
    _bend(ue, contacts)


def _warn(ue, message):
    sink = getattr(ue, "warnings", None)
    if isinstance(sink, list):
        sink.append(str(message))
    fn = getattr(ue, "log_warning", None)
    if callable(fn):
        try:
            fn(str(message))
        except Exception:
            return


def _save(ue):
    library = getattr(ue, "EditorLevelLibrary", None)
    save = getattr(library, "save_current_level", None)
    if callable(save):
        save()


def _class(ue, *names):
    for name in names:
        cls = getattr(ue, name, None)
        if cls is not None:
            return cls
    return None


def _actors(ue, world=None):
    if world is not None:
        statics = getattr(ue, "GameplayStatics", None)
        get_all = getattr(statics, "get_all_actors_of_class", None)
        actor_cls = getattr(ue, "Actor", None)
        if callable(get_all) and actor_cls is not None:
            try:
                found = get_all(world, actor_cls)
                if found:
                    return list(found)
            except Exception as exc:
                _warn(ue, f"Game world actors were not listed: {exc}")
    try:
        return list(ue.get_editor_subsystem(ue.EditorActorSubsystem).get_all_level_actors())
    except Exception:
        return []


def _by_label(ue, world=None):
    found = {}
    for actor in _actors(ue, world):
        found[actor.get_actor_label()] = actor
    return found


def _call(obj, name, *args, **kwargs):
    fn = getattr(obj, name, None)
    if not callable(fn):
        return False
    fn(*args, **kwargs)
    return True


def _set_prop(obj, name, value):
    setter = getattr(obj, "set_editor_property", None)
    if not callable(setter):
        return False
    try:
        setter(name, value)
        return True
    except Exception:
        return False


def _read_location(actor):
    if actor is None:
        return (0.0, 0.0, 0.0)
    getter = getattr(actor, "get_actor_location", None)
    loc = getter() if callable(getter) else getattr(actor, "location", None)
    if loc is None:
        return (0.0, 0.0, 0.0)
    return (float(loc.x), float(loc.y), float(loc.z))


def _read_rotation(actor):
    getter = getattr(actor, "get_actor_rotation", None)
    rot = getter() if callable(getter) else getattr(actor, "rotation", None)
    if rot is None:
        return (0.0, 0.0, 0.0)
    return (float(rot.pitch), float(rot.yaw), float(getattr(rot, "roll", 0.0)))


def _base_yaw(actor):
    label = actor.get_actor_label()
    if label not in _BASE_YAW:
        _BASE_YAW[label] = _read_rotation(actor)[1]
    return _BASE_YAW[label]


def _find_or_spawn(ue, label, cls, location, rotation):
    actor = _by_label(ue).get(label)
    if actor is not None:
        return actor
    if cls is None:
        return None
    actor = ue.get_editor_subsystem(ue.EditorActorSubsystem).spawn_actor_from_class(cls, location, rotation)
    actor.set_actor_label(label)
    return actor


def _spawn_body(ue, spec):
    actor = _find_or_spawn(
        ue,
        spec["label"],
        _class(ue, "StaticMeshActor"),
        ue.Vector(spec["x"], spec["y"], spec["z"]),
        ue.Rotator(spec.get("pitch", 0.0), spec.get("yaw", 0.0), 0.0),
    )
    if actor is None:
        return None
    actor.set_actor_label(spec["label"])
    actor.set_actor_location(ue.Vector(spec["x"], spec["y"], spec["z"]), False, True)
    actor.set_actor_rotation(ue.Rotator(spec.get("pitch", 0.0), spec.get("yaw", 0.0), 0.0), True)
    scale = spec["scale"]
    actor.set_actor_scale3d(ue.Vector(scale[0], scale[1], scale[2]))
    mesh = garden_logic.MESH[spec["mesh"]]
    asset = ue.EditorAssetLibrary.load_asset(mesh)
    comp = actor.get_component_by_class(ue.StaticMeshComponent)
    comp.set_static_mesh(asset)
    return actor


def _spawn_dynamic(ue):
    for spec in logic.log_placements() + logic.fruit_placements():
        _spawn_body(ue, spec)


def _mesh(ue, actor):
    cls = getattr(ue, "StaticMeshComponent", None)
    getter = getattr(actor, "get_component_by_class", None) if actor is not None else None
    if cls is None or not callable(getter):
        return None
    try:
        return getter(cls)
    except Exception:
        return None


def _add_component(ue, actor, cls):
    add = getattr(actor, "add_component_by_class", None)
    if callable(add):
        try:
            return add(cls)
        except Exception as exc:
            _warn(ue, f"Could not add a component: {exc}")
    factory = getattr(ue, "new_object", None)
    if not callable(factory):
        return None
    try:
        try:
            comp = factory(cls, outer=actor)
        except TypeError:
            comp = factory(cls)
    except Exception as exc:
        _warn(ue, f"Could not create a component: {exc}")
        return None
    adder = getattr(actor, "add_instance_component", None)
    if callable(adder):
        adder(comp)
    register = getattr(comp, "register_component", None)
    if callable(register):
        register()
    return comp


def _configure_pontoon(ue, comp, radius):
    cls = _class(ue, "SphericalPontoon")
    if cls is None or comp is None:
        return
    try:
        pontoon = cls()
        if hasattr(pontoon, "set_editor_property"):
            pontoon.set_editor_property("relative_location", ue.Vector(0.0, 0.0, 0.0))
            pontoon.set_editor_property("radius", float(radius))
        comp.set_editor_property("pontoons", [pontoon])
    except Exception as exc:
        _warn(ue, f"Buoyancy pontoon was not configured: {exc}")


def _existing_component(actor, cls):
    for item_cls, comp in getattr(actor, "added_components", ()) or ():
        if item_cls is cls:
            return comp
    comps = getattr(actor, "comps", None)
    if isinstance(comps, dict):
        return comps.get(cls)
    getter = getattr(actor, "get_component_by_class", None)
    if not callable(getter):
        return None
    try:
        return getter(cls)
    except Exception:
        return None


def _add_buoyancy(ue, actor, spec):
    if not spec["floats"]:
        return None
    cls = _class(ue, "BuoyancyComponent")
    if cls is None:
        return None
    existing = _existing_component(actor, cls)
    if existing is not None:
        _configure_pontoon(ue, existing, spec["pontoon_radius"])
        return existing
    comp = _add_component(ue, actor, cls)
    if comp is not None:
        _configure_pontoon(ue, comp, spec["pontoon_radius"])
    return comp


def _arm(ue, actor, kind):
    spec = logic.body_spec(kind)
    comp = _mesh(ue, actor)
    if comp is None:
        return None
    mobility = getattr(getattr(ue, "ComponentMobility", None), "MOVABLE", None)
    if mobility is not None:
        _call(comp, "set_mobility", mobility)
    _call(comp, "set_collision_profile_name", spec["collision"])
    _call(comp, "set_notify_rigid_body_collision", True)
    _call(comp, "set_enable_gravity", True)
    _call(comp, "set_linear_damping", spec["linear_damping"])
    _call(comp, "set_angular_damping", spec["angular_damping"])
    _call(
        comp,
        "set_mass_override_in_kg",
        bone_name="None",
        mass_in_kg=spec["mass"],
        override_mass=True,
    )
    _call(comp, "set_use_ccd", True)
    _call(comp, "set_simulate_physics", True)
    _add_buoyancy(ue, actor, spec)
    return comp


def _arm_actor(ue, actor):
    kind = logic.classify_label(actor.get_actor_label())
    if kind not in logic.DYNAMIC_KINDS:
        return
    try:
        _arm(ue, actor, kind)
    except Exception as exc:
        _warn(ue, f"Physics was not armed on {actor.get_actor_label()}: {exc}")


def _arm_ground(ue):
    ground = _by_label(ue).get("Elyon.Ground")
    comp = _mesh(ue, ground)
    if comp is not None:
        _call(comp, "set_collision_profile_name", "BlockAll")


def _arm_all(ue):
    _arm_ground(ue)
    for actor in list(_actors(ue)):
        _arm_actor(ue, actor)


def _try_water_material(ue, body):
    try:
        assets = getattr(ue, "EditorAssetLibrary", None)
        if assets is None or not assets.does_asset_exist(WATER_MATERIAL):
            return
        _set_prop(body, "water_material", assets.load_asset(WATER_MATERIAL))
    except Exception as exc:
        _warn(ue, f"Water material was left as the engine default: {exc}")


def _apply_water(ue):
    river_cls = _class(ue, "WaterBodyRiver", "WaterBodyRiverActor")
    if river_cls is None:
        _warn(ue, "Water plugin class WaterBodyRiver is missing. The cube river stays visible.")
        return False
    try:
        points = logic.river_spline_points()
        first = points[0]
        actor = _find_or_spawn(
            ue,
            "Elyon.WaterRiver",
            river_cls,
            ue.Vector(first["x"], first["y"], first["z"]),
            ue.Rotator(0.0, 0.0, 0.0),
        )
        if actor is None:
            raise RuntimeError("WaterBodyRiver did not spawn")
        spline_cls = _class(ue, "WaterSplineComponent")
        body_cls = _class(ue, "WaterBodyRiverComponent")
        spline = actor.get_component_by_class(spline_cls) if spline_cls is not None else None
        body = actor.get_component_by_class(body_cls) if body_cls is not None else None
        if spline is None or body is None:
            raise RuntimeError("Water river is missing its spline or river component")
        clear = getattr(spline, "clear_spline_points", None)
        if callable(clear):
            clear()
        space = getattr(getattr(ue, "SplineCoordinateSpace", None), "WORLD", None)
        for point in points:
            spline.add_spline_point(ue.Vector(point["x"], point["y"], point["z"]), space)
            body.set_river_width_at_spline_input_key(point["key"], point["width"])
            body.set_river_depth_at_spline_input_key(point["key"], point["depth"])
        _try_water_material(ue, body)
        cube = _by_label(ue).get("Elyon.River")
        hide = getattr(cube, "set_actor_hidden_in_game", None) if cube is not None else None
        if callable(hide):
            hide(True)
        return True
    except Exception as exc:
        _warn(ue, f"Water river was not created. The cube river stays visible. {exc}")
        return False


def _apply_wind(ue):
    cls = _class(ue, "WindDirectionalSource")
    if cls is None:
        _warn(ue, "WindDirectionalSource is missing. Plants still bend from contact.")
        return False
    try:
        state = logic.wind_state()
        actor = _find_or_spawn(
            ue,
            state["label"],
            cls,
            ue.Vector(state["x"], state["y"], state["z"]),
            ue.Rotator(0.0, state["yaw"], 0.0),
        )
        if actor is None:
            return False
        actor.set_actor_location(ue.Vector(state["x"], state["y"], state["z"]), False, True)
        actor.set_actor_rotation(ue.Rotator(0.0, state["yaw"], 0.0), True)
        comp_cls = _class(ue, "WindDirectionalSourceComponent")
        comp = actor.get_component_by_class(comp_cls) if comp_cls is not None else None
        if comp is None:
            return False
        _set_prop(comp, "strength", state["strength"])
        _set_prop(comp, "speed", state["speed"])
        _set_prop(comp, "min_gust_amount", state["min_gust"])
        _set_prop(comp, "max_gust_amount", state["max_gust"])
        _set_prop(comp, "radius", state["radius"])
        _set_prop(comp, "point_wind", False)
        return True
    except Exception as exc:
        _warn(ue, f"Wind source was not created: {exc}")
        return False


def _try_simple_grass_wind(ue):
    editing = getattr(ue, "MaterialEditingLibrary", None)
    assets = getattr(ue, "EditorAssetLibrary", None)
    if editing is None or assets is None or not hasattr(assets, "does_asset_exist"):
        return False
    try:
        found = None
        for path in logic.GRASS_WIND_PATHS:
            if assets.does_asset_exist(path):
                found = path
                break
        if found is None:
            _warn(ue, "SimpleGrassWind was not found. Plants bend when God or a held object comes near them.")
            return False
        creator = getattr(editing, "create_material", None)
        if not callable(creator):
            _warn(ue, "SimpleGrassWind exists, but this editor cannot create the wind material. Plants still bend from contact.")
            return False
        material = creator("M_Elyon_WindLeaf", "/Game/Materials")
        function = assets.load_asset(found)
        expr_cls = getattr(ue, "MaterialExpressionMaterialFunctionCall", None)
        make_expr = getattr(editing, "create_material_expression", None)
        if expr_cls is not None and callable(make_expr):
            expression = make_expr(material, expr_cls)
            if hasattr(expression, "set_editor_property"):
                expression.set_editor_property("material_function", function)
            connect = getattr(editing, "connect_material_property", None)
            prop = getattr(getattr(ue, "MaterialProperty", None), "MP_WORLD_POSITION_OFFSET", None)
            if callable(connect) and prop is not None:
                connect(expression, "", prop)
        save = getattr(assets, "save_asset", None)
        if callable(save):
            save("/Game/Materials/M_Elyon_WindLeaf")
        return True
    except Exception as exc:
        _warn(ue, f"Wind sway material was skipped: {exc}")
        return False


def _ensure_handle(ue, actor):
    if actor is None:
        return None
    cls = _class(ue, "PhysicsHandleComponent")
    if cls is None:
        return None
    comp = None
    getter = getattr(actor, "get_component_by_class", None)
    if callable(getter):
        try:
            comp = getter(cls)
        except Exception:
            comp = None
    if comp is None:
        comp = _add_component(ue, actor, cls)
    if comp is None:
        return None
    for name, value in logic.HANDLE.items():
        _set_prop(comp, name, value)
    return comp


def _ensure_god_camera(ue):
    try:
        existing = _by_label(ue).get("Elyon.GodCamera")
        if existing is not None:
            _ensure_handle(ue, existing)
            return existing
        cls = _class(ue, "CineCameraActor", "CameraActor")
        if cls is None:
            _warn(ue, "No cine camera class. God grabbing still attaches to the player pawn on Play.")
            return None
        spec = logic.god_camera_spec()
        actor = _find_or_spawn(
            ue,
            spec["label"],
            cls,
            ue.Vector(spec["x"], spec["y"], spec["z"]),
            ue.Rotator(spec["pitch"], spec["yaw"], 0.0),
        )
        if actor is None:
            return None
        actor.set_actor_location(ue.Vector(spec["x"], spec["y"], spec["z"]), False, True)
        actor.set_actor_rotation(ue.Rotator(spec["pitch"], spec["yaw"], 0.0), True)
        cine_cls = _class(ue, "CineCameraComponent")
        if cine_cls is not None:
            comp = actor.get_component_by_class(cine_cls)
            _set_prop(comp, "focal_length", 24.0)
            _set_prop(comp, "current_aperture", 2.8)
        _ensure_handle(ue, actor)
        return actor
    except Exception as exc:
        _warn(ue, f"God camera was not created: {exc}")
        return None


def _bend(ue, contacts):
    plants = []
    actors = {}
    for actor in _actors(ue):
        label = actor.get_actor_label()
        if logic.classify_label(label) != "plant":
            continue
        actors[label] = actor
        plants.append(
            {
                "label": label,
                "location": _read_location(actor),
                "base_yaw": _base_yaw(actor),
            }
        )
    for bend in logic.bend_plants(plants, contacts):
        actor = actors[bend["label"]]
        actor.set_actor_rotation(ue.Rotator(bend["pitch"], bend["yaw"], 0.0), True)
        comp = _mesh(ue, actor)
        if comp is not None:
            _call(comp, "set_custom_primitive_data_float", 0, bend["weight"])


def _session():
    global _SESSION
    if _SESSION is None:
        _SESSION = logic.new_session()
    return _SESSION


def _register_tick(ue):
    global _TICK_REGISTERED
    if _TICK_REGISTERED:
        return
    register = getattr(ue, "register_slate_post_tick_callback", None)
    if not callable(register):
        scripting = getattr(ue, "EditorPythonScripting", None)
        register = getattr(scripting, "register_slate_post_tick_callback", None)
    if not callable(register):
        return

    def _on_tick(*args):
        delta = args[0] if args else 0.0
        try:
            _tick(ue, delta)
        except Exception as exc:
            _warn(ue, f"Physics tick failed: {exc}")

    try:
        register(_on_tick)
    except Exception as exc:
        _warn(ue, f"Physics tick was not registered: {exc}")
        return
    _TICK_REGISTERED = True


def _game_world(ue):
    try:
        cls = getattr(ue, "UnrealEditorSubsystem", None)
        if cls is not None:
            world = ue.get_editor_subsystem(cls).get_game_world()
            if world:
                return world
    except Exception as exc:
        _warn(ue, f"Game world lookup failed: {exc}")
    library = getattr(ue, "EditorLevelLibrary", None)
    getter = getattr(library, "get_game_world", None)
    if callable(getter):
        try:
            return getter()
        except Exception as exc:
            _warn(ue, f"Game world lookup failed: {exc}")
    return None


def _player_controller(ue, world):
    statics = getattr(ue, "GameplayStatics", None)
    getter = getattr(statics, "get_player_controller", None)
    if not callable(getter):
        return None
    try:
        return getter(world, 0)
    except Exception as exc:
        _warn(ue, f"Player controller was not found: {exc}")
        return None


def _try_flying(ue, pawn):
    mode = getattr(getattr(ue, "MovementMode", None), "MOVE_Flying", None)
    getter = getattr(pawn, "get_movement_component", None)
    if mode is None or not callable(getter):
        return
    try:
        move = getter()
        setter = getattr(move, "set_movement_mode", None)
        if callable(setter):
            setter(mode)
    except Exception as exc:
        _warn(ue, f"God pawn was left on its default movement: {exc}")


def _seat_god_pawn(ue, world):
    global _SEATED
    if _SEATED:
        return
    camera = _by_label(ue).get("Elyon.GodCamera")
    controller = _player_controller(ue, world)
    if camera is None or controller is None or not hasattr(controller, "get_pawn"):
        return
    pawn = controller.get_pawn()
    if pawn is None:
        return
    try:
        loc = _read_location(camera)
        pitch, yaw, roll = _read_rotation(camera)
        pawn.set_actor_location(ue.Vector(*loc), False, True)
        rot = ue.Rotator(pitch, yaw, roll)
        if hasattr(pawn, "set_actor_rotation"):
            pawn.set_actor_rotation(rot, True)
        if hasattr(controller, "set_control_rotation"):
            controller.set_control_rotation(rot)
        _try_flying(ue, pawn)
        _ensure_handle(ue, pawn)
        _SEATED = True
    except Exception as exc:
        _warn(ue, f"God pawn was not seated: {exc}")


def _poll_keys(ue, controller):
    is_down = getattr(controller, "is_input_key_down", None)
    if not callable(is_down):
        return set()
    held = set()
    for action, key_name in logic.KEYS.items():
        try:
            key = ue.Key(key_name) if hasattr(ue, "Key") else key_name
            if is_down(key):
                held.add(action)
        except Exception:
            continue
    return held


def _forward_of(ue, rot):
    if rot is None:
        return (1.0, 0.0, 0.0)
    lib = getattr(ue, "MathLibrary", None)
    getter = getattr(lib, "get_forward_vector", None) if lib is not None else None
    if callable(getter):
        try:
            vec = getter(rot)
            return (float(vec.x), float(vec.y), float(vec.z))
        except Exception:
            pass
    pitch = math.radians(float(rot.pitch))
    yaw = math.radians(float(rot.yaw))
    cp = math.cos(pitch)
    return (cp * math.cos(yaw), cp * math.sin(yaw), math.sin(pitch))


def _view_vectors(ue, controller):
    pawn = controller.get_pawn() if hasattr(controller, "get_pawn") else None
    origin = _read_location(pawn if pawn is not None else controller)
    rot = None
    getter = getattr(controller, "get_control_rotation", None)
    if callable(getter):
        rot = getter()
    if rot is None and pawn is not None:
        pitch, yaw, roll = _read_rotation(pawn)
        rot = ue.Rotator(pitch, yaw, roll)
    return origin, _forward_of(ue, rot)


def _body_snapshot(ue, world=None):
    bodies = []
    for actor in _actors(ue, world):
        label = actor.get_actor_label()
        kind = logic.classify_label(label)
        if kind not in logic.DYNAMIC_KINDS:
            continue
        bodies.append({"label": label, "kind": kind, "location": _read_location(actor)})
    return bodies


def _linear_falloff(ue):
    value = getattr(getattr(ue, "RadialImpulseFalloff", None), "RIF_LINEAR", None)
    return value if value is not None else "RIF_LINEAR"


def _impulse(ue, actor, impulse):
    comp = _mesh(ue, actor)
    if comp is None:
        return
    _call(comp, "add_impulse", ue.Vector(*impulse), "None", False)


def _impulse_velocity(ue, actor, velocity):
    kind = logic.classify_label(actor.get_actor_label()) if actor is not None else None
    mass = logic.body_spec(kind)["mass"] if kind in logic.BODY else 1.0
    _impulse(ue, actor, tuple(component * mass for component in velocity))


def _divine(ue, actors, action):
    falloff = _linear_falloff(ue)
    origin = action["origin"]
    for item in action["impulses"]:
        comp = _mesh(ue, actors.get(item["label"]))
        if comp is None:
            continue
        radial = getattr(comp, "add_radial_impulse", None)
        if callable(radial):
            radial(
                ue.Vector(*origin),
                action["radius"],
                action["strength"],
                falloff,
                False,
            )
        else:
            _call(comp, "add_impulse", ue.Vector(*item["impulse"]), "None", False)


def _active_handle(ue, controller):
    pawn = controller.get_pawn() if controller is not None and hasattr(controller, "get_pawn") else None
    if pawn is not None:
        handle = _ensure_handle(ue, pawn)
        if handle is not None:
            return handle
    camera = _by_label(ue).get("Elyon.GodCamera")
    if camera is not None:
        return _ensure_handle(ue, camera)
    return None


def _perform(ue, handle, actions, world=None):
    actors = _by_label(ue, world)
    for action in actions:
        op = action["op"]
        if op == "grab" and handle is not None:
            comp = _mesh(ue, actors.get(action["label"]))
            if comp is None:
                continue
            loc = action["location"]
            handle.grab_component_at_location(comp, "None", ue.Vector(loc[0], loc[1], loc[2]))
        elif op == "move" and handle is not None:
            loc = action["location"]
            handle.set_target_location(ue.Vector(loc[0], loc[1], loc[2]))
        elif op == "release" and handle is not None:
            handle.release_component()
        elif op == "throw":
            if handle is not None:
                handle.release_component()
            _impulse_velocity(ue, actors.get(action["label"]), action["velocity"])
        elif op == "push":
            _impulse(ue, actors.get(action["label"]), action["impulse"])
        elif op == "divine":
            _divine(ue, actors, action)


def _tick(ue, delta_time):
    del delta_time
    world = _game_world(ue)
    if world is None:
        return
    _seat_god_pawn(ue, world)
    controller = _player_controller(ue, world)
    if controller is None:
        return
    origin, forward = _view_vectors(ue, controller)
    actions = logic.step_god(
        ue,
        _session(),
        {
            "location": origin,
            "forward": forward,
            "keys": _poll_keys(ue, controller),
            "bodies": _body_snapshot(ue, world),
        },
    )
    _perform(ue, _active_handle(ue, controller), actions, world)
    contacts = [origin]
    move = next((action for action in actions if action["op"] == "move"), None)
    if move is not None:
        contacts.append(move["location"])
    _bend(ue, contacts)
