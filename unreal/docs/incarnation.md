# Incarnation: walk among them

God leaves the sky and walks in a settlement as a human being. The people have a disposition toward that body. On some locked endings the disposition can become hostile enough for one crucifixion beat. What follows is an underworld passage, then a resurrection that puts the same human form back among the living. The player may then return to the god view.

This is an original telling for Elyon. It is not a scripture, and it does not quote one. It is not a scene about how a body breaks. The player never performs the death. There is no gore, no crowd taunt, and no player verb for the killing. The return is the point of the mode, because that is what changes the settlement.

The mode is not a fifth ending. Harmony, wonder, exile, and order stay the four ids already shipped in `unreal/Data/endings.json`. Silence is not reopened here. A value of `hands` is not an ending this mode accepts.

The numbers below are a starting tune. They live in `unreal/Data/incarnation.json` and are applied by `unreal/Scripts/incarnation.py`. `unreal/Scripts/incarnation_build.py` only places placeholder engine shapes on two maps of its own. It does not open `/Game/Maps/Day1_Garden`.

## What this scaffold is

A pure-Python state machine, a hostility model, the legal phase transitions, and the data those use. Unit tests drive it with the mocked `unreal` module already in `unreal/tests/test_garden.py`. No model is loaded. No socket is opened. `needs_voice` events set `model_called` to false. The crowd never receives one.

It does not import the Day 1 garden builder, the civilizations sketch, Chaos physics, voice intents, or Living Voices. Those are other features. A later settlement tick can read `faith`, `fear`, `prosperity`, `population`, `clash_eased`, `incarnate_returned`, and `events` from the state this mode returns. This file does not simulate that tick.

## Phases

| Phase | Where the player is | God acts | Living tick |
| --- | --- | --- | --- |
| `sky` | God view, before the choice | Available | Running |
| `walking` | One human form in the settlement | Waiting | Running |
| `crucifixion` | The form is gone. The picture does not stay | Waiting | Paused |
| `underworld` | A passage under the settlement | Waiting | Paused |
| `returned` | The same human form, at the center | Waiting | Running |
| `ascended` | God view again | Available | Running |

```
sky --enter--> walking --beat, if seized--> crucifixion --continue--> underworld --leave--> returned --ascend--> ascended
                  |
                  +--ascend, when they have not turned--> ascended
```

`meet` and `listen` do not change phase. `meet` is only legal while walking. `listen` is only legal in the passage.

Illegal paths raise `IncarnationError` and do not change the caller's state: skipping the passage, ascending during the crucifixion beat, leaving during the walk, entering twice, entering with no shelter, or feeding the mode an ending it does not know.

Actions are `enter`, `beat`, `meet`, `continue`, `listen`, `leave`, and `ascend`. There is no action for killing, striking, or sentencing.

## Entering

`enter` is legal from `sky` only, and only once (`chosen`). The settlement must already have shelter. Stores are not required. On entry:

- Hostility starts at 0, band `welcome`.
- The god camera sleeps.
- Flood, blessing, punishment, divine force, and speech that remakes the world wait (`interventions_available` and `world_speech_available` are false).
- One human pawn is among the living.

## Disposition

Hostility exists for the walk. It starts at 0 and is clamped from 0 to 100, and also to the ending's cap.

Each `beat` while walking:

- It rises while fear is at or above 55 and faith is under 40.
- Otherwise it falls by 8 when faith is over 60, or when this beat was only walking and being spoken to.
- If the rise condition is true, a people who are afraid still turn. Walking gently does not cancel that.
- If neither condition is true, hostility holds.

The rise is an integer:

```
amount = rise * prosperityDivisor / (prosperityDivisor + prosperity)
```

`rise` is 12 and `prosperityDivisor` is 100, using integer division. Prosperity slows the rise. When the settlement has both shelter and stores, that amount is halved again. The rise is at least 1 while the rise condition holds, so a prosperous people turn slowly rather than never.

Bands:

| Hostility | Band | Leaders, when seizure is possible |
| --- | --- | --- |
| 0–30 | welcome | receive |
| 31–60 | wary | question |
| 61–80 | hostile | question |
| 81–100 | seized | seize |

Nearby people wear that band (`crowd_tag`) only during `walking`. They do not hold a conversation. A `meet` with role `crowd` adds no event. A leader or a prophet emits one `{needs_voice: true, model_called: false}` event. Each meeting is one line. The scaffold also keeps a short original line so the moment is not empty before a local model exists.

## How the four endings color the walk

- **harmony — The garden kept.** Attitude `loyalty`. Hostility is capped at 60, so the walk can become wary and no further. Seizure does not fire. Clash stays disallowed. They stayed because God asked. A body among them is not a test they pass by killing.
- **wonder — The open orchard.** Attitude `descent`. The prose of that ending already says God can still descend. Welcome is the common path. Seizure is possible if fear stays high. On the return, prophets emit one `needs_voice` event.
- **exile — East of the garden.** Attitude `east`. The region defaults to `east` and the return does not move it. This is a second walk, outside the gate. Seizure can happen. The return eases clash for whatever later tick reads `clash_eased`. It does not undo exile and it does not reopen silence.
- **order — The closed question.** Attitude `refusal`. Hostility is capped at 60. The people do not kill what they will not ask. Leaders may receive or question. They never seize. Clash stays omitted. The return moves faith and fear and does not restore wonder (`wonder_restored` stays false).

`seizure_fires` is false for harmony and order even if a caller hands it a hostility of 81 or more. The cap and the flag both hold.

## The crucifixion beat

Seizure is the crucifixion event. It fires only when hostility is 81 or higher and that ending already allows a lethal clash (wonder, exile).

It is one beat:

- The pawn among the living is gone.
- The picture does not stay on the death. The level marker for this phase is an absence, not a body.
- Fear rises by 10, once, clamped at 100, because the one who walked with them is gone.
- Population does not change. This is not a flood and not a clash casualty.
- The event records `graphic: false`, `player_acted: false`, and `population_delta: 0`.
- The living tick pauses. God acts stay unavailable.

The only legal next action is `continue`. That action means the beat is over. It is not a verb for the killing.

## The underworld

`continue` opens `/Game/Maps/Incarnation_Underworld`. It is a passage, not a punishment gallery. God acts stay unavailable. The living tick stays paused. The player walks and listens.

A few figures already lost to flood or clash are there (Mira, Oren, and Sela in the default data). Each may speak once: one `needs_voice` line, `model_called` false, never a crowd call. Hearing them is not a price. `leave` is legal with none of them heard. There is no fight that earns the way out.

Leaving is the resurrection.

## The return

`leave` sets phase `returned`:

- The same human form is back at the center of the settlement.
- `incarnate_returned` is set and stays set after the player ascends.
- Hostility is 0. The band is welcome.
- Population is unchanged. The region is unchanged. The ending id is unchanged.
- Prosperity rises by 6, because the work resumes, clamped at 100.
- Faith and fear move with the ending, clamped from 0 to 100:

| Ending | Faith | Fear | What else |
| --- | --- | --- | --- |
| harmony | +20 | −15 | Build and trade were already the life of this people. The return confirms it. |
| wonder | +16 | −12 | Prophets emit `needs_voice`. |
| exile | +10 | −8 | `clash_eased` is set. The settlement stays east. |
| order | +8 | −6 | Clash stays omitted. Wonder is not restored. |

`ascend` from `returned` wakes the god camera and turns interventions and world-changing speech back on. The flag stays.

`ascend` from `walking` is the other way home, used when the people do not turn. It sets `departed_in_peace`, does not set `incarnate_returned`, and does not apply the return table. Hostility is cleared because the body is no longer among them. `last_hostility` keeps the score from the last beat.

## Maps

Placeholder shapes from `/Engine/BasicShapes/`. No Marketplace assets. Sun `light_color` is an `unreal.Color` (0–255). Fog inscattering is an `unreal.LinearColor`.

| Phase | Map | What is placed |
| --- | --- | --- |
| walking | `/Game/Maps/Incarnation_Walk` | Ground, sun, fog, player start, human-form sphere |
| crucifixion | `/Game/Maps/Incarnation_Walk` | The same light rig, dimmed, plus an absence marker. The sphere is removed |
| underworld | `/Game/Maps/Incarnation_Underworld` | A smaller passage, a dim light, one listener marker per lost figure |
| returned | `/Game/Maps/Incarnation_Walk` | The human-form sphere again, in a brighter light |
| sky, ascended | none | The open level is left alone |

Placing a phase again updates those actors instead of stacking copies. Labels use the prefix `Elyon.Incarnation.` so a stray garden actor is not destroyed.

Running `Scripts/incarnation_build.py` from the editor keeps the editor open and places a welcome walk on the wonder ending. It is not wired into `Scripts/run_all.py`.

## Tests

From the repo root:

```
python3 -m unittest discover -s unreal/tests -v
```

`unreal/tests/test_incarnation.py` covers the disposition thresholds, the ending caps, the full exile path through the passage and the return, the peace path, the refusal path, voice events, and the map builder against `FakeUnreal`.

## What this mode does not do

- It does not quote scripture or stage a graphic death.
- It does not add a fifth ending or reopen the hands choice.
- It does not call Qwen, xAI, or any other model. It does not spend money or open a network connection.
- It does not simulate Mass Entity, StateTree, Niagara, Chaos, or a non-Euclidean interior. Those can dress this state later. The death is not a Chaos event.
- It does not change the Day 1 garden, voice intents, physics, civilizations, or Living Voices.
