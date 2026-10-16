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

## Physics, water, wind, and the God hand

The same script arms Chaos rigid bodies after it builds the garden. Press Play, then click the viewport so it has focus.

- Left mouse button grabs the rock, log, or fruit you are looking at. Move the view to carry it. Release to drop it.
- Q lifts the held object. Z lowers it.
- Right mouse button throws it along the view.
- F pushes the object you are looking at.
- Middle mouse button is divine force, a radial impulse.

Rocks are about 120 kg. They rest on the ground and sink. Logs are about 22 kg and fruit about 0.2 kg. Logs and fruit spawn in the air so they fall, collide, and stack, and they carry buoyancy so they float. Plants and trees stay kinematic. A plant bends away from the God pawn or a held object, up to 28 degrees, and that bend does not stack on itself. A WindDirectionalSource (strength 0.35, radius 0 so it is directional) drives foliage. If the engine has SimpleGrassWind, the script also builds a wind-sway material. If it does not, the per-actor bend still runs.

The Water plugin is enabled. When `WaterBodyRiver` exists, the script lays a river spline on the cube river (about 700 units wide and 180 deep) and hides the cube. If the plugin class is missing, the cube river stays visible and the rest of the level still saves.

Chaos uses `Config/DefaultEngine.ini`: gravity -980, substepping, and CCD left on so fruit does not tunnel. The God hand is a physics handle on the cine camera, and on Play it is also attached to the possessed pawn after that pawn is seated at the camera. Key names are in `Config/DefaultInput.ini`. The tick polls those keys while the editor stays open, so run the script once and then press Play.

`Data/` holds the days of creation, Adam and Eve dialogue, and the four endings, exported from the current game. The hands choice becomes wonder when silence was kept, and exile otherwise.

Python remote execution is turned on in `Config/DefaultEngine.ini`. The first time you open the project, the startup map may be missing until the script has run once.
