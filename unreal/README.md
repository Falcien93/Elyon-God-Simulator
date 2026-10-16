# Elyon in Unreal Engine 5.8

This folder is a vertical slice of the first garden. The playable Electron game in the rest of the repo is unchanged. Nothing here was run inside Unreal Editor.

You need Unreal Engine 5.8 installed. Open a terminal in this folder and run:

```
UnrealEditor.exe ElyonUE.uproject -ExecutePythonScript=Scripts/run_all.py
```

If `UnrealEditor.exe` is not on your PATH, use the full path, usually `Engine\Binaries\Win64\UnrealEditor.exe` inside your 5.8 install.

The script builds the level `/Game/Maps/Day1_Garden` and saves it. Running it again updates the same actors instead of stacking copies. The garden is saved at dawn. Darkness and dawn are the two states of `let_there_be_light` in `Scripts/level_build.py` (false, then true).

What the level contains:

- A large ground plane made from the engine plane shape.
- Sky atmosphere, a directional sun, a sky light, exponential height fog, and volumetric clouds.
- A garden of placeholder trees, rocks, and plants scattered from engine cone and cube shapes. The scatter is deterministic Python, so the same run always places the same objects. The PCG plugin is enabled for later work and is not used by this script.
- A river made from a long flat cube.
- A player start.
- A sphere marker labeled Adam.

No paid or Marketplace assets are required.

`Data/` holds the days of creation, Adam and Eve dialogue, and the four endings, exported from the current game. The hands choice becomes wonder when silence was kept, and exile otherwise.

Python remote execution is turned on in `Config/DefaultEngine.ini`. The first time you open the project, the startup map may be missing until the script has run once.
