"""Log the sun, exposure, and viewport, then save a HighResShot from above the garden.

Run from unreal/:
UnrealEditor.exe ElyonUE.uproject -ExecutePythonScript=Scripts/diag_shot.py

The shot is written under the project's Saved/Screenshots folder.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import level_build
import shot_check
from garden_logic import OVERVIEW, physical_ev100

SHOT_COMMAND = "HighResShot 1920x1080"


def _log(ue, message):
    log = getattr(ue, "log", None)
    if log:
        log(message)
    print(message)


def _warn(ue, message):
    log_warning = getattr(ue, "log_warning", None)
    if log_warning:
        log_warning(message)
    _log(ue, message)


def _prop(target, name):
    getter = getattr(target, "get_editor_property", None)
    if getter is None:
        return None
    try:
        return getter(name)
    except Exception:
        return None


def diagnose(ue=None):
    ue = level_build._ue(ue)
    actors = level_build._by_label(ue)
    sun = actors.get("Elyon.Sun")
    if sun is None:
        _log(ue, "Elyon diag: Elyon.Sun is missing")
    else:
        rotation = sun.get_actor_rotation()
        comp = sun.get_component_by_class(ue.DirectionalLightComponent)
        intensity = _prop(comp, "intensity")
        _log(
            ue,
            "Elyon diag sun: "
            f"pitch={rotation.pitch} yaw={rotation.yaw} roll={rotation.roll} "
            f"intensity_lux={intensity}",
        )
        if rotation.pitch > 0.0:
            _warn(ue, "Elyon diag sun pitch is positive, so the light is aimed up")
    exposure = actors.get("Elyon.Exposure")
    if exposure is None:
        _log(ue, "Elyon diag: Elyon.Exposure is missing")
    else:
        settings = _prop(exposure, "settings")
        iso = _prop(settings, "camera_iso")
        shutter = _prop(settings, "camera_shutter_speed")
        fstop = _prop(settings, "depth_of_field_fstop")
        ev = None
        if iso and shutter and fstop:
            ev = physical_ev100(fstop, shutter, iso)
        _log(
            ue,
            "Elyon diag exposure: "
            f"method={_prop(settings, 'auto_exposure_method')} "
            f"bias={_prop(settings, 'auto_exposure_bias')} "
            f"physical_camera={_prop(settings, 'auto_exposure_apply_physical_camera_exposure')} "
            f"iso={iso} shutter={shutter} fstop={fstop} ev100={ev}",
        )
    editor = level_build._editor_subsystem(ue, "UnrealEditorSubsystem")
    if editor is not None and hasattr(editor, "get_level_viewport_camera_info"):
        try:
            location, rotation = editor.get_level_viewport_camera_info()
            _log(
                ue,
                "Elyon diag viewport before move: "
                f"x={location.x} y={location.y} z={location.z} "
                f"pitch={rotation.pitch} yaw={rotation.yaw}",
            )
        except Exception as exc:
            _log(ue, f"Elyon diag could not read the viewport: {exc}")
    view = level_build.frame_overview(ue)
    _log(
        ue,
        "Elyon diag overview: "
        f"x={view['x']} y={view['y']} z={view['z']} pitch={view['pitch']} yaw={view['yaw']}",
    )
    level_editor = level_build._editor_subsystem(ue, "LevelEditorSubsystem")
    if level_editor is not None and hasattr(level_editor, "editor_invalidate_viewports"):
        level_editor.editor_invalidate_viewports()
    system = getattr(ue, "SystemLibrary", None)
    if system is None or not hasattr(system, "execute_console_command"):
        _log(ue, "Elyon diag: HighResShot is unavailable")
        return view
    started = time.time()
    system.execute_console_command(None, SHOT_COMMAND)
    _log(ue, f"Elyon diag saved {SHOT_COMMAND} under Saved/Screenshots from {OVERVIEW}")
    _check_frame(ue, started)
    return view


def _screenshot_root(ue):
    paths = getattr(ue, "Paths", None)
    saved = None
    if paths is not None and hasattr(paths, "project_saved_dir"):
        try:
            saved = paths.project_saved_dir()
        except Exception:
            saved = None
    if not saved:
        saved = os.path.join(os.getcwd(), "Saved")
    return os.path.join(saved, "Screenshots")


def _check_frame(ue, started):
    root = _screenshot_root(ue)
    if not os.path.isdir(root):
        _log(ue, "Elyon diag frame check skipped: Saved/Screenshots is missing")
        return
    deadline = time.time() + 3.0
    path = None
    while True:
        path = shot_check.newest_png(root, started)
        if path is not None or time.time() >= deadline:
            break
        time.sleep(0.25)
    if path is None:
        _log(ue, "Elyon diag frame check skipped: no new screenshot")
        return
    try:
        with open(path, "rb") as handle:
            kind, lumas = shot_check.classify_png(handle.read())
    except Exception as exc:
        _log(ue, f"Elyon diag frame check failed: {exc}")
        return
    mean = sum(lumas) / len(lumas) if lumas else 0.0
    message = f"Elyon diag frame: {kind} mean_luma={mean:.1f} file={path}"
    if kind in ("black", "white"):
        _warn(ue, message)
        return
    _log(ue, message)


def main(ue=None):
    if ue is None:
        import unreal

        ue = unreal
    ue.EditorPythonScripting.set_keep_python_script_alive(True)
    diagnose(ue)


if __name__ == "__main__":
    main()
