# Merge plan after the Day 1 garden

Draft PRs #12–#22 were branched from `main` in parallel. None of them contain PR #11 (`cursor/garden-look-66c6` at `7b1556e`). That commit is `main` plus the garden look (0 commits behind `main`, 10 ahead). Test each later PR on a laptop only after #11 is merged, and only one at a time.

This note was checked in a throwaway worktree. Nothing here rebases, force-pushes, or edits those PR branches. GitHub "mergeable" means the PR applies to today's `main`. It does not mean the PR applies to #11.

`run_all.py` pickup means `UnrealEditor -ExecutePythonScript=Scripts/run_all.py` runs the new feature. A separate script does not count.

## Order

Merge #11 first, after the editor shot looks right. Do not edit that branch while the laptop test is queued.

Then take the rest in this order. A row marked **hold** goes red in CI on top of #11 today. Land the fix on that PR's own branch, re-run its tests, then merge. Do not merge it red.

| Order | PR | What | Gate on main + #11 | `run_all.py` |
| --- | --- | --- | --- | --- |
| 1 | #11 | Day 1 garden look | Already green. Waiting on the editor. | Yes. Builds the garden, then `diag_shot`. |
| 2 | #14 | Voice as God | **Hold.** `run_all.py` conflicts. After the resolution below, 2 tests fail. | Yes. Call `install(ue)` after the garden build. |
| 3 | #12 | Chaos physics, water, wind, God hand | **Hold.** `DefaultEngine.ini` and `run_all.py` conflict. After that resolution, 1 failure and 7 errors. | Yes. Call `apply_physics(ue)` after the garden build. |
| 4 | #18 | Win64 demo cook script | Green (28 tests). Cooks whatever is already merged, so wait until the held rows you want in the demo are actually merged. | No. `Scripts/package_demo.ps1`. |
| 5 | #16 | Adam and Eve | **Hold.** `README.md` and `run_all.py` conflict. After that resolution, 3 errors. | Yes. Call `spawn_people(ue=ue)` after the garden build. |
| 6 | #21 | Creation days 2–7 | **Hold.** No git conflict. Import error in `test_creation`. | No. `Scripts/run_creation.py`. |
| 7 | #19 | Four endings | **Hold.** `ElyonUE.uproject` and `run_all.py` conflict. After that resolution, 1 error. | Yes, when Sequencer Scripting is loaded. |
| 8 | #17 | Incarnation walk | **Hold.** No git conflict. 2 test failures. | No. `incarnation_build.place()`. |
| 9 | #15 | Pause-menu AI provider | Green (31 tests). No git conflict. Can move earlier; it does not touch the garden script. | No. |
| 10 | #20 | Ising / Kuramoto civilization tick | Green (106 tests). No git conflict. | No. Python only. |
| 11 | #22 | Seed multiverse | Green (55 tests). No git conflict. | No. Library under `unreal/multiverse/`. |
| 12 | #7 | Living Voices (Electron) | Conflicts with `main` (and therefore with #11). After the resolution below, `npm test` is 43 passing. | No. Electron only. |

Close **#13** without merging. Its tip (`529dc8f`) is an ancestor of #20, and #20's tests already cover the sketch. Merging #13 and then #20 is also safe (one extra commit, then #20's tip). It is not a second feature.

Nothing else in this list is redundant. #7 is behind `main` (the site, the Windows installer, and the desktop shell) and still needs a rebase, but the Living Voices files are not on `main`.

## How the checks were run

For each PR except #7, the unique commits were replayed onto `7b1556e` with `git rebase --onto`. #7 was replayed the same way; its conflicts are the ones it already has with `main`. Unreal tests were `python3 -m unittest discover -s unreal/tests`. #7 was `npm test`.

PRs that apply with no conflict and pass: **#13, #15, #18, #20, #22**.

PRs that apply with no conflict and fail: **#17, #21**.

PRs that stop on a conflict, and still fail after the resolution in this note: **#12, #14, #16, #19**.

#7 stops on a conflict. The resolution below passes `npm test`.

## `run_all.py` when several features land

#11's script must stay the base:

1. `level_build.build(dawn=True, ue=ue)`
2. The feature calls, in merge order: `install(ue)`, then `apply_physics(ue)`, then `spawn_people(ue=ue)`, then `build_endings(ue=ue)` only when `sequencer_ready(ue)`.
3. `diag_shot.diagnose(ue)`
4. Log `Elyon run_all finished`.

Keep `set_keep_python_script_alive(True)`. Voice, physics, and Adam & Eve all place actors the garden build deletes, because those labels are not in the garden plan. Call them after `build`, every time `run_all.py` runs. Each of those PRs conflicts on `run_all.py` again with whoever edited it last. Use the same stack. Do not restore `from level_build import build` in place of the `diag_shot` import.

## Conflicts and how to resolve them

### #14 voice — `unreal/Scripts/run_all.py` only

`unreal/README.md` auto-merges. Insert `from voice_session import install` and call `install(ue)` after `level_build.build` and before `diag_shot.diagnose`.

Then fix the two failing tests before merge. `test_number_key_brings_the_dawn` and `test_phrase_key_and_push_to_talk` expect sun intensity `10.0`. On #11, dawn is `120000` lux. The voice path already calls `let_there_be_light`, so the actor is at 120000 and the assertions are the stale part. `voice_logic.py` still stores `"sun": 10.0` in its world dict. Update that stored number and the two assertions to the lux value. Do not turn the garden sun back down to 10.

`voice_session.py` still imports `_by_label`, `_rot`, `_subsystem`, `_ue`, `_vec`, and `let_there_be_light` from `level_build`. Those names still exist on #11.

### #12 physics — `DefaultEngine.ini` and `run_all.py`

`unreal/README.md` and `ElyonUE.uproject` auto-merge. Water stays a single enabled plugin (PythonScriptPlugin, EditorScriptingUtilities, RemoteControl, PCG, Water).

In `DefaultEngine.ini`, keep #11's console variables, including `r.Streaming.PoolSize=2048` and `r.EyeAdaptation.CachedLightingPreExposure=8`. Append the physics block after them. Do not take the physics branch's pool size of 3072.

```
[/Script/Engine.PhysicsSettings]
DefaultGravityZ=-980
bEnablePCM=True
bEnableStabilization=True
bSubstepping=True
MaxSubstepDeltaTime=0.008333
MaxSubsteps=4
BounceThresholdVelocity=200
DefaultDegreesOfFreedom=Full3D
bDisableCCD=False
```

In `run_all.py`, call `apply_physics(ue)` after `level_build.build` and before `diag_shot.diagnose`.

Then fix the tests before merge. `physics_build.py` reads `garden_logic.MESH`. #11 renamed that dict to `MESH_CANDIDATES`. The old keys were engine Basic Shapes (`/Engine/BasicShapes/Plane`, `Cube`, `Sphere`, `Cone`, `Cylinder`). Point the physics bodies at those engine paths. Do not put cone trees back into the Day 1 plan.

`test_labels_and_placements_stay_out_of_the_river_and_the_plan` asserts `Elyon.GodCamera` is absent from the garden plan. #11's plan includes that cine camera. Physics also registers `Elyon.GodCamera` in `managed_labels()`. Give the physics pawn its own label and drop the assert that the garden plan has no God camera. Leave #11's `Elyon.GodCamera` in place.

Design overlap, not a git conflict: #11 keeps a thin cube river and lake. Physics adds a Water Body and hides the cube when that body succeeds (`test_water_success_hides_the_cube_and_floats_logs_and_fruit`). Keep both. Do not remove #11's lake material.

### #16 Adam and Eve — `unreal/README.md` and `run_all.py`

In the README, keep #11's "Sky, haze, and the 4060 preset" paragraph. Add one sentence that Adam and Eve are placed after the garden actors. Do not restore the old bullets about cone and cube trees.

In `run_all.py`, call `spawn_people(ue=ue)` after `level_build.build` and before `diag_shot.diagnose`.

Then fix `characters_logic.py`, which still does `garden_logic.MESH[person["mesh"]]`. Same Basic Shapes mapping as physics. The three errors are all that missing name (`test_spawn_is_idempotent_and_run_all_keeps_the_garden`, `test_step_and_address_update_the_spawned_actors`, and the garden `test_run_all_keeps_the_editor_open`, which imports the characters hook). The other character tests passed on the resolved tree.

### #19 endings — `ElyonUE.uproject` and `run_all.py`

`unreal/README.md` auto-merges. Keep Water, and add SequencerScripting after it. Both enabled. One plugin list, no duplicate PCG entry.

In `run_all.py`, after the garden build and before `diag_shot.diagnose`:

```
if sequencer_ready(ue):
    build_endings(ue=ue)
```

Then fix `SequencerAssetLib.does_asset_exist` in `test_endings.py`. It still reads `self.exists`. #11's fake asset library uses `map_ready` for `/Game/Maps/Day1_Garden` and no longer has `exists`. `test_build_is_idempotent_and_run_all_uses_it_when_sequencer_scripting_is_loaded` is the only failure (30 other tests passed). Teach the fake the #11 shape, or set the flag `build` actually checks.

### #21 days 2–7 — no git conflict, import is broken

`creation_logic.py` does `from garden_logic import MESH` at import time, so `test_creation` does not load. Stop importing `MESH`. Map `plane`, `cube`, `sphere`, `cone`, and `cylinder` onto `/Engine/BasicShapes/...` inside the creation scripts. Days 2–7 are their own maps. Do not pull those shapes back into the Day 1 scatter.

`run_all.py` does not call this. On the laptop, run `Scripts/run_creation.py`.

### #17 incarnation — no git conflict, two tests fail

`test_walk_places_a_human_form_with_engine_colors` and `test_crucifixion_is_an_absence_and_the_passage_is_another_map` expect `EditorLevelLibrary.loaded == "/Game/Maps/Incarnation_Walk"`. It stays `None`. #11's fake `does_asset_exist` returns true only for `/Game/Maps/Day1_Garden` after `new_level`. A second `place()` therefore calls `new_level` again instead of `load_level`. Broaden the fake so any path passed to `new_level` later exists. The real editor asset library does not have the Day 1 special case, so this is a unit-test gate, and CI still runs it.

`run_all.py` does not call this. On the laptop, run the incarnation place script.

### #7 Living Voices — `README.md`, `electron/main.js`, `package.json`

Same three files conflict with `main` and with #11. The other Living Voices files auto-merge (`index.html`, `js/main.js`, `js/save.js`, `js/sim.js`, `js/ui.js`).

- `package.json`: keep `main`'s test list and `capture:site`, and add `test/living.test.js` at the end of the `npm test` list.
- `README.md`: keep `main`'s tests paragraph. Add the sentence that Living Voices lives in `js/living.js` and `electron/living-host.js`, and name `test/living.test.js` with the other test files.
- `electron/main.js`: keep the guards import (`isGameSender`, `navigationAllowed`, `windowPreferences`) and add `createLivingHost` plus `acceptableWavBase64`. Keep `contain()`. Add `livingRoot`, `living`, `decodeSpeech`, and `denied`. Do not add a second `fromGame` or a second unguarded `get-about`. The voice IPC handlers that auto-merge already use the guarded `fromGame`.

After that resolution, `npm test` passed (43 tests). Rebase the PR branch itself only when you are ready to merge it. This plan does not do that.

## What each PR touches

| PR | Branch tip | Files |
| --- | --- | --- |
| #7 | `cursor/living-voices-66c6` | `README.md`, `package.json`, `css/game.css`, `electron/living-host.js`, `electron/main.js`, `electron/preload.cjs`, `index.html`, `js/converse.js`, `js/living.js`, `js/main.js`, `js/save.js`, `js/sim.js`, `js/slots.js`, `js/ui.js`, `js/wav.js`, `test/living.test.js` |
| #11 | `cursor/garden-look-66c6` `7b1556e` | Garden config, `ElyonUE.uproject` (Water), `unreal/README.md`, `diag_shot.py`, `garden_logic.py`, `level_build.py`, `run_all.py`, `shot_check.py`, garden tests |
| #12 | `cursor/garden-physics-66c6` | `DefaultEngine.ini`, `DefaultInput.ini`, `ElyonUE.uproject`, `unreal/README.md`, `physics_build.py`, `physics_logic.py`, `run_all.py`, `test_physics.py` |
| #13 | `cursor/civilizations-sketch-66c6` | `civ_sim.py`, `docs/civilizations.md`, `docs/physics-ideas.md`, `test_civ.py` |
| #14 | `cursor/voice-as-god-66c6` | `Data/intents.json`, `unreal/README.md`, `run_all.py`, `voice_logic.py`, `voice_session.py`, `test_voice.py` |
| #15 | `cursor/pause-ai-provider-fa57` | `.gitignore`, `unreal/README.md`, `ai_providers.py`, `ai_settings.py`, `pause_settings.py`, `test_ai_settings.py` |
| #16 | `cursor/adam-eve-characters-d52c` | `Data/characters.json`, `unreal/README.md`, `characters_build.py`, `characters_logic.py`, `run_all.py`, `test_characters.py` |
| #17 | `cursor/incarnation-walk-among-them-f5d7` | `Data/incarnation.json`, `unreal/README.md`, `incarnation.py`, `incarnation_build.py`, `docs/incarnation.md`, `test_incarnation.py` |
| #18 | `cursor/ue-windows-demo-package-4a01` | `unreal/README.md`, `package_demo.ps1`, `test_package_demo.py` |
| #19 | `cursor/unreal-four-endings-621d` | `Data/ending_sequences.json`, `Data/endings.json`, `ElyonUE.uproject`, `unreal/README.md`, `endings_build.py`, `endings_logic.py`, `run_all.py`, `test_endings.py` |
| #20 | `cursor/civ-ising-kuramoto-b108` | #13's files plus `Data/civ_core.json`, `civ_rng.py`, `civ_tick.py`, `ising_society.py`, `kuramoto_faith.py`, `test_civ_tick.py`, `test_ising.py`, `test_kuramoto.py` |
| #21 | `cursor/creation-days-2-7-5c17` | `Data/creation_week.json`, `unreal/README.md`, `creation_build.py`, `creation_logic.py`, `run_creation.py`, `test_creation.py` |
| #22 | `cursor/seed-multiverse-25b7` | `Data/major_choices.json`, `Data/physics_constants.json`, `unreal/README.md`, `docs/multiverse.md`, `unreal/multiverse/*.py`, `test_multiverse.py` |

`physics_constants.json` in #22 does not overlap the physics scripts in #12.

## Laptop, one PR at a time

1. Merge #11 only after the overview shot looks right. Leave that branch alone until then.
2. For the next row, if it is **hold**, fix that branch until its tests pass on top of the garden, then merge.
3. When the PR hooks `run_all.py`, run that script in the editor. Otherwise run the entry in the table (`run_creation.py`, incarnation place, `package_demo.ps1`, or the Python tests for pause, civ, and multiverse).
4. #18's cook should be the garden plus voice plus physics, which is why it sits after those two. If #12 or #14 is still held, skip the cook or cook the garden alone. The packaging tests do not cook.
5. #7 is the Electron track. It does not belong in the middle of the Unreal merges.
