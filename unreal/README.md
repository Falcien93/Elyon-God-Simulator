# Elyon in Unreal Engine 5.8

This folder is a vertical slice of the first garden. The playable Electron game in the rest of the repo is unchanged.

You need Unreal Engine 5.8 installed. Open a terminal in this folder and run:

```
UnrealEditor.exe ElyonUE.uproject -ExecutePythonScript=Scripts/run_all.py
```

If `UnrealEditor.exe` is not on your PATH, use the full path, usually `Engine\Binaries\Win64\UnrealEditor.exe` inside your 5.8 install.

The script builds the level `/Game/Maps/Day1_Garden` and saves it, then leaves the editor open. Running it again updates the same actors instead of stacking copies. An older `Elyon.Ground` actor from a previous run is removed. The garden is saved at dawn. Darkness and dawn are the two states of `let_there_be_light` in `Scripts/level_build.py` (false, then true). Sun and sky light colors are `unreal.Color` values (0–255). Fog inscattering is a `unreal.LinearColor`.

## Sky, haze, and the 4060 preset

The sky is a `SkyAtmosphere` plus a `VolumetricCloud`. The script does not spawn a sky sphere. Dawn clouds sit low (layer bottom 1.2 km, height 2.8 km) with a warm ground albedo, and the view sample scale is 0.6 so the 4060 is not asked for a full cloud march. `Config/DefaultEngine.ini` sets `r.EyeAdaptation.CachedLightingPreExposure=8`. On UE 5.8 that keeps cached Lumen and real-time sky capture valid from EV -4 to EV 16.

`Elyon.Exposure` is an unbound post-process volume with manual exposure, so the view does not wait on eye adaptation. Dawn turns on physical camera exposure: ISO 100, shutter 1/250 s, f/8, bias 0. That is about EV 14 for the 120000 lux sun, inside the cached-lighting window. A manual bias of -15 left the frame black, and +12 left it white. White balance at dawn is 4300 K. UE 5.8 has no histogram log min/max on `PostProcessSettings`. The sun pitch is -20 (golden hour), color warm orange. Python's `Rotator` constructor is roll, pitch, yaw, so the script sets the named fields. `Elyon.SkyLight` is a movable real-time capture at intensity 0.6 with a warm tint, so a blue captured sky does not paint the shadows cyan. Its recapture is queued for the next editor tick so `run_all.py` can finish. Bloom stays at 0.05. Vignette, chromatic aberration, and lens flares are 0. Light shafts and volumetric fog are off. `Elyon.Fog` is a thin warm exponential height fog: dawn density 0.0016, inscatter a golden haze, starting 4500 units out, max opacity 0.2. It is not a wall in front of the camera. The terrain is a flat plane on the ground. The overview camera sits at z 2600, south of the garden. Darkness dims the sun. It does not drop a thick fog in front of the camera.

Water uses Lumen reflections with screen traces on the opaque world, and screen-space reflections for the translucent river and lake (`r.SSR.Quality=2`). Hardware ray tracing is off. Software Lumen (mesh distance fields) is the global illumination path.

The Steam target is an RTX 4060 laptop at 1080p to 1440p with TSR, running smoothly. The project default is the 1440p end of that range: 2560×1440, TSR, screen percentage 67, in `Config/DefaultEngine.ini`, `Config/DefaultScalability.ini` (`[RTX4060_1440p]`), and `Config/DefaultGameUserSettings.ini`. Scalability stays at Epic for view distance, shadows, Lumen, reflections, textures, foliage, and shading. Post and effects stay at High. Nanite is how the forest and rocks stay dense. Cinematic scalability, volumetric fog grids, and hardware ray tracing are left off. 1080p uses the same quality groups and costs less than 1440p.

## God view

`Elyon.GodCamera` is a cine camera with a 24mm lens, placed above the garden. The script also saves a level sequence at `/Game/Cinematics/LS_GodFlythrough`. The move is 28 seconds: a high opening, a pass over the trees and the river, a look toward the low sun, then a wide hold. Section ranges are plain integers at the 24 fps display rate, which is what `set_range` takes in UE 5.8. The camera cut is `sequence.add_track(MovieSceneCameraCutTrack)` on a possessable of `Elyon.GodCamera`. UE 5.8 has no master-track API. The script does not play the sequence, so the perspective viewport is not left inside that camera. It frames an overview south of the garden, looking north and down. Open `LS_GodFlythrough` and press play when you want the flythrough.

`Scripts/run_all.py` calls `Scripts/diag_shot.py` after the build. That logs the sun rotation and lux, the exposure camera, and the viewport location, then moves to the overview and runs `HighResShot 1920x1080`. The image lands in `Saved/Screenshots`. The script warns if that frame is all black or all white. Viewport calls go through `UnrealEditorSubsystem` and `LevelEditorSubsystem`. You can also run `diag_shot.py` on its own.

## Terrain and free foliage

`Elyon.Terrain` is a large terrain mesh: the engine plane, scaled to cover the garden, with a grass material. It is not a Landscape actor. A scripted Landscape with no heightmap would come in empty or fail in the editor, so this slice uses the plane.

Foliage uses only free assets. The script checks these paths in order and uses the first one that exists:

| Role | First choice | Starter Content | Engine fallback |
| --- | --- | --- | --- |
| Tree | `/Game/Fab/Foliage/SM_Tree` | `/Game/StarterContent/Props/SM_Bush` | `/Engine/BasicShapes/Sphere` crown on a cylinder trunk |
| Trunk | | `/Game/StarterContent/Materials/M_Wood_Oak` (bark) | `/Engine/BasicShapes/Cylinder` |
| Rock | `/Game/Fab/Foliage/SM_Rock` | `/Game/StarterContent/Props/SM_Rock` | `/Engine/BasicShapes/Sphere` |
| Plant | `/Game/Fab/Foliage/SM_Plant` | `/Game/StarterContent/Props/SM_Bush` | `/Engine/BasicShapes/Sphere` |
| Grass material | `/Game/Fab/Foliage/M_Grass` | `/Game/StarterContent/Materials/M_Ground_Grass` | `/Game/Materials/M_Elyon_Grass` |
| Leaf material | `/Game/Fab/Foliage/M_Leaf` | `/Game/StarterContent/Materials/M_Ground_Moss` | `/Game/Materials/M_Elyon_Leaf` |
| Rock material | | `/Game/StarterContent/Materials/M_Rock_Basalt` | `/Game/Materials/M_Elyon_Rock` |
| Bark material | | `/Game/StarterContent/Materials/M_Wood_Oak` | `/Game/Materials/M_Elyon_Bark` |
| Water material | `/Water/Materials/WaterSurface/Water_Material_Lake` | `/Game/StarterContent/Materials/M_Water_Lake` | `/Game/Materials/M_Elyon_Water` |

`Elyon.River` is the long channel. `Elyon.Lake` is a still body of water on the west side. Both stay thin cubes. The Water plugin is enabled so its free lake material can be used when that asset is mounted. The script does not spawn Water Body splines. The authored water fallback is Single Layer Water when the engine exposes that shading model, deep green-black rather than cyan, translucent, with roughness that moves. Screen-space reflections and Lumen have a surface to hit. The authored grass and bark lerp two colors through world-position noise, so the ground is not one flat green. Foliage is kept off the river and the lake. The scatter is 48 trees, 28 rocks, and 200 plants, and it is deterministic. A complete Fab `SM_Tree` hides the extra trunk. A bush or a sphere crown keeps the cylinder.

Trees, rocks, and the terrain mesh are Nanite. On a project mesh (Fab or any copied Starter mesh under `/Game`), the script turns Nanite on and saves the asset. Engine Basic Shapes are left untouched; in UE 5.8 those shapes already ship as Nanite meshes. Plants stay ordinary cards, because masked grass often costs more as Nanite than it saves.

Nothing paid is required. A real Starter or Fab mesh keeps its own materials. Engine shapes get a material only when one of the free materials above is already in the project, or when the script can author the `M_Elyon_*` fallback.

To add the free Starter Content pack (included with Unreal, not a purchase):

1. In the editor, open the Content Browser.
2. Add Feature or Content Pack, then add Starter Content.
3. Run the script again. Tree crowns and plants pick up `SM_Bush`, rocks pick up `SM_Rock`, and the terrain can use `M_Ground_Grass`.

Optional free Fab foliage, if you download it yourself and place it at those exact paths: `SM_Tree`, `SM_Rock`, `SM_Plant`, `M_Grass`, and `M_Leaf` under `/Game/Fab/Foliage/`. The script does not download Fab. If neither Starter Content nor those Fab assets are present, each tree is a cylinder trunk with a sphere crown, plants are small spheres, and the ground, bark, and water use the authored materials. Nothing in this list is a paid asset.

The PCG plugin is enabled for later work and is not used by this script.

What else the level contains:

- SkyAtmosphere, VolumetricCloud, a directional sun, a real-time sky light, a thin exponential height fog, and the exposure volume.
- The river, the lake, a player start, and a sphere marker labeled Adam.
- The god camera and the flythrough sequence.

Graphics defaults are Lumen global illumination, Lumen reflections with screen traces, Nanite, virtual shadow maps, TSR, and DirectX 12, tuned for an RTX 4060 laptop at 1440p. Virtual shadow maps need Shader Model 6, so `Config/DefaultEngine.ini` adds `PCD3D_SM6` under the Windows D3D12 targeted shader formats. Surfaces should use high-quality free engine and Starter Content materials only. The sky atmosphere distance scale uses the engine property `aerial_pespective_view_distance_scale` (UE spells Pespective without an r).

The game and the best free local LLM for intelligent NPCs ship as one install package. The model runs on the player's machine. It is not a paid API and not a separate download. This slice does not contain the model yet.

## Voice as God

Spoken commands are the hook. Hold **V** and speak, or press **1–5** when you have no microphone. A hotword is optional: start the line with "elyon". The transcript hits a fuzzy phrase table in `Data/intents.json` first. Synonyms such as "let there be light", "light", and "bring forth light" all map to LIGHT. Qwen3 4B through llama.cpp is asked for a JSON intent only when that matcher misses. Speech-to-text is whisper.cpp, `small.en` then `base.en`, with the GPU left on for an RTX 4060 (the command omits whisper.cpp's `-ng` flag).

What the five starter intents do:

| Key | Intent | World change |
| --- | --- | --- |
| 1 | LIGHT | The sun rises out of darkness. Sky light and Lumen brighten. |
| 2 | WATER | The river fills. Say it again and rain begins. |
| 3 | GROW | Foliage appears in a ring around the gaze point, and nearby plants scale up. A PCG volume is spawned when the class exists, using `/Game/PCG/GrowAroundGaze`. |
| 4 | CALM | Wind, clouds, and the storm settle. |
| 5 | DESTROY | Lightning at the gaze point, plus a radial impulse of 25000 where the mesh supports it. |

**P** cycles sample phrases through the same matcher. The subtitle actor `Elyon.VoiceSubtitle` shows what God said.

The whisper and llama binaries are not in this repo. They ship inside the one install, under `Content/Voice/whisper` (`whisper-cli`, `ggml-small.en.bin`, `ggml-base.en.bin`) and `Content/Voice/llama` (`llama-cli`, `Qwen3-4B.gguf`). Overrides, if you already have a local build: `ELYON_WHISPER`, `ELYON_WHISPER_MODEL`, `ELYON_LLAMA`, `ELYON_LLAMA_MODEL`, `ELYON_FFMPEG`, and `ELYON_FFMPEG_INPUT` (`dshow:audio=Microphone` on Windows, `pulse:default` on Linux). Do not download weights from the editor script. If the tools are missing, the subtitle says to press 1–5 and nothing is spawned.

Adding a command is a new block in `Data/intents.json` with an `id`, `phrases`, a `line`, and an existing `effect` (`light`, `water`, `grow`, `calm`, `destroy`). A brand-new effect also needs a branch in `apply_intent` and `present`.

This path is separate from the desktop Living Voices option, which uses whisper-cli, Ollama, and Piper inside the Electron app and stays off until that setting is enabled.

### Run it

From this folder:

```
UnrealEditor.exe ElyonUE.uproject -ExecutePythonScript=Scripts/run_all.py
```

If `UnrealEditor.exe` is not on your PATH, use `Engine\Binaries\Win64\UnrealEditor.exe` inside the 5.8 install. The editor stays open. Press Play, then click the viewport so it has focus.

### Keyboard, no microphone

1. Run the script above.
2. Press Play and click the viewport.
3. Press **1** LIGHT, **2** WATER, **3** GROW, **4** CALM, **5** DESTROY.
4. Press **P** to send the next sample phrase ("let there be light", then "fill the river", and so on).
5. Read `Elyon.VoiceSubtitle`. The level is already at dawn after the script, with the sun at 120000 lux. LIGHT calls `let_there_be_light(True)` again and raises the sky light to at least 1.35. It does not dim the sun. Say WATER twice: the first fills the river, the second starts rain.

Running the script again rebuilds the garden, clears voice-spawned actors, and arms the listener once more.

### Microphone on the laptop

1. Place a CUDA or Vulkan whisper.cpp build on the machine. GPU stays on: do not pass `-ng`. Put `whisper-cli` and `ggml-small.en.bin` (fallback `ggml-base.en.bin`) in `Content/Voice/whisper`, or point `ELYON_WHISPER` and `ELYON_WHISPER_MODEL` at them.
2. Put `ffmpeg` on PATH. On Windows the default input is `dshow:audio=Microphone`. If that name is wrong, list devices with `ffmpeg -list_devices true -f dshow -i dummy` and set `ELYON_FFMPEG_INPUT=dshow:audio=Exact Device Name`. On Linux the default is `pulse:default`.
3. Optional: put llama.cpp's `llama-cli` and a Qwen3 4B GGUF in `Content/Voice/llama` for lines the phrase table does not know. The call is local, `-n 80 --temp 0 -no-cnv`, and it returns JSON only. If llama is missing, an unmatched line stays on the subtitle and the garden does not change.
4. Run the editor script, press Play, click the viewport.
5. Hold **V** for about four seconds, say "let there be light" or "elyon, let there be light", and release **V**. The script records 16 kHz mono audio, then runs `whisper-cli -m <model> -f <wav> -l en -nt` with no `-ng`.
6. The subtitle shows the line you spoke, and the sun, river, plants, wind, or lightning follow the intent.

`Data/` holds the days of creation, Adam and Eve dialogue, and the four endings, exported from the current game. The hands choice becomes wonder when silence was kept, and exile otherwise.

Python remote execution is turned on in `Config/DefaultEngine.ini`. The first time you open the project, the startup map may be missing until the script has run once.
