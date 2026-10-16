# Civilizations after the sixth day

Design sketch for the layer that begins once humanity is in the world and the garden choice has locked an ending. This is not a new set of endings, and it is not the Day 1 garden. Days stay the eight already shipped in `unreal/Data/days.json`: light, waters, land, grove, lights, creatures, humanity (the sixth day), rest (the seventh). Civilizations play out after that choice.

The garden already tracks `order` and `wonder` (0–100), plus trust, wonder, and will on Adam and Eve. Faith, prosperity, fear, and population are new stats for tribes. They sit beside the garden stats. They do not replace them.

A pure-Python sketch of the rules lives in `unreal/Scripts/civ_sim.py`. It does not import Unreal and it does not call a model. Tests in `unreal/tests/test_civ.py` run with the existing `python3 -m unittest discover -s unreal/tests -v` step.

## (a) Tribes on their own

A tribe forms when people share a place, a locked ending, and a first shelter. Each tick the many choose one of three acts:

- **Build.** Raise shelter, stores, and walls. Prosperity ticks up. The first tick of a tribe with no shelter always builds.
- **Trade.** Move goods between settlements that already have shelter. Prosperity and a little faith rise.
- **Clash.** Raid or fight. Population and prosperity fall, fear rises. Some endings forbid it.

### Utility for the crowd, a short plan for the settlement

The many do not think in paragraphs. Each tick scores build, trade, and clash from faith, prosperity, fear, population, and the locked ending, then takes the highest score. That is the utility AI.

A settlement also keeps a short goal list, in order: shelter, then trade, then clash. Shelter is mandatory until it exists. Clash is absent from the list when the ending forbids it. This is the lightweight GOAP idea: a fixed goal order, not a search over a large action graph. The prototype uses the goal list to force the first shelter and to drop clash under order. The utility scores pick among the acts that remain.

Later, crowds of people live as Mass Entity (an ECS). Their state stays the same scores. Leaders, and only leaders, can grow a StateTree on top of that: shelter, trade, speak, or call the people to clash. Mass AI is the Unreal home for the crowd. The prototype is a few dicts and a tick.

### Who gets a voice

The bundled local model is **Qwen3 4B, run through llama.cpp**, inside the one install package. It is not a paid API and it is not a second download. The binary is not in this repo.

Only leaders, prophets, and dialogue lines call it. A crowd tick never does. When a leader should speak, or a prophet under wonder, the sim emits an event `{needs_voice: true, model_called: false}` and stops. Nothing in `civ_sim.py` loads a model, opens a socket, or shells out.

Living Voices (whisper, Ollama, Piper, off by default, a different PR) is a separate path for spoken sky replies in the 2D and desktop game. This sketch does not merge the two. Whether Qwen3 4B replaces that path or sits beside it is an open question.

## (b) God interventions are stat changes

Flood, blessing, punishment, and divine force change faith, prosperity, fear, and population. Visuals come later. The numbers below are the prototype. They are easy to retune.

| Act | Faith | Prosperity | Fear | Population |
| --- | --- | --- | --- | --- |
| Flood | +6 if faith is at least 40, otherwise −6 | −18 | +22 | −8, floor 1 |
| Blessing | +12 | +16 | −10 | +2 |
| Punishment | +6 if faith is at least 55, otherwise −8 | −12 | +18 | −1, floor 1 |
| Divine force | +8 if faith is at least 50, otherwise −8 | −4 | +14 | unchanged |

Flood can deepen faith or crack it. A people who already trust read the water as judgment they can bear. A people who do not, read it as abandonment.

Punishment works the same way. High faith takes it as justice. Low faith takes it as harm.

Divine force is a local shock. High faith moves toward awe. Low faith moves toward terror. Fear rises either way.

The Day 1 physics work uses the words "divine force" for a radial impulse on rigid bodies. Here the same words mean a change to tribe stats. They may become one verb. They are not the same system yet.

## (c) The four endings, under their real names

The shorthand thrives / falls / transcends / starts over is a design nickname. The shipped ids and titles are the names the game already uses, in `unreal/Data/endings.json` and `js/content.js`. Do not rename them.

`js/sim.js` `resolveEnding` locks the first ending and ignores a later one. `ending:hands` becomes **wonder** when `flags.silence` is set, and **exile** otherwise. The prototype copies that rule and then refuses to vote a second ending. Civilizations play the locked id. They do not reopen silence.

| Shorthand | Shipped id | Title | What the prose already says |
| --- | --- | --- | --- |
| Thrives | `harmony` | The garden kept | They left the fruit because God asked and stayed. Order deepened. Wonder narrowed into loyalty. The work did not unwind. |
| Starts over | `exile` | East of the garden | They ate. Shame and skill. God clothed them and walked them east. Love went past the gate. Not a wipe, and not monsters. |
| Transcends | `wonder` | The open orchard | No law had been set, so the bite did not exile them. Seeing changed. They are uncondemned. God can still descend. |
| Falls | `order` | The closed question | The fruit is out of reach. Nothing can fall. Evenings are peaceful. Wonder is the thing that is missing. |

**Falls does not match a collapse ending.** Nothing shipped is the fall of a people. The closest reading is order: wonder falls inside a peace that cannot break. Exile is a departure and, in the prose, a beginning east of the gate. This sketch maps "falls" to order and flags the mismatch for John. It does not invent a fifth ending.

Once the id is locked, the sim biases the three acts:

- **harmony — The garden kept.** Build and trade dominate. Clash is scored so far down that the prototype never selects it.
- **wonder — The open orchard.** Build and trade, little clash, prophets marked `needs_voice` once faith is high. No prohibition to preach against.
- **exile — East of the garden.** The settlement is founded in the east, outside the garden. Fear starts with room to rise. Clash is available. Population and prosperity can still grow. That is the skill the ending already names.
- **order — The closed question.** Build is strong. Clash is omitted from the goal list and scored out of reach. Prophets stay quiet. Prosperity can rise. Questions do not.

Exile's garden flag `clothed` and the move of Adam and Eve east (homes near 38.2, 22.4 and 37.4, 23.1 in the 2D world) are why the first settlement outside the garden is an east region, not a second garden.

## (d) Unreal features, named for later

None of these are in the prototype.

- **Mass AI on Mass Entity.** Thousands of people as entities. The utility tick is the data model. StateTree is for leaders, prophets, and a handful of named figures, not for every body.
- **PCG for settlements.** The PCG plugin is already enabled on the Day 1 project. The garden scatter is still Python. Settlements should be PCG graphs: lots, paths, and a few unique buildings, seeded per tribe. First playable can be one instanced village.
- **World Partition.** The persistent garden is one cell. East of the gate, where exile walks, can be another. Loading the whole of that as one open world from day 1 is the other option.
- **Niagara for disasters.** Flood, fire, and a blessing's light are Niagara systems driven by the same stat impulses. The stats change even if the effect is missing.
- **Chaos for destruction.** Clash and flood break buildings the physics layer already knows how to simulate as rigid bodies. Destruction is a consequence of the stat change, not a separate rule.

## (e) Build order

**First**

- This stat model and the utility tick, with the goal list shelter then trade then clash.
- One settlement of instanced people. Not Mass.
- Interventions as the four stat impulses above.
- The ending id locked from the garden choice, including hands plus silence.
- Leader and prophet lines as `needs_voice` events. No model in the loop.

**Later**

- Mass Entity crowds and Mass AI.
- StateTree for leaders only.
- PCG settlements.
- World Partition, garden plus east, if that split wins.
- Niagara disasters and Chaos destruction tied to flood and clash.
- Qwen3 4B through llama.cpp for leaders, prophets, and dialogue, bundled in the one install. The crowd still does not call it.

## (f) Open questions for John

1. Is "falls" the closed question (wonder falls, the people remain) or exile (the people leave)? The shipped text has no collapse ending.
2. Do civilizations only play out the locked garden ending, or can a long sim drift into another? `resolveEnding` keeps the first one.
3. How many is "the many" for a first playable: dozens of actors, or thousands on Mass?
4. Is Qwen3 4B via llama.cpp the bundled model for leaders, and does Living Voices stay a separate path?
5. Is clash lethal (population loss and Chaos destruction) or ritual (fear and prosperity only)?
6. World Partition: a persistent garden plus an east region, or one open world from day 1?
7. Does divine force reuse the physics radial impulse, or is it only these stats?
8. Confirm the sim must not reopen `flags.silence`. Wonder versus exile is already decided before this layer starts.
