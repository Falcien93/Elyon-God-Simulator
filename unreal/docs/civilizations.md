# Civilizations after the sixth day

Design sketch for the layer that begins once humanity is in the world and the garden choice has locked an ending. This is not a new set of endings, and it is not the Day 1 garden. Days stay the eight already shipped in `unreal/Data/days.json`: light, waters, land, grove, lights, creatures, humanity (the sixth day), rest (the seventh). Civilizations play out after that choice.

The garden already tracks `order` and `wonder` (0–100), plus trust, wonder, and will on Adam and Eve. Faith, prosperity, fear, and population are new stats for tribes. They sit beside the garden stats. They do not replace them.

Incarnation, a later mode in which God walks among the people, is specified in (f). Quantum miracles, a later layer of paired outcomes, are specified in (g). Neither is in the Python sketch.

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

The same voice rule covers Incarnation. Leaders and prophets who meet God in human form, and the few dead who speak in the underworld, emit `needs_voice`. The crowd around that body still does not call the model. World-changing speech from the god view waits until that view returns.

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

Incarnation does not vote a new ending and does not reopen silence. How each locked id colors that walk is (f).

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

**After the first settlement, before Mass**

Incarnation waits until that first list exists. The rules are (f). The build itself is five steps, and none of them need a model in the loop:

1. One human pawn among the instanced people. Attitude comes from faith and fear. No death yet.
2. The seizure beat, only on endings that already allow clash.
3. The underworld as one small map.
4. The return, the `incarnate_returned` flag, and the stat changes in (f).
5. Spoken lines for the meeting and for the dead, still `needs_voice` until Qwen is in the install.

**Later layer, after the core civ sim**

Quantum miracles wait until the first list is playing one locked ending. They are not part of that core tick. The rules are (g). Incarnation should already be able to walk, reach the crucifixion fail state, descend, and return, because this layer reads those states. The layer itself is four steps:

1. One paired cast, held as a marker: healing or plague, or a bountiful or barren harvest.
2. The first NPC who sees it collapses it from that NPC's faith versus fear or doubt.
3. Write the result into faith, power, and wrath.
4. Then let wrath and the collapse touch Incarnation: hostility on the walk, the seizure beat, the pause in the underworld, and the bias after the return.

**Later**

- Mass Entity crowds and Mass AI, carrying the attitude band from (f) as a tag.
- StateTree for leaders only, including receive, question, and seize once Incarnation exists. Seize stays off the tree for harmony and order.
- PCG settlements.
- World Partition, garden plus east, if that split wins. The underworld becomes a cell only after that.
- Niagara disasters and Chaos destruction tied to flood and clash. The return's light can be Niagara. The death is not a Chaos event.
- Qwen3 4B through llama.cpp for leaders, prophets, dialogue, and the few dead in the underworld, bundled in the one install. The crowd still does not call it.

## (f) Incarnation

God can leave the sky and walk among the people in a human body. This is one mode, entered after a settlement has shelter. It is not a fifth ending. The garden choice stays locked. The telling is original to Elyon: a walk, a possible turning of the crowd, a death, a descent, and a return. It does not quote scripture. It is not a scene about how a body breaks. The player never crucifies anyone. The people may turn. The return is the point, because that is what changes the civilization.

### Walking in a body

From the god view, the player chooses Incarnation once. The god camera sleeps. Flood, blessing, punishment, and divine force wait. Speech that remakes the world waits with them. What remains is a single human pawn in the settlement: walk, stand near people, and hear leaders and prophets.

Attitude is faith set against hostility, and it exists only while that body is among them. Hostility is not a new score inside the crowd's utility tick. It is derived for the duration of the walk:

- It starts at 0.
- It rises while fear is high and faith is under 40.
- It falls when faith is over 60, or when the player has only walked and been spoken to.
- It is clamped from 0 to 100. Prosperity slows the rise. A people with shelter and stores turn more slowly.

Bands: 0–30 welcome, 31–60 wary, 61–80 hostile, 81–100 seized.

Nearby people wear that band. The many still choose build, trade, or clash. They do not hold a conversation. Leaders, and later a StateTree, may receive, question, or seize. Only those speakers, and prophets, emit `needs_voice`. The crowd still does not call Qwen3 4B.

### When they turn

Seizure is the crucifixion event. It fires only at hostility 81 or higher, and only when that ending already allows a lethal clash. Harmony caps hostility at 60, so the walk can become wary and no further. Order does not seize. There the attitude is refusal: distance and silence, also capped at 60, because clash is already omitted from that people. Wonder can reach seizure, but the low clash weight means fear has to stay high. Exile can reach it. The east already knows how to clash.

The event is one beat. The pawn is gone. The picture does not stay on the death. There is no gore, no crowd taunt, and no player verb for the killing. The living settlement's fear rises by 10 once, because the one who walked with them is gone. Population does not drop for this. It is not a flood and not a clash casualty.

### The underworld

Death loads a playable section under the settlement. It is a passage, not a punishment gallery. A few figures already lost to flood or clash are there. They can speak, one `needs_voice` line each, under the same rule as the living: the local model, and never a crowd call. God-interventions stay unavailable. The living utility tick pauses. The player walks and listens. Leaving is the resurrection. There is no fight that earns it.

### The return

Resurrection puts the same human form back at the center of the settlement. The player may then rise to the god view again. The locked ending id does not change. A flag `incarnate_returned` is set. Hostility goes to 0. Population stays. Prosperity rises a little, because the work resumes. Faith and fear move with the ending:

| Ending | Faith | Fear | What else changes |
| --- | --- | --- | --- |
| harmony | +20 | −15 | Build and trade stay dominant. The return confirms a loyalty the garden already chose. |
| wonder | +16 | −12 | Prophets emit `needs_voice`. God descended, and came back, inside the open orchard. |
| exile | +10 | −8 | Clash is scored down for the rest of the sim. The settlement stays east. The return is God walking back to them, not a recall through the gate. |
| order | +8 | −6 | Clash stays omitted. The closed question stays closed. Faith moves. Wonder is not restored by this flag. |

These numbers are a starting tune, the same way the interventions are.

### How the four endings color the walk

- **harmony — The garden kept.** They stayed because God asked. A body among them reads as loyalty kept, not as a test they can fail by killing. Hostility cannot reach seizure.
- **wonder — The open orchard.** The prose already says God can still descend. This mode is that descent. Welcome is the common path. Seizure is possible if fear has the people. The return gives prophets a voice.
- **exile — East of the garden.** God already walked them east. This is a second walk, outside the gate. They may receive the one who clothed them, or resent the leading. Seizure can happen. The underworld is not the garden. The return does not undo exile and does not reopen silence.
- **order — The closed question.** A human God is the missing question standing in a peace that will not break. The people do not kill what they will not ask. Refusal replaces crucifixion. The return changes stats and leaves the fruit out of reach.

### AI

- The crowd utility tick is unchanged in shape. While the pawn is near, each person copies the tribe band: welcome, wary, hostile, or seized. Later, Mass Entity stores that tag. Mass AI still does not call the model.
- When StateTree exists, leaders gain three states for this mode: receive, question, seize. Seize is absent under harmony and under order.
- Prophets speak when they meet the incarnate, and again on the return under wonder. Dead leaders in the underworld use that same one-line budget.
- Qwen3 4B through llama.cpp stays on leaders, prophets, dialogue, and those few dead. It stays in the one install. It stays off the crowd. Until that later step the sim still emits `{needs_voice: true, model_called: false}`.
- Living Voices stays the other path. It is not this mode.

### Where it sits in the build

Not in the first slice. The stat tick, one settlement, the four impulses, the locked ending, and `needs_voice` come first. Incarnation uses that settlement. It does not need Mass, and it does not need the model binary.

The five steps are listed under build order. Chaos does not simulate the death. Niagara can carry the return's light later. Neither is required for the mode to change the civilization's state.

Quantum miracles, in (g), are the layer after this. They can push a walk toward seizure or away from it. They do not replace the death or the return with a second undecided outcome.

## (g) Quantum miracles

A miracle God casts can be held in superposition: two possible outcomes at once, until an NPC observes it. This is a later layer. It is not a fifth ending, and it is not a rewrite of the four interventions in the core sim. Flood, blessing, punishment, and divine force stay single outcomes there. A quantum miracle is an extra cast, added only after that sim is playing one locked ending.

The telling stays original to Elyon. The pair is a choice the world has not made yet. It is not a joke about the crucifixion, and it is not a quotation of scripture.

### Superposition

God casts one miracle. Until a person sees it, both branches are true and neither has landed:

- A healing, or a plague.
- A bountiful harvest, or a barren one.

Only one superposition is active in a settlement. A second cast waits. The marker stores the pair, the place, and that it is still unobserved. No NPC has faith, power, or wrath changed yet. God, in the sky or in the incarnate body, is not an observer. Casting it does not collapse it.

### The observer effect

The first NPC who sees it collapses it. Leaders and crowd members both count. Whoever is first decides. Later witnesses live in the world that already landed. They do not get a second collapse.

Belief at that moment is faith versus fear or doubt. Doubt here means faith under 40. It is a reading of the faith stat, not a new stored meter.

- If faith is greater than fear, and faith is at least 40, the life-giving branch lands: healing, or a bountiful harvest.
- If fear is greater than or equal to faith, or faith is under 40, fear or doubt decides, and the harsh branch lands: plague, or a barren harvest.

The comparison is numbers. The observer does not call Qwen3 4B to pick the branch. If that observer is a leader or a prophet, they may emit `needs_voice` afterward, to speak about what they saw. A crowd member who collapses it stays silent. The crowd tick still does not call the model.

### Faith, power, and wrath

The collapse writes back into three stats. Faith is the tribe stat the core sim already has. Power and wrath are new, 0–100, and they belong to this layer. Power starts at 50. Wrath starts at 10. They are not prosperity and they are not fear. Prosperity, fear, and population stay on the core tick until a later tune says otherwise.

| Landed state | Faith | Power | Wrath |
| --- | --- | --- | --- |
| Healing, or a bountiful harvest | +10 | +8 | −8, floor 0 |
| Plague, or a barren harvest | −8 | −6 | +12 |

Clamp each result from 0 to 100. These are a starting tune.

Power is capacity for the next cast. It does not choose the branch. A high power makes the landed result larger (a deeper healing, a wider plague, a fuller store, a harder barren year). Wrath is the harsh residue. It does not pick the branch either. It is what a harsh landing leaves in the people, and what a life-giving landing eases.

### Incarnation

On the walk, God may still cast one paired miracle. The human pawn does not observe it. The first other NPC who sees it collapses it, using that NPC's faith versus fear or doubt.

A life-giving landing adds 10 faith and subtracts 15 from hostility, on top of the walk's usual movement. Wrath falls with the table above, so the people are harder to push toward seizure.

A harsh landing subtracts 8 faith, adds 12 wrath, and adds 15 hostility. Hostility still caps at 60 under harmony and under order. Under wonder and exile, that extra hostility can cross 81 and fire the crucifixion fail state. The miracle did not kill God. The people's turn did, and only where clash was already allowed.

### The crucifixion fail state

The crucifixion is not a superposition. "Alive or dead" is not a pair an NPC collapses. Seizure is the committed fail state from (f): hostility at 81 or higher, on an ending that allows clash, one beat, no player verb for the killing.

What this layer adds is a path into that fail state. Wrath from a plague or a barren harvest makes the walk more dangerous. It does not leave the death undecided. Once seizure fires, the miracle that led there has already collapsed. There is no remaining branch in which the crucifixion did not happen.

Harmony still cannot seize. Order still refuses. A harsh collapse in those endings changes faith, power, and wrath, and stops there.

### The underworld

The descent is the passage after that committed death. It is not the harsh branch of a miracle, and it is not still waiting on an observer.

No living NPC is there to collapse anything. The dead do not observe a miracle in the settlement above. The living utility tick is paused, so no new witness walks up to an uncollapsed marker. A superposition that was still open when God died waits. God does not cast a new quantum miracle below. Interventions are already unavailable there, and a cast with no living observer would have nothing to land in.

### The resurrection

The return is committed. It is not a pair of "stays dead" and "rises" that the first witness collapses. The human form is back because (f) already brought them back. The ending id stays locked.

Before anyone looks at a waiting miracle, the return applies its own stat changes from (f), then power +6 and wrath −10. The first living NPC who then sees a miracle that waited through the underworld collapses it with that gentler belief. Faith is higher and fear is lower, so the life-giving branch is the likely landing. That is the feedback: the return changes the observer, and the observer lands the miracle that was held open.

A new cast after the return works the same as any other cast. It does not reopen silence, move exile back through the gate, or restore wonder under order.

### Where it sits in the build

After the core civ sim, as a later layer. The utility tick, the four deterministic interventions, the locked ending, and one settlement come first. This layer does not enter `civ_sim.py` in that slice.

The four steps are listed under build order. They sit after Incarnation in that order because wrath has to have a walk, a fail state, a descent, and a return to touch. Mass, Niagara, and the model binary are still later. A marker and a stat write are enough for the collapse to be real.

## (h) Open questions for John

1. Is "falls" the closed question (wonder falls, the people remain) or exile (the people leave)? The shipped text has no collapse ending.
2. Do civilizations only play out the locked garden ending, or can a long sim drift into another? `resolveEnding` keeps the first one.
3. How many is "the many" for a first playable: dozens of actors, or thousands on Mass?
4. Is Qwen3 4B via llama.cpp the bundled model for leaders, and does Living Voices stay a separate path?
5. Is clash lethal (population loss and Chaos destruction) or ritual (fear and prosperity only)?
6. World Partition: a persistent garden plus an east region, or one open world from day 1?
7. Does divine force reuse the physics radial impulse, or is it only these stats?
8. Confirm the sim must not reopen `flags.silence`. Wonder versus exile is already decided before this layer starts.
9. While God is incarnate, do the four interventions and world-changing speech stay asleep until the god view returns?
10. Order already omits clash. This sketch also omits crucifixion there, and calls the attitude refusal. Should order ever seize?
11. Resurrection under order changes faith and fear and leaves the ending id locked. Should `incarnate_returned` be allowed to bring wonder back, or must the closed question stay closed?
12. Is the underworld one small map with a few of the dead, or a World Partition cell under the settlement?
13. Do power and wrath stay their own stats, or should power stand in for prosperity and wrath for fear?
14. Do the four core interventions stay single outcomes, with quantum miracles as an extra cast only?
15. Is one uncollapsed miracle per settlement the right limit?
