"""Entry point for UnrealEditor -ExecutePythonScript=Scripts/run_creation.py."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from creation_build import build_week


def main(ue=None):
    if ue is None:
        import unreal

        ue = unreal
    # ExecutePythonScript closes the editor on the next tick unless this stays set.
    ue.EditorPythonScripting.set_keep_python_script_alive(True)
    build_week(ue)


if __name__ == "__main__":
    main()
