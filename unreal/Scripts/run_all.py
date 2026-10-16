"""Entry point for UnrealEditor -ExecutePythonScript=Scripts/run_all.py."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from level_build import build
from physics_build import apply as apply_physics


def main(ue=None):
    if ue is None:
        import unreal

        ue = unreal
    # ExecutePythonScript closes the editor on the next tick unless this stays set.
    ue.EditorPythonScripting.set_keep_python_script_alive(True)
    build(dawn=True, ue=ue)
    # build() deletes Elyon actors that are not in the garden plan, so logs, fruit,
    # wind, and the water body have to be applied again after every build.
    apply_physics(ue)


if __name__ == "__main__":
    main()
