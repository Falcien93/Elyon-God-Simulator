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

Python remote execution is turned on in `Config/DefaultEngine.ini`. The first time you open the project, the startup map may be missing until the script has run once.

## Package a playable Windows demo

`Scripts/package_demo.ps1` cooks this project into a Win64 build you can zip and run. Continuous integration does not install Unreal Engine 5.8, so it never calls RunUAT. `tests/test_package_demo.py` reads the script and checks the arguments.

On the Windows machine that packages the demo, install Unreal Engine 5.8 at `C:\Program Files\Epic Games\UE_5.8`. Copy this `unreal` folder to `C:\ElyonSlice` so the project file is `C:\ElyonSlice\ElyonUE.uproject`. Open that project and run `Scripts/run_all.py` once, so `/Game/Maps/Day1_Garden` is saved on disk. Then, in PowerShell:

```
powershell -ExecutionPolicy Bypass -File C:\ElyonSlice\Scripts\package_demo.ps1
```

That defaults to Shipping. The same script packages Development:

```
powershell -ExecutionPolicy Bypass -File C:\ElyonSlice\Scripts\package_demo.ps1 -Configuration Development
```

The map list defaults to `/Game/Maps/Day1_Garden`. Pass `-Maps` as a PowerShell list of `/Game/...` paths to cook more than one. The script joins that list with `+` and passes it as RunUAT `-map`:

```
powershell -ExecutionPolicy Bypass -File C:\ElyonSlice\Scripts\package_demo.ps1 -Maps '/Game/Maps/Day1_Garden','/Game/Maps/AnotherMap'
```

`AnotherMap` is only the shape of a second entry. This slice saves `/Game/Maps/Day1_Garden`.

The script calls `Engine\Build\BatchFiles\RunUAT.bat` with `BuildCookRun`, `-platform=Win64`, `-clientconfig` set to Shipping or Development, and `-build -cook -stage -pak -archive -prereqs -compressed`. It refuses any other configuration, an empty map list, a map that is not a `/Game/` asset path, and paths that contain shell metacharacters.

Shipping lands in `C:\ElyonSlice\Packaged\Shipping` (Development uses the `Development` folder). The playable files are the `Windows` archive inside that folder (`WindowsNoEditor` and `WindowsClient` are accepted when that is the folder RunUAT wrote). The script zips that folder to `C:\ElyonSlice\Packaged\ElyonUE-Win64-Shipping.zip` and writes `C:\ElyonSlice\Packaged\package_demo-Shipping.log`. The log records the engine, the project, the configuration, the maps, the full RunUAT command, the exit code, and the zip path. RunUAT's own console output is `package_demo-Shipping.uat.log` beside it. Unzip the archive and run `ElyonUE.exe`.

`-DryRun` writes that log and the RunUAT arguments, then stops. It does not cook, and it does not zip. `-EngineRoot`, `-Project`, `-ArchiveRoot`, `-ZipPath`, and `-LogPath` override the paths above. The script does not upload the zip anywhere. While a real package is running, RunUAT's lines are printed and copied into the `.uat.log` file.
