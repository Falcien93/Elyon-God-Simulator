"""Entry point for UnrealEditor -ExecutePythonScript=Scripts/run_all.py."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from level_build import build


def main():
    build(dawn=True)


if __name__ == "__main__":
    main()
