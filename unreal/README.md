# Elyon in Unreal Engine 5.8

This folder is a vertical slice of the first garden. The playable Electron game in the rest of the repo is unchanged.

You need Unreal Engine 5.8 installed. Open a terminal in this folder and run:

```
UnrealEditor.exe ElyonUE.uproject -ExecutePythonScript=Scripts/run_all.py
```

If `UnrealEditor.exe` is not on your PATH, use the full path, usually `Engine\Binaries\Win64\UnrealEditor.exe` inside your 5.8 install.

The script builds the level `/Game/Maps/Day1_Garden` and saves it, then leaves the editor open. Running it again updates the same actors instead of stacking copies. An older `Elyon.Ground` actor from a previous run is removed. The garden is saved at dawn. Darkness and dawn are the two states of `let_there_be_light` in `Scripts/level_build.py` (false, then true). Sun and sky light colors are `unreal.Color` values (0–255). Fog inscattering is a `unreal.LinearColor`.

## Sky, haze, and the 4060 preset

The sky is a `SkyAtmosphere` plus a `VolumetricCloud`. The script does not spawn a sky sphere. Clouds sit at a normal altitude (layer bottom about 1.6 km). UE 5.8 warns that cached Lumen and real-time sky capture lighting will be clipped when exposure sits above about EV 12. `Config/DefaultEngine.ini` sets `r.EyeAdaptation.CachedLightingPreExposure=8` so daylight near EV 13 stays inside the cache.

`Elyon.Exposure` is an unbound post-process volume. Dawn clamps histogram auto exposure from EV 12 to EV 14. Bloom stays at 0.05. Vignette, chromatic aberration, and lens flares are 0. Light shafts and volumetric fog are off. `Elyon.Fog` is a subtle exponential height fog: dawn density 0.0008, starting 8000 units out, max opacity 0.15. Darkness dims the sun. It does not drop a thick fog in front of the camera.

Water uses Lumen reflections with screen traces on the opaque world, and screen-space reflections for the translucent river and lake (`r.SSR.Quality=2`). Hardware ray tracing is off. Software Lumen (mesh distance fields) is the global illumination path.

The Steam target is an RTX 4060 laptop at 1080p to 1440p with TSR, running smoothly. The project default is the 1440p end of that range: 2560×1440, TSR, screen percentage 67, in `Config/DefaultEngine.ini`, `Config/DefaultScalability.ini` (`[RTX4060_1440p]`), and `Config/DefaultGameUserSettings.ini`. Scalability stays at Epic for view distance, shadows, Lumen, reflections, textures, foliage, and shading. Post and effects stay at High. Nanite is how the forest and rocks stay dense. Cinematic scalability, volumetric fog grids, and hardware ray tracing are left off. 1080p uses the same quality groups and costs less than 1440p.

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

`Elyon.River` is the long channel. `Elyon.Lake` is a still body of water on the west side. Both use the water material above. The authored water fallback is translucent, with low roughness, so screen-space reflections have a surface to hit. Foliage is kept off the river and the lake. The scatter is 48 trees, 28 rocks, and 200 plants, and it is deterministic.

Trees, rocks, and the terrain mesh are Nanite. On a project mesh (Fab or any copied Starter mesh under `/Game`), the script turns Nanite on and saves the asset. Engine Basic Shapes are left untouched; in UE 5.8 those shapes already ship as Nanite meshes. Plants stay ordinary cards, because masked grass often costs more as Nanite than it saves.

Nothing paid is required. A real Starter or Fab mesh keeps its own materials. Engine shapes get a material only when one of the free materials above is already in the project, or when the script can author the `M_Elyon_*` fallback.

To add the free Starter Content pack (included with Unreal, not a purchase):

1. In the editor, open the Content Browser.
2. Add Feature or Content Pack, then add Starter Content.
3. Run the script again. Trees and plants pick up `SM_Bush`, rocks pick up `SM_Rock`, and the terrain can use `M_Ground_Grass`.

Optional free Fab foliage, if you download it yourself and place it at those exact paths: `SM_Tree`, `SM_Rock`, `SM_Plant`, `M_Grass`, and `M_Leaf` under `/Game/Fab/Foliage/`. The script does not download Fab. If neither Starter Content nor those Fab assets are present, the garden falls back to engine cones and spheres with the authored green, rock, and water materials.

The PCG plugin is enabled for later work and is not used by this script.

What else the level contains:

- SkyAtmosphere, VolumetricCloud, a directional sun, a real-time sky light, a thin exponential height fog, and the exposure volume.
- The river, the lake, a player start, and a sphere marker labeled Adam.
- The god camera and the flythrough sequence.

Graphics defaults are Lumen global illumination, Lumen reflections with screen traces, Nanite, virtual shadow maps, TSR, and DirectX 12, tuned for an RTX 4060 laptop at 1440p. Surfaces should use high-quality free engine and Starter Content materials only.

The game and the best free local LLM for intelligent NPCs ship as one install package. The model runs on the player's machine. It is not a paid API and not a separate download. This slice does not contain the model yet.

`Data/` holds the days of creation, Adam and Eve dialogue, and the four endings, exported from the current game. The hands choice becomes wonder when silence was kept, and exile otherwise.

Python remote execution is turned on in `Config/DefaultEngine.ini`. The first time you open the project, the startup map may be missing until the script has run once.
