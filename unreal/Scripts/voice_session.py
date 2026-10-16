"""Apply voice intents to the Day 1 garden. Missing whisper or llama binaries are skipped."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import voice_logic
from level_build import _by_label, _rot, _subsystem, _ue, _vec, let_there_be_light

_USE_DEFAULT = object()

SUBTITLE = "Elyon.VoiceSubtitle"
GROWTH_MESH = "/Engine/BasicShapes/Cone"
RAIN_MESH = "/Engine/BasicShapes/Sphere"


def _warn(ue, message):
    log_warning = getattr(ue, "log_warning", None)
    if log_warning:
        log_warning(message)


def _gaze(ue):
    library = getattr(ue, "EditorLevelLibrary", None)
    if library is not None and hasattr(library, "get_level_viewport_camera_info"):
        try:
            location, _rotation = library.get_level_viewport_camera_info()
            return (float(location.x), float(location.y), 40.0)
        except Exception as exc:
            _warn(ue, f"Elyon voice kept the default gaze: {exc}")
    return (0.0, -200.0, 40.0)


def _show(ue, text):
    actors = _by_label(ue)
    actor = actors.get(SUBTITLE)
    sub = _subsystem(ue)
    if actor is None:
        cls = getattr(ue, "TextRenderActor", None) or getattr(ue, "TargetPoint", None)
        if cls is None:
            return
        actor = sub.spawn_actor_from_class(cls, _vec(ue, -200.0, -900.0, 220.0), _rot(ue))
        actor.set_actor_label(SUBTITLE)
    actor.set_editor_property("tags", ["voice", text])
    for comp_name in ("TextRenderComponent",):
        comp_cls = getattr(ue, comp_name, None)
        if comp_cls is None or not hasattr(actor, "get_component_by_class"):
            continue
        try:
            comp = actor.get_component_by_class(comp_cls)
            comp.set_editor_property("text", text)
        except Exception as exc:
            _warn(ue, f"Elyon subtitle text was not set: {exc}")


def _scale_to(actor, ue, scale):
    actor.set_actor_scale3d(_vec(ue, scale[0], scale[1], scale[2]))


def _spawn_static(ue, label, mesh, x, y, z, scale):
    cls = getattr(ue, "StaticMeshActor", None)
    if cls is None:
        return None
    actor = _subsystem(ue).spawn_actor_from_class(cls, _vec(ue, x, y, z), _rot(ue))
    actor.set_actor_label(label)
    _scale_to(actor, ue, scale)
    if hasattr(ue, "EditorAssetLibrary"):
        try:
            asset = ue.EditorAssetLibrary.load_asset(mesh)
            comp = actor.get_component_by_class(ue.StaticMeshComponent)
            comp.set_static_mesh(asset)
        except Exception as exc:
            _warn(ue, f"Elyon could not mesh {label}: {exc}")
    return actor


def _enrich(resolved, table):
    """Copy data-driven numbers from the intent onto the command."""
    if not resolved.get("id"):
        return resolved
    intent = table["by_id"][resolved["id"]]
    merged = dict(resolved)
    pcg = intent.get("pcg") or {}
    if pcg:
        merged.setdefault("count", pcg.get("count", 8))
        merged.setdefault("radius", pcg.get("radius", 600))
        merged.setdefault("graph", pcg.get("graph"))
    if "impulse" in intent:
        merged.setdefault("impulse", intent["impulse"])
    if "radius" in intent and resolved.get("effect") == "destroy":
        merged.setdefault("radius", intent["radius"])
    return merged


def _present_light(ue):
    light = let_there_be_light(True, ue=ue)
    actors = _by_label(ue)
    sky = actors.get("Elyon.SkyLight")
    if sky and hasattr(ue, "SkyLightComponent"):
        comp = sky.get_component_by_class(ue.SkyLightComponent)
        comp.set_editor_property("intensity", max(1.35, light["skylight_intensity"]))
        if hasattr(comp, "recapture_sky"):
            comp.recapture_sky()


def _present_water(ue, world):
    actors = _by_label(ue)
    river = actors.get("Elyon.River")
    if river is not None:
        river.set_actor_location(_vec(ue, 0.0, 1200.0, 20.0), False, True)
        _scale_to(river, ue, (90.0, 8.0, 0.45))
    if world.get("rain"):
        for index in range(5):
            label = f"Elyon.Rain.{index + 1:02d}"
            if label in actors:
                continue
            _spawn_static(ue, label, RAIN_MESH, -600.0 + index * 280.0, 1200.0, 900.0, (0.4, 0.4, 1.2))


def _present_grow(ue, world, gaze):
    actors = _by_label(ue)
    for point in world.get("growth") or []:
        if point["label"] in actors:
            continue
        _spawn_static(
            ue,
            point["label"],
            GROWTH_MESH,
            point["x"],
            point["y"],
            point["z"],
            (world["foliage_scale"], world["foliage_scale"], world["foliage_scale"] * 2.0),
        )
    radius = float((world.get("pcg") or {}).get("radius") or 600)
    for label, actor in list(_by_label(ue).items()):
        if not label.startswith("Elyon.Plant.") or actor.location is None:
            continue
        dx = actor.location.x - gaze[0]
        dy = actor.location.y - gaze[1]
        if dx * dx + dy * dy > radius * radius:
            continue
        scale = world["foliage_scale"]
        _scale_to(actor, ue, (scale, scale, scale))
    pcg_cls = getattr(ue, "PCGVolume", None)
    graph = (world.get("pcg") or {}).get("graph")
    if pcg_cls is not None and graph and "Elyon.PCGGrow" not in _by_label(ue):
        volume = _subsystem(ue).spawn_actor_from_class(
            pcg_cls, _vec(ue, gaze[0], gaze[1], gaze[2]), _rot(ue)
        )
        volume.set_actor_label("Elyon.PCGGrow")
        volume.set_editor_property("tags", ["pcg", graph])


def _present_calm(ue, world):
    actors = _by_label(ue)
    clouds = actors.get("Elyon.Clouds")
    if clouds is not None:
        clouds.set_editor_property("tags", ["calm", str(world["clouds"])])
        comp_cls = getattr(ue, "VolumetricCloudComponent", None)
        if comp_cls is not None:
            try:
                comp = clouds.get_component_by_class(comp_cls)
                comp.set_editor_property("layer_height", 0.6)
            except Exception as exc:
                _warn(ue, f"Elyon clouds stayed as they were: {exc}")
    wind_cls = getattr(ue, "WindDirectionalSource", None) or getattr(ue, "TargetPoint", None)
    wind = actors.get("Elyon.Wind")
    if wind is None and wind_cls is not None:
        wind = _subsystem(ue).spawn_actor_from_class(wind_cls, _vec(ue, 0.0, 0.0, 400.0), _rot(ue))
        wind.set_actor_label("Elyon.Wind")
    if wind is not None:
        wind.set_editor_property("tags", ["wind", str(world["wind"])])
        comp_cls = getattr(ue, "WindDirectionalSourceComponent", None)
        if comp_cls is not None:
            try:
                comp = wind.get_component_by_class(comp_cls)
                comp.set_editor_property("strength", world["wind"])
            except Exception as exc:
                _warn(ue, f"Elyon wind strength was not set: {exc}")
    fog = actors.get("Elyon.Fog")
    if fog is not None and hasattr(ue, "ExponentialHeightFogComponent"):
        comp = fog.get_component_by_class(ue.ExponentialHeightFogComponent)
        comp.set_editor_property("fog_density", 0.008)


def _present_destroy(ue, world, gaze):
    strike = world["strikes"][-1]
    label = f"Elyon.Lightning.{len(world['strikes']):02d}"
    cls = getattr(ue, "PointLight", None) or getattr(ue, "TargetPoint", None)
    if cls is None:
        return
    actor = _subsystem(ue).spawn_actor_from_class(
        cls, _vec(ue, gaze[0], gaze[1], gaze[2] + 200.0), _rot(ue)
    )
    actor.set_actor_label(label)
    actor.set_editor_property("tags", ["lightning", str(strike["impulse"])])
    if hasattr(ue, "PointLightComponent"):
        try:
            comp = actor.get_component_by_class(ue.PointLightComponent)
            comp.set_editor_property("intensity", 50000.0)
        except Exception as exc:
            _warn(ue, f"Elyon lightning intensity was not set: {exc}")
    radius = float(strike["radius"])
    for other in _subsystem(ue).get_all_level_actors():
        if other.location is None or other.get_actor_label() == label:
            continue
        dx = other.location.x - gaze[0]
        dy = other.location.y - gaze[1]
        if dx * dx + dy * dy > radius * radius:
            continue
        if not hasattr(ue, "StaticMeshComponent"):
            continue
        try:
            mesh = other.get_component_by_class(ue.StaticMeshComponent)
        except Exception:
            continue
        impulse = getattr(mesh, "add_radial_impulse", None)
        if impulse:
            impulse(_vec(ue, gaze[0], gaze[1], gaze[2]), radius, float(strike["impulse"]))


def present(ue, world, resolved, gaze):
    effect = resolved.get("effect")
    if effect == "light":
        _present_light(ue)
    elif effect == "water":
        _present_water(ue, world)
    elif effect == "grow":
        _present_grow(ue, world, gaze)
    elif effect == "calm":
        _present_calm(ue, world)
    elif effect == "destroy":
        _present_destroy(ue, world, gaze)
    _show(ue, resolved.get("subtitle") or world.get("subtitle") or "")


def _accept(ue, state, resolved, gaze):
    resolved = _enrich(resolved, state["table"])
    if resolved.get("id"):
        state["world"] = voice_logic.apply_intent(state["world"], resolved, gaze)
        present(ue, state["world"], resolved, gaze)
    else:
        state["world"]["subtitle"] = resolved.get("subtitle") or ""
        _show(ue, state["world"]["subtitle"])
    return resolved


def press(ue, state, key):
    """Keyboard fallback. 1–5 fire intents. P plays the next sample phrase. V is push-to-talk."""
    ue = _ue(ue)
    action = voice_logic.command_for_key(key, state["table"], state.get("phrase_i", 0))
    gaze = _gaze(ue)
    if action["type"] == "phrase":
        state["phrase_i"] = state.get("phrase_i", 0) + 1
        resolved = voice_logic.resolve_utterance(action["text"], state["table"], llm=state.get("llm"))
        return _accept(ue, state, resolved, gaze)
    if action["type"] == "intent":
        return _accept(ue, state, voice_logic.direct_intent(action["id"], state["table"]), gaze)
    if action["type"] == "push_to_talk":
        state["listen"] = True
        return {"type": "push_to_talk"}
    return None


def release_talk(ue, state, runner):
    """End push-to-talk. runner(wav_path) returns transcript text or None."""
    ue = _ue(ue)
    state["listen"] = False
    if runner is None:
        _show(ue, "Microphone tools are not installed. Press 1-5 to speak as God.")
        return None
    text = runner()
    if not text:
        _show(ue, "Microphone tools are not installed. Press 1-5 to speak as God.")
        return None
    resolved = voice_logic.resolve_utterance(text, state["table"], llm=state.get("llm"))
    return _accept(ue, state, resolved, _gaze(ue))


def _key_down(ue, name):
    player = getattr(ue, "get_play_in_editor_player", None)
    if player is None:
        return False
    controller = player()
    if controller is None or not hasattr(controller, "is_input_key_down"):
        return False
    key_cls = getattr(ue, "Key", None)
    token = key_cls(name) if key_cls else name
    return bool(controller.is_input_key_down(token))


def _poll(ue, state):
    keys = state.setdefault("held", set())
    for name in list((state["table"].get("keyboard") or {})) + [state["table"].get("pushToTalk", "V")]:
        down = _key_down(ue, name)
        if down and name not in keys:
            keys.add(name)
            if name == state["table"].get("pushToTalk"):
                press(ue, state, name)
            else:
                press(ue, state, name)
        elif down and name == state["table"].get("pushToTalk"):
            keys.add(name)
        elif not down and name in keys:
            keys.remove(name)
            if name == state["table"].get("pushToTalk") and state.get("listen"):
                release_talk(ue, state, state.get("runner"))


def install(ue=None, table=None, llm=_USE_DEFAULT, runner=_USE_DEFAULT):
    """Arm subtitles and the keyboard. Tick registration is optional."""
    ue = _ue(ue)
    loaded = table or voice_logic.load_table()
    state = {
        "table": loaded,
        "world": voice_logic.new_world(),
        "phrase_i": 0,
        "held": set(),
        "listen": False,
        "llm": _default_llm(loaded) if llm is _USE_DEFAULT else llm,
        "runner": _default_runner(loaded) if runner is _USE_DEFAULT else runner,
    }
    _show(ue, "")
    log = getattr(ue, "log", None)
    if log:
        log("Elyon voice ready. Press 1-5, P, or hold V.")
    register = getattr(ue, "register_slate_post_tick_callback", None)
    if register is not None and not state.get("ticking"):
        def _tick(_delta):
            try:
                _poll(ue, state)
            except Exception as exc:
                _warn(ue, f"Elyon voice tick skipped: {exc}")

        register(_tick)
        state["ticking"] = True
    return state


def bundled_tool(env_name, fallback_name):
    override = os.environ.get(env_name, "").strip()
    if override:
        return override
    return fallback_name


def _project_root():
    return Path(__file__).resolve().parents[1]


def _named_binary(folder, stem):
    name = f"{stem}.exe" if os.name == "nt" else stem
    return str(_project_root() / "Content" / "Voice" / folder / name)


def whisper_binary():
    return bundled_tool("ELYON_WHISPER", _named_binary("whisper", "whisper-cli"))


def llama_binary():
    return bundled_tool("ELYON_LLAMA", _named_binary("llama", "llama-cli"))


def llama_model_path():
    return bundled_tool("ELYON_LLAMA_MODEL", str(_project_root() / "Content" / "Voice" / "llama" / "Qwen3-4B.gguf"))


def whisper_model_file(table):
    override = os.environ.get("ELYON_WHISPER_MODEL", "").strip()
    if override:
        return override
    roots = (
        voice_logic.WHISPER_DIR,
        _project_root() / "Content" / "Voice" / "whisper",
    )
    for root in roots:
        path = voice_logic.choose_whisper_model(table, os.path.isfile, root=root)
        if os.path.isfile(path):
            return path
    return ""


def _tool_ready(path):
    if not path:
        return False
    if os.path.isfile(path):
        return True
    return shutil.which(path) is not None


def capture_transcript(table):
    """Record a short take and transcribe it. Returns None when the tools are absent."""
    binary = whisper_binary()
    model = whisper_model_file(table)
    ffmpeg = bundled_tool("ELYON_FFMPEG", "ffmpeg")
    if not _tool_ready(binary) or not os.path.isfile(model) or not _tool_ready(ffmpeg):
        return None
    wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav.close()
    try:
        record = voice_logic.ffmpeg_record_command(wav.name)
        record[0] = ffmpeg
        recorded = subprocess.run(record, shell=False, capture_output=True, timeout=20)
        if recorded.returncode != 0:
            return None
        command = voice_logic.whisper_command(wav.name, table, binary, model)
        heard = subprocess.run(command, shell=False, capture_output=True, timeout=60, text=True)
        if heard.returncode != 0:
            return None
        return (heard.stdout or "").strip() or None
    except (OSError, subprocess.TimeoutExpired):
        return None
    finally:
        try:
            os.remove(wav.name)
        except OSError:
            pass


def ask_local_llm(prompt, table):
    """Ask the bundled Qwen model for one JSON intent. Returns None when it is not installed."""
    binary = llama_binary()
    model = llama_model_path()
    if not _tool_ready(binary) or not os.path.isfile(model):
        return None
    command = voice_logic.llama_command(prompt, table, binary, model)
    try:
        result = subprocess.run(command, shell=False, capture_output=True, timeout=30, text=True)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _default_llm(table):
    def _ask(prompt):
        return ask_local_llm(prompt, table)

    return _ask


def _default_runner(table):
    def _run():
        return capture_transcript(table)

    return _run
