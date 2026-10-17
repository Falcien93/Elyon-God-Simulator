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
- Adam and Eve, placed by the same script after the garden actors. See below.

No paid or Marketplace assets are required.

Graphics defaults in `Config/DefaultEngine.ini` and `Config/DefaultScalability.ini` are the high end of the engine: Lumen for global illumination and reflections, Nanite, virtual shadow maps, hardware ray tracing when the GPU has it, TSR, DirectX 12, and cinematic scalability. Foliage density is raised so PCG gardens read as dense. Surfaces should use high-quality free engine and Starter Content materials only. The PCG plugin is already enabled for that foliage. This slice still places placeholder shapes with Python so the level can be rebuilt and tested without a PCG graph.

The game and the best free local LLM for intelligent NPCs ship as one install package. The model runs on the player's machine. It is not a paid API and not a separate download. This slice does not contain the model yet.

`Data/` holds the days of creation, Adam and Eve dialogue, and the four endings, exported from the current game. The hands choice becomes wonder when silence was kept, and exile otherwise.

Python remote execution is turned on in `Config/DefaultEngine.ini`. The first time you open the project, the startup map may be missing until the script has run once.

## Adam and Eve

`run_all.py` saves the garden, then places `Elyon.Person.Adam` and `Elyon.Person.Eve` in `/Game/Maps/Day1_Garden`. They are engine cylinders. Adam is heavier and taller (78 kg, 1.78 m) than Eve (58 kg, 1.62 m). The sphere marker `Elyon.Adam` stays where it is. Running the script again moves the same two actors instead of stacking copies. A garden rebuild drops them, because the garden plan does not list them, and `run_all.py` puts them back.

The day follows `Data/characters.json`: wake, eat, drink, work, rest. Hunger, thirst, and fatigue change with that day. Eating, drinking, and rest ease the matching need when the fire has a meal, water, and a place to lie down. A tired person moves more slowly, and the card line says so. Work is gathering on the near bank. They walk around the river. They do not step in it. `come` leads along that bank toward Elyon, or toward a point a later voice names. `stay` and `resume` send them back to the day. `work` holds them at the work until rest, or until they are told to resume.

Speech is a hook for a later local voice. Addressing someone records `needs_voice: true` and leaves `model_called` false. The request carries who they are, the act, the needs, the scripted node in `Data/dialogue.json`, and that node's first line. With no voice attached, that scripted line is what they say. Nothing in this folder downloads a model or calls an API.

From the editor Python console, after `run_all.py`:

```
import characters_build
characters_build.step_day(30)
characters_build.address("eve", "Are you awake?")
```

`step_day` moves them and does not save. The garden build saves, then spawn saves again so Adam and Eve are in the level.

Tests, from the repo root:

```
python3 -m unittest discover -s unreal/tests -v
```
