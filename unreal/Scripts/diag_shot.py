"""Log the sun, exposure, and viewport, then save a HighResShot from above the garden.

Run from unreal/:
UnrealEditor.exe ElyonUE.uproject -ExecutePythonScript=Scripts/diag_shot.py

The shot is written under the project's Saved/Screenshots folder.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import level_build
from garden_logic import OVERVIEW

SHOT_COMMAND = "HighResShot 1920x1080"


def _log(ue, message):
    log = getattr(ue, "log", None)
    if log:
        log(message)
    print(message)


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
    exposure = actors.get("Elyon.Exposure")
    if exposure is None:
        _log(ue, "Elyon diag: Elyon.Exposure is missing")
    else:
        settings = _prop(exposure, "settings")
        _log(
            ue,
            "Elyon diag exposure: "
            f"method={_prop(settings, 'auto_exposure_method')} "
            f"min_ev100={_prop(settings, 'auto_exposure_min_brightness')} "
            f"max_ev100={_prop(settings, 'auto_exposure_max_brightness')} "
            f"bias={_prop(settings, 'auto_exposure_bias')} "
            f"physical_camera={_prop(settings, 'auto_exposure_apply_physical_camera_exposure')}",
        )
    library = getattr(ue, "EditorLevelLibrary", None)
    if library is not None and hasattr(library, "get_level_viewport_camera_info"):
        try:
            location, rotation = library.get_level_viewport_camera_info()
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
    if library is not None and hasattr(library, "editor_invalidate_viewports"):
        library.editor_invalidate_viewports()
    system = getattr(ue, "SystemLibrary", None)
    if system is None or not hasattr(system, "execute_console_command"):
        _log(ue, "Elyon diag: HighResShot is unavailable")
        return view
    system.execute_console_command(None, SHOT_COMMAND)
    _log(ue, f"Elyon diag saved {SHOT_COMMAND} under Saved/Screenshots from {OVERVIEW}")
    return view


def main(ue=None):
    if ue is None:
        import unreal

        ue = unreal
    ue.EditorPythonScripting.set_keep_python_script_alive(True)
    diagnose(ue)


if __name__ == "__main__":
    main()
