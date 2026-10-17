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

## Days 2 through 7

`Scripts/run_creation.py` builds the rest of the week and leaves the editor on the seventh day. `/Game/Maps/Day1_Garden` is unchanged. The new maps use the same placeholder shapes, the same idempotent rebuild, and the same color split: sun and sky lights are `unreal.Color` values (0–255), and fog inscattering is a `unreal.LinearColor`.

```
UnrealEditor.exe ElyonUE.uproject -ExecutePythonScript=Scripts/run_creation.py
```

| Day | Map | What the script places |
| --- | --- | --- |
| 2 | `/Game/Maps/Day2_Waters` | Firmament, waters above, sea, river, and lake |
| 3 | `/Game/Maps/Day3_Land` | Dry land, shore, grass, flowers, and the two trees |
| 4 | `/Game/Maps/Day4_Lights` | Sun, moon, and stars |
| 5 | `/Game/Maps/Day5_Creatures` | Fish in the waters and birds over the land |
| 6 | `/Game/Maps/Day6_Humanity` | Deer, sheep, a lion, Adam, and Eve |
| 7 | `/Game/Maps/Day7_Rest` | Evening light, and a presence drawn near both of them |

Each map keeps what the earlier days made. Running the script again updates those actors instead of stacking copies. Placement is deterministic and follows the garden's water, land, and clearing rules from `Data/creation_week.json`. A later day stays locked until the earlier days are done, including the first day's light. Fish and birds are the fifth day. The land animals stand with Adam and Eve on the sixth. Counts match the grove and the creature seeding in the playable garden.

`set_hours` in `Scripts/creation_build.py` switches a map that already has the sun between day, night, and evening. The seventh day is saved at evening. Story lines for all eight days stay in `Data/days.json`. The week file names which of those beats each map completes.

`Data/` holds the days of creation, Adam and Eve dialogue, and the four endings, exported from the current game. The hands choice becomes wonder when silence was kept, and exile otherwise.

Python remote execution is turned on in `Config/DefaultEngine.ini`. The first time you open the project, the startup map may be missing until the script has run once.
