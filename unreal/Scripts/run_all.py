"""Entry point for UnrealEditor -ExecutePythonScript=Scripts/run_all.py."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import level_build


def main(ue=None):
    if ue is None:
        import unreal

        ue = unreal
    # ExecutePythonScript closes the editor on the next tick unless this stays set.
    ue.EditorPythonScripting.set_keep_python_script_alive(True)
    level_build.build(dawn=True, ue=ue)
    # build() already frames this. Set it again so the perspective view stays on the overview.
    level_build.frame_overview(ue)
    log = getattr(ue, "log", None)
    if log:
        log("Elyon run_all finished")


if __name__ == "__main__":
    main()
