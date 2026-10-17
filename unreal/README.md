# Elyon in Unreal Engine 5.8

This folder is a vertical slice of the first garden. The playable Electron game in the rest of the repo is unchanged.

You need Unreal Engine 5.8 installed. Open a terminal in this folder and run:

```
UnrealEditor.exe ElyonUE.uproject -ExecutePythonScript=Scripts/run_all.py
```

If `UnrealEditor.exe` is not on your PATH, use the full path, usually `Engine\Binaries\Win64\UnrealEditor.exe` inside your 5.8 install.

The script builds the level `/Game/Maps/Day1_Garden` and saves it, then leaves the editor open. Running it again updates the same actors instead of stacking copies. The garden is saved at dawn. Darkness and dawn are the two states of `let_there_be_light` in `Scripts/level_build.py` (false, then true). Sun and sky light colors are `unreal.Color` values (0–255). Fog inscattering is a `unreal.LinearColor`.

What the level contains:

- A large ground plane made from the engine plane shape.
- Sky atmosphere, a directional sun, a sky light, exponential height fog, and volumetric clouds.
- A garden of placeholder trees, rocks, and plants scattered from engine cone and cube shapes. The scatter is deterministic Python, so the same run always places the same objects. The PCG plugin is enabled for later work and is not used by this script.
- A river made from a long flat cube.
- A player start.
- A sphere marker labeled Adam.

No paid or Marketplace assets are required.

Graphics defaults in `Config/DefaultEngine.ini` and `Config/DefaultScalability.ini` are the high end of the engine: Lumen for global illumination and reflections, Nanite, virtual shadow maps, hardware ray tracing when the GPU has it, TSR, DirectX 12, and cinematic scalability. Foliage density is raised so PCG gardens read as dense. Surfaces should use high-quality free engine and Starter Content materials only. The PCG plugin is already enabled for that foliage. This slice still places placeholder shapes with Python so the level can be rebuilt and tested without a PCG graph.

The game and the best free local LLM for intelligent NPCs ship as one install package. The model runs on the player's machine. It is not a paid API and not a separate download. This slice does not contain the model yet.

`Data/` holds the days of creation, Adam and Eve dialogue, and the four endings, exported from the current game. The hands choice becomes wonder when silence was kept, and exile otherwise.

## Four endings

Harmony, exile, wonder, and order are the campaign endings from the page. `Scripts/endings_logic.py` tracks the word, the silence, the serpent, and which choice was taken. `Scripts/endings_build.py` builds a Level Sequence scaffold for each one.

- **Harmony** — Eve leaves the fruit. The garden homes stay. The serpent is gone.
- **Exile** — the hands choice after a spoken commandment. They are clothed, and their homes move to the eastern grass past the river.
- **Wonder** — the hands choice after silence. They stay in the garden, uncondemned.
- **Order** — the question is closed, from Eve or by sending the serpent away. The tree is guarded.

The first ending sticks. Adam and Eve then speak their epilogue. The serpent cannot be addressed. Walking the garden continues after the sequence hold. Each sequence lives at `/Game/Cinematics/Endings/LS_Ending_<id>`. It has a cine camera, a camera cut bound to that camera, a fade up from black that stays clear, and marked frames for the title, each paragraph, and the hold. Running the script again replaces those assets instead of stacking tracks.

```
UnrealEditor.exe ElyonUE.uproject -ExecutePythonScript=Scripts/endings_build.py
```

`Scripts/run_all.py` builds the sequences too when Sequencer Scripting is loaded. That plugin is enabled on `ElyonUE.uproject`.

From this folder:

```
python3 -m unittest discover -s tests -v
```

Python remote execution is turned on in `Config/DefaultEngine.ini`. The first time you open the project, the startup map may be missing until the script has run once.
