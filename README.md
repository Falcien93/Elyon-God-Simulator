# Elyon

Elyon: First Light is a Unity HDRP garden. Adam and Eve are already awake. You stay above them or walk among them, and you speak. They have bodies, they answer as those people through the xAI Responses API, and they live a day: wake, eat, drink, work, rest. They follow the shore. They do not walk through the lake. Only you can step on the water.

Unreal Engine 5 could not be installed or run on the machine that built this (no Epic account, no GPU device). The game is Unity 6000.0.64f1 with the High Definition Render Pipeline. Adam and Eve are skinned bodies with a face, ears, limbs, skin, and weight, Adam heavier than Eve. The valley is terrain around an HDRP water surface, with a shore, morning fog, and a warm sun.

This is an original telling, not a scripture. Linen, no sexual content. "A child" on a body card is a burden, not a scene.

## Play First Light

Open `ElyonFirstLight` in Unity 6000.0.64f1 or newer with HDRP. Use **Elyon → Open First Light**, then press Play. The outdoors scene builds the garden when it starts.

- **M**, or the Sky / Walk button, switches between the sky and walking among them.
- Drag to look. **WASD** or the arrows move. In the sky that pans your presence. On the ground it walks, including across the lake.
- Click Adam or Eve, type, and press Enter or **Speak**. **C** or **Come here** calls the chosen person along the shore.
- Hunger, thirst, and fatigue change through the day. A tired person moves slowly, and the card says so.

Paste an xAI key into the panel and press **Keep the key here**. It is written only to `elyon-xai-key.txt` in the app's persistent data folder (`Application.persistentDataPath`). A file named `xai-key.local.txt` next to the Unity project is also read and is gitignored. The garden record never contains the key. With no key, the day still runs and the panel explains that a key is needed. The chosen person's card says a key is needed before they can answer.

When a key is present, that person answers as themselves, in that age, and they know the pact, the raid, the law, the stores, who was born or lost, their parents, and the memory the line carries. Their reply can set one act the year already understands. **Work** puts them on the labor of that age for the rest of the year. **Stay** keeps that person from being the one who leaves. **Leave** moves that person alone to the other hearth, so meals, births, and labor change with who is there. **Peace** keeps the commandment in that hold, so the fields work harder, fear eases, and the hold does not raid. **Raid** marks that hold to carry off grain, wood, and a spare tool when the year ends; the other hold may fail to build, and someone may leave. A reply may also ask for **rain**, a **drought**, or a **herd**, and that is the one act for the year. With no key, the years and the short lines still run. The key is never written into the repo or the garden record.

Each year is a season. Spring, summer, autumn, and winter follow the year, and the panel names which one is open. Autumn grows the fields. Winter slows gathering, hunting, and the fields, eats a little more, and no child is born unless a house was blessed. A thin hold looks hungrier in winter, so it may raid. Summer and autumn grow a herd the hold is keeping, if the stores can feed it. Winter takes a head when the grain cannot.

From the camps, Elyon may keep a herd on a hold. The hunt then brings meat from those animals. A raid can carry off a head and some fish. From the fields, Elyon may send rain, a drought, or a flood. Rain fills water and grain and puts fish in the nets. Drought dries the stores, kills the fish, thins the herd, slows the outdoor work, and blocks a birth unless a house was blessed. A flood carries off grain and wood, scatters a head of the herd, and does the same to a birth. The sky clears when the year turns. Once it is clear, a hold with water and fields, or a name already on its fish, puts a few back in the nets. Winter still thins an unnamed catch. A named fishery keeps one through the cold and is back in the stores, so a drought does not erase it from the rest of history. Fish and herds stay in the garden record. The key does not.

Speech uses `POST https://api.x.ai/v1/responses` with model `grok-4.7`. Each person is instructed to believe they are that person, including the children and the people who later keep house with them. They do not say they are an assistant or a language model. A new line can start before the last one finishes, and they can talk while they walk.

## One people, ten ages

The valley does not offer a menu of ages. Adam and Eve are already awake at the fire, in the first family. The same bodies, needs, kin, speech, work, food, shelter, tools, belief, and settlements carry them forward. A garden day is a year. At the end of the day the household eats from its stores, children age, a birth or a newcomer can join a house, and at most one age can begin. When an age does begin, someone takes up its work before that year is written down, so the stores already show the learning, the drive, or the power that age lives by.

Siblings do not keep house together. An adult with no living partner is joined by a newcomer. Each living hold bears at most one child a year, and a blessing names which house bears. A dark year, from a withheld harvest or darkened lamps, bears no child unless a house was blessed, and someone unblessed may leave for another hearth. A birth is a line in the chronicle ("someone is born into the house of A and B in that age"), not a scene. "A child in their care" on a body card is the burden of an infant. A young person is a smaller body in the world. Until age 8 they follow a parent. After that they take up the work of the age: fields, the engine, the lamps, or the press. A hoe, an axe, or a hammer dulls with work. The card shows its edge. The smith mends the dullest tool in the hold. Once a temple stands and faith is at least 28, a yearly rite spends one meal and eases grief. When an age begins, each living person remembers how that age is lived, and that memory is kept in the garden record so they can still say it after the game is opened again.

The people are one line from Adam and Eve. A child is named and keeps both parents, and the card walks that line back to the garden even after those parents have died. A newcomer comes into a house of that line. The line carries a short memory of the garden, the pact, the raid, and the age each person was born into. A descendant in a later age can say who their people were. A death, the planting of a hold, and a dark year update that memory. When a key is present, a reply knows the speaker's parents and that memory. With no key, the line still exists and the chosen card still says a key is needed. The key is never written into the repo or the garden record.

Elyon chooses one living person and rests attention there. That person knows God is there. For that season their fear eases and the hold's faith stirs; a withheld person grows more afraid instead. Blessing that person marks their house: it may bear, and they will not be the one to leave. Withholding that person uses the same leaving rule, so they may go to the other hearth. When a key is present they answer as themselves, speaking to Elyon, and they know their parents, the age, the pact, the raid, and the chronicle. One reply sets one act. With no key, a short line still runs and the card says a key is needed. The key is never written into the repo, the garden record, or the scene. One choice lasts: keep the people in the valley, or send them out. The person Elyon is resting on can answer, and that answer becomes the next season, or asks for rain or a drought. A reply that asks for nothing leaves the sky alone. A withheld person still cannot change the season or the sky. A withheld answer fails, and so does a season the land cannot bear, and the chronicle says so. A child born after the valley choice carries that choice. The line and the chronicle remember it, and later ages say it. Each save also writes `elyon-scene.json` from the simulation: the people, who is in the valley, the holds, the weather, the herd, and the lamps, so a later render can match the year.

Elyon can give a name to an unnamed person, and, once they are in the valley, to an unnamed herd and to unnamed fish. A blank name takes the next unused name. A typed name is kept if it is not already carried. Later ages still say that name: in the work, in the stores, on the card, and in a reply. The chronicle keeps the garden, each new age, births, deaths, pacts, raids, the weather, and those names. It is saved with the world. The chosen card shows the garden, the ages, and the latest of that record. With no key, naming and the chronicle still work, and the card still says a key is needed. The key is never written into the repo or the garden record.

A hold founders when the food and the faith are gone, or when grief is heavy and the stores are thin. The people go to another hearth. The last hearth does not empty. A blessing can send a house back to an empty hold. The far hold is planted from the city, the north hold from the mills once the road is open, and the west quarter only after the present is blessed. A failed hold's mill, engine, and lamps no longer count toward the next age. The people carry the food with them, and blessing a house back into the ruin makes those works count again. Keeping the commons can lift a hold over the meal a birth needs, or drop the giver under it. Once two holds stand, Elyon may bless a pact or withhold it. Under a pact they exchange grain, wood, and a spare tool, and their people stay. A withheld pact sends nothing that year, and someone may leave the poorer hearth. The wood that arrives is what the next year can build. A hungry or grieving hold with no pact and no kept law can raid another and carry off grain, wood, and a tool. The raided hold may fail to build, and someone may leave. A kept law or a blessed pact makes that hold keep the peace instead. Elyon can stop a raid: the stores stay, and the people stay. Speech names the pact or the raid in the voice of the age.

Speech and work follow the age. A person at the engine does not talk like a gatherer at the first fire. In the industrial years, gatherers haul wood into drive. Dark lamps slow the fields and make the wire-workers afraid. The body card and the voice both name that day's work. Setting or banking the engine, and kindling or darkening the lamps, changes that work the same day.

What changes:

- **First family.** Gather fruit and wood at the fire. You may bless, heal, set fruit, calm a fear, turn the years, and name an unnamed person.
- **Camps.** The household moves to the eastern meadow, hunts, and sleeps in lean-tos. You may send game, keep a herd, name that herd, and raise a shelter from their wood.
- **Farming.** Fields, houses, grain, and hoes. You may send rain, send a drought, send a flood, bless a field, and name the fish. Rain puts fish in the nets. Drought and flood can take the herd, the fish, and a birth. After the sky clears, the nets refill while the water holds.
- **Metal and towns.** Ore, a smithy, and hammers. The camp is a town on the ridge. You may gift ore and mend a body at the smithy.
- **Cities and empires.** A hall, a temple, and the far hold across the valley. You may proclaim a law, grant a harvest, or withhold one. A kept commandment puts people on the fields instead of the watch, eases fear, and opens the road for less wood. If faith fails, the commandment breaks and fear returns. Withholding the harvest darkens the year: no child is born there unless a house was blessed, and someone may leave. You may bless a pact, withhold it, or stop a raid.
- **Roads and letters.** Someone teaches. A road can join the holds, and grain can move along it. You may open the road and kindle a lesson.
- **Mills.** A mill multiplies the harvest. You may turn it or let it rest. Once the road is open, a north hold can be planted.
- **Industry and engines.** An engine house burns wood into drive and speeds the fields. Gatherers haul wood to it. You may set the engine or bank it. A banked engine makes no drive, and the other holds cannot copy it while it is cold.
- **Electricity and cities of light.** Drive becomes power, and lamps are strung over the city. Lit lamps ease fatigue and fear. You may kindle the lamps or darken them. Darkening them costs faith and raises fear.
- **The present.** A press is kept in the house of letters. You may bless the present, which lets the west quarter be planted, or keep a commons that moves a tenth of the richer store to the poorer hold. The years still turn after that. Once the road is open, the other holds raise their own mill, engine, and lamps from their own wood, and someone there keeps them. A failed hold stays empty until you bless a house back into it.

An age begins only when its facts are true: enough years, people, meals, wood, shelter, tools, faith, learning, drive, or power. The right-hand panel says what is still missing. **The years turn** resolves one year of labor, kinship, and building, so later ages can be reached without watching every day. Divine acts that lack the wood, the field, the smithy, the hall, the mill, the engine, or the power say so and change nothing.

The record is `elyon-first-light.json` in the persistent data folder, version 6. It keeps the people, their parents, the age they were born into, the names Elyon has given, the line's memory, who is still in the valley, the chronicle, and the settlements. Year lines stay apart from the garden, the ages, and the landmarks, so a long history does not drop them. It does not keep the key. Older tiny records are ignored.

The ages can be proven without opening the editor:

```bash
dotnet run --project ElyonFirstLight/Headless/Elyon.Headless.csproj
```

That run starts with Adam and Eve and turns the years through the present: a birth, a name, a pact, a raid Elyon stops, rain and a drought, a herd, and a death. It fails if an age never opens, the line back to Adam or Eve breaks, the chronicle drops the garden, or the key is written into the save.

This machine has no Unity editor license and no GPU, so the valley was not rendered here. Open the project in a licensed Unity 6000 editor and press Play to see it.

Ground, sand, bark, and rock photographs are CC0 maps from Poly Haven. See `ElyonFirstLight/Assets/Elyon/THIRD-PARTY.txt`.

## The page

The page still has address chat and voice. It is the installable canvas beside ElyonFirstLight, not a replacement for that Unity project.

A single-player mythic simulator you can install. You play as Elyon and shape the first garden: light, waters, land, the two trees, the lights of the sky, the creatures, and Adam and Eve. Then you walk among them, name what lives, speak or keep silent, and see which ending the garden keeps.

Adam and Eve can also be addressed freely. Their replies follow what you say and the living field (age, coherence, cycle, seals). Text chat always works. Voice input and spoken replies use the Web Speech API when the window has it, and stay in the log when it does not.

This is an original telling, not a scripture. The earlier single-page Unity Thread sketch (population, ten Divine Fiat actions, and the seal victory screen) remains in the history of `main`. The page keeps that field’s ages, seals, coherence, and achievements beside the creation campaign.

## Play

Requirements: Node.js 20 or newer.

```bash
npm install
npm start
```

`npm start` opens the desktop window. The garden is drawn on a canvas. Menus, dialogue, the address log, and the divine log sit over it.

You can also serve the folder and open it in a browser:

```bash
python3 -m http.server 8080
```

Then visit `http://localhost:8080`. Opening `index.html` as a file blocks ES modules on some systems. The desktop app does not have that limit.

### Install a build

```bash
npm run dist
```

On Linux this writes:

- `dist/linux-unpacked/elyon` — run that file directly
- `dist/Elyon-1.0.0.AppImage` — one file you can mark executable and launch

The desktop window opens on a short splash, then the title screen. **About** (also under the Elyon menu) shows the name, version, description, `com.elyon.garden`, the MIT license, and that the build is not code-signed. The version comes from `package.json`.

Icons are original: `assets/icon.png`, `assets/icon.ico`, `assets/icon.icns`, and the Linux sizes under `assets/icons/`.

Windows NSIS and macOS DMG targets are declared in `package.json` with signing turned off (`forceCodeSigning: false`, `win.signAndEditExecutable: false`, `mac.identity: null`, notarization off). No certificates are required. The Windows executable and the Setup program use `assets/icon.ico`. The installed app does not open developer tools. Build locally on the matching operating system:

```bash
npm run dist:win
npm run dist:mac
```

Continuous integration on Ubuntu builds the unpacked Linux app (`npm run dist:dir`). A Windows job runs `npm ci`, `npm test`, and `electron-builder --win nsis` (unsigned, and it does not publish a GitHub Release) on pull requests, on pushes to `main`, and when someone starts the workflow by hand. The Setup executable is the Actions artifact `elyon-windows-installer`, kept for 14 days.

## How to play

1. **Begin** (or **Continue** if a record already exists).
2. **Open your eyes**, then follow the gold action at the bottom of the screen through the days of making.
3. After dry land appears, press **M** to walk the garden (Walk Among). **M** again returns to Sky View. **WASD** or the arrow keys move you. Click open ground to walk there.
4. Press **E** beside Adam or Eve to speak the story. Sky view can also address them by clicking them.
5. Once Adam is formed, **Address** opens text chat with Adam or Eve. **Speak** reads the last reply aloud. **Voice** listens when speech recognition exists. In the desktop window it often does not: type instead. A missing spoken voice does not drop the reply.
6. After the grove is planted, number keys **1–8** select brushes (water, meadow, bloom, tree, bless, beast, fish, bird). They spend Breath.
7. **Esc** pauses. **H** opens help. **F** toggles fullscreen. The scroll wheel zooms.

The campaign has four endings: harmony, exile, wonder, and order. After an ending you may keep walking the garden.

The Unity Thread reading (shown in Address) tracks age, coherence, cycle, population, faith, beings, and seven seals. Seals open as the days of making are finished. Ages move Primordial → Awakened → Christos → Unity as coherence and seals rise. Reaching an ending sets Unity and absolute coherence. Population keeps growing slowly after the lights are set, and the hundred-beings achievement is still there.

## Achievements

- First Seed — Adam and Eve are both in the garden
- Awakened Age, Christos Age, Unity Age
- Three Seals Open, All Seals Unsealed
- Coherence 50%, Absolute Coherence
- 100 Beings
- Spoken with the First Beings (five or more address lines)
- Walked Among Them (kept after you ascend again)

## Saves

The game keeps three gardens. Each slot holds one versioned record (garden, address log, mood and faith, Unity Thread, achievements). The library envelope is format 1:

- In the desktop app: Electron `userData` / `elyon-saves.json`
- In a browser: `localStorage` key `elyon-saves-v1`

An older single record is migrated into the first empty slot and is not copied again:

- Desktop: `userData` / `elyon-save.json`
- Browser: `localStorage` key `elyon-save-v1`

If a desktop library and a browser library both exist, the newer stamp wins and the other library's unseen slots are filled in. Pause **Export the record** writes the active garden as `elyon-save.json`. **Import a record** replaces only the active slot. A new creation replaces one slot. The other two stay.

## Settings

Settings are separate from the gardens and are remembered on this computer:

- Desktop: `userData` / `elyon-settings.json`
- Browser: `localStorage` key `elyon-settings-v1`

Master volume scales music and effects. Fullscreen, text speed (slow, normal, fast), and voice on/off are stored with them. Per-garden music and effects levels stay inside the slot.

## Voice

Voice input needs a runtime that exposes `SpeechRecognition` or `webkitSpeechRecognition` (Chromium browsers such as Chrome or Edge usually do). Electron on this build often has no speech-recognition service. The Address panel then tells you to type. Spoken replies need `speechSynthesis`. If that call is missing or throws, the reply remains in the address log.

## Tests

```bash
npm test
```

Campaign rules (ritual order, dialogue, the four endings, movement, and save repair) live in `js/sim.js` and `js/save.js`. Address replies, achievements, and voice fallback live in `js/converse.js` and `js/voice.js`. Slots, migration, and settings live in `js/slots.js`. Version text lives in `js/release.js` and must match `package.json`. They are covered by `test/game.test.js`, `test/campaign.test.js`, `test/saves.test.js`, and `test/release.test.js`.

## Fonts

Cormorant Garamond and Cinzel are included as WOFF2 files under `assets/fonts/` and are licensed under the SIL Open Font License. See `assets/fonts/OFL.txt`.
