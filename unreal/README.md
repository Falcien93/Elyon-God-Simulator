# Elyon in Unreal Engine 5.8

This folder is a vertical slice of the first garden. The playable Electron game in the rest of the repo is unchanged.

You need Unreal Engine 5.8 installed. Open a terminal in this folder and run:

```
UnrealEditor.exe ElyonUE.uproject -ExecutePythonScript=Scripts/run_all.py
```

If `UnrealEditor.exe` is not on your PATH, use the full path, usually `Engine\Binaries\Win64\UnrealEditor.exe` inside your 5.8 install.

The script builds the level `/Game/Maps/Day1_Garden` and saves it, then leaves the editor open. Running it again updates the same actors instead of stacking copies. An older `Elyon.Ground` actor from a previous run is removed. The garden is saved at dawn. Darkness and dawn are the two states of `let_there_be_light` in `Scripts/level_build.py` (false, then true). Sun and sky light colors are `unreal.Color` values (0–255). Fog inscattering is a `unreal.LinearColor`.

## Golden hour

UE 5.8 warns that cached Lumen and real-time sky capture lighting will be clipped when exposure sits above about EV 12. The default pre-exposure of 4 leaves that window too narrow for daylight. `Config/DefaultEngine.ini` sets `r.EyeAdaptation.CachedLightingPreExposure=8` so a golden-hour exposure near EV 13 stays inside the cache. Volumetric fog and light shafts are turned on in that same file.

The level places an unbound `PostProcessVolume` labeled `Elyon.Exposure`. Dawn uses histogram auto exposure clamped from EV 12 to EV 14, a warm white balance, a little bloom, and a light vignette. Darkness uses a low window from EV -1 to EV 2 so night is not crushed by the day clamp. Height fog stays thin (density 0.002) so the garden does not become a grey wall. Volumetric fog, directional inscattering, and the sun's light-shaft bloom are what carry the god rays. The sun is a low amber light at intensity 8, with a wider source angle, volumetric shadows, and atmosphere sun light so the sky disk and the rays agree. Volumetric clouds sit low for a late-afternoon sky.

## God view

`Elyon.GodCamera` is a cine camera with a 24mm lens, placed above the garden. The script also saves a level sequence at `/Game/Cinematics/LS_GodFlythrough` and asks the editor to play it. The move is 28 seconds: a high opening, a pass over the trees and the river, a look toward the low sun, then a wide hold. The editor stays open on that camera. If the sequence does not start on its own, open `LS_GodFlythrough` and press play.

## Terrain and free foliage

`Elyon.Terrain` is a large terrain mesh: the engine plane, scaled to cover the garden, with a grass material. It is not a Landscape actor. A scripted Landscape with no heightmap would come in empty or fail in the editor, so this slice uses the plane.

Foliage uses only free assets. The script checks these paths in order and uses the first one that exists:

| Role | First choice (optional Fab) | Starter Content | Engine fallback |
| --- | --- | --- | --- |
| Tree | `/Game/Fab/Foliage/SM_Tree` | `/Game/StarterContent/Props/SM_Bush` | `/Engine/BasicShapes/Cone` |
| Rock | `/Game/Fab/Foliage/SM_Rock` | `/Game/StarterContent/Props/SM_Rock` | `/Engine/BasicShapes/Sphere` |
| Plant | `/Game/Fab/Foliage/SM_Plant` | `/Game/StarterContent/Props/SM_Bush` | `/Engine/BasicShapes/Cone` |
| Grass material | `/Game/Fab/Foliage/M_Grass` | `/Game/StarterContent/Materials/M_Ground_Grass` | `/Game/Materials/M_Elyon_Grass` |
| Leaf material | `/Game/Fab/Foliage/M_Leaf` | `/Game/StarterContent/Materials/M_Ground_Moss` | `/Game/Materials/M_Elyon_Leaf` |
| Rock material | | `/Game/StarterContent/Materials/M_Rock_Basalt` | `/Game/Materials/M_Elyon_Rock` |
| Water material | | `/Game/StarterContent/Materials/M_Water_Lake` | `/Game/Materials/M_Elyon_Water` |

`Elyon.River` is the long channel. `Elyon.Lake` is a still body of water on the west side. Both use the water material above. Foliage is kept off the river and the lake. The scatter is dense (48 trees, 28 rocks, and 200 plants) and deterministic, so the same run always places the same objects.

Nothing paid is required. A real Starter or Fab mesh keeps its own materials. Engine shapes get a material only when one of the free materials above is already in the project, or when the script can author the `M_Elyon_*` fallback.

To add the free Starter Content pack (included with Unreal, not a purchase):

1. In the editor, open the Content Browser.
2. Add Feature or Content Pack, then add Starter Content.
3. Run the script again. Trees and plants pick up `SM_Bush`, rocks pick up `SM_Rock`, and the terrain can use `M_Ground_Grass`.

Optional free Fab foliage, if you download it yourself and place it at those exact paths: `SM_Tree`, `SM_Rock`, `SM_Plant`, `M_Grass`, and `M_Leaf` under `/Game/Fab/Foliage/`. The script does not download Fab. If neither Starter Content nor those Fab assets are present, the garden falls back to engine cones and spheres with the authored green, rock, and water materials.

The PCG plugin is enabled for later work and is not used by this script.

What else the level contains:

- Sky atmosphere, a directional sun, a real-time sky light, exponential height fog with volumetric fog, volumetric clouds, light shafts, and the exposure volume.
- The river, the lake, a player start, and a sphere marker labeled Adam.
- The god camera and the flythrough sequence.

Graphics defaults in `Config/DefaultEngine.ini` and `Config/DefaultScalability.ini` are the high end of the engine: Lumen for global illumination and reflections, Nanite, virtual shadow maps, hardware ray tracing when the GPU has it, TSR, DirectX 12, and cinematic scalability. Foliage density is raised so a later PCG garden can read as dense. Surfaces should use high-quality free engine and Starter Content materials only.

The game and the best free local LLM for intelligent NPCs ship as one install package. The model runs on the player's machine. It is not a paid API and not a separate download. This slice does not contain the model yet.

`Data/` holds the days of creation, Adam and Eve dialogue, and the four endings, exported from the current game. The hands choice becomes wonder when silence was kept, and exile otherwise.

Python remote execution is turned on in `Config/DefaultEngine.ini`. The first time you open the project, the startup map may be missing until the script has run once.
