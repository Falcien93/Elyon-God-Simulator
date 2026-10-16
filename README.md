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

From the camps, Elyon may keep a herd on a hold. The hunt then brings meat from those animals. A raid can carry off a head and some fish. From the fields, Elyon may send rain, a drought, or a flood. Rain fills water and grain and puts fish in the nets. Drought dries the stores, kills the fish, thins the herd, slows the outdoor work, and blocks a birth unless a house was blessed. A flood carries off grain and wood, scatters a head of the herd, and does the same to a birth. The sky clears when the year turns. Fish and herds stay in the garden record. The key does not.

Speech uses `POST https://api.x.ai/v1/responses` with model `grok-4.7`. Each person is instructed to believe they are that person, including the children and the people who later keep house with them. They do not say they are an assistant or a language model. A new line can start before the last one finishes, and they can talk while they walk.

## One people, ten ages

The valley does not offer a menu of ages. Adam and Eve are already awake at the fire, in the first family. The same bodies, needs, kin, speech, work, food, shelter, tools, belief, and settlements carry them forward. A garden day is a year. At the end of the day the household eats from its stores, children age, a birth or a newcomer can join a house, and at most one age can begin.

Siblings do not keep house together. An adult with no living partner is joined by a newcomer. Each living hold bears at most one child a year, and a blessing names which house bears. A dark year, from a withheld harvest or darkened lamps, bears no child unless a house was blessed, and someone unblessed may leave for another hearth. A birth is a line in the chronicle ("someone is born into the house of A and B in that age"), not a scene. "A child in their care" on a body card is the burden of an infant. A young person is a smaller body in the world. Until age 8 they follow a parent. After that they take up the work of the age: fields, the engine, the lamps, or the press. A hoe, an axe, or a hammer dulls with work. The card shows its edge. The smith mends the dullest tool in the hold. Once a temple stands and faith is at least 28, a yearly rite spends one meal and eases grief. When an age begins, each living person remembers how that age is lived, and that memory is kept in the garden record so they can still say it after the game is opened again.

The people are one line from Adam and Eve. A child is named and keeps both parents, and the card walks that line back to the garden even after those parents have died. A newcomer comes into a house of that line. The line carries a short memory of the garden, the pact, the raid, and the age each person was born into. A descendant in a later age can say who their people were. A death, the planting of a hold, and a dark year update that memory. When a key is present, a reply knows the speaker's parents and that memory. With no key, the line still exists and the chosen card still says a key is needed. The key is never written into the repo or the garden record.

A hold founders when the food and the faith are gone, or when grief is heavy and the stores are thin. The people go to another hearth. The last hearth does not empty. A blessing can send a house back to an empty hold. The far hold is planted from the city, the north hold from the mills once the road is open, and the west quarter only after the present is blessed. A failed hold's mill, engine, and lamps no longer count toward the next age. The people carry the food with them, and blessing a house back into the ruin makes those works count again. Keeping the commons can lift a hold over the meal a birth needs, or drop the giver under it. Once two holds stand, Elyon may bless a pact or withhold it. Under a pact they exchange grain, wood, and a spare tool, and their people stay. A withheld pact sends nothing that year, and someone may leave the poorer hearth. The wood that arrives is what the next year can build. A hungry or grieving hold with no pact and no kept law can raid another and carry off grain, wood, and a tool. The raided hold may fail to build, and someone may leave. A kept law or a blessed pact makes that hold keep the peace instead. Elyon can stop a raid: the stores stay, and the people stay. Speech names the pact or the raid in the voice of the age.

Speech and work follow the age. A person at the engine does not talk like a gatherer at the first fire. In the industrial years, gatherers haul wood into drive. Dark lamps slow the fields and make the wire-workers afraid. The body card and the voice both name that day's work. Setting or banking the engine, and kindling or darkening the lamps, changes that work the same day.

What changes:

- **First family.** Gather fruit and wood at the fire. You may bless, heal, set fruit, calm a fear, and turn the years.
- **Camps.** The household moves to the eastern meadow, hunts, and sleeps in lean-tos. You may send game, keep a herd, and raise a shelter from their wood.
- **Farming.** Fields, houses, grain, and hoes. You may send rain, send a drought, send a flood, and bless a field. Rain puts fish in the nets. Drought and flood can take the herd, the fish, and a birth.
- **Metal and towns.** Ore, a smithy, and hammers. The camp is a town on the ridge. You may gift ore and mend a body at the smithy.
- **Cities and empires.** A hall, a temple, and the far hold across the valley. You may proclaim a law, grant a harvest, or withhold one. A kept commandment puts people on the fields instead of the watch, eases fear, and opens the road for less wood. If faith fails, the commandment breaks and fear returns. Withholding the harvest darkens the year: no child is born there unless a house was blessed, and someone may leave. You may bless a pact, withhold it, or stop a raid.
- **Roads and letters.** Someone teaches. A road can join the holds, and grain can move along it. You may open the road and kindle a lesson.
- **Mills.** A mill multiplies the harvest. You may turn it or let it rest. Once the road is open, a north hold can be planted.
- **Industry and engines.** An engine house burns wood into drive and speeds the fields. Gatherers haul wood to it. You may set the engine or bank it. A banked engine makes no drive, and the other holds cannot copy it while it is cold.
- **Electricity and cities of light.** Drive becomes power, and lamps are strung over the city. Lit lamps ease fatigue and fear. You may kindle the lamps or darken them. Darkening them costs faith and raises fear.
- **The present.** A press is kept in the house of letters. You may bless the present, which lets the west quarter be planted, or keep a commons that moves a tenth of the richer store to the poorer hold. The years still turn after that. Once the road is open, the other holds raise their own mill, engine, and lamps from their own wood, and someone there keeps them. A failed hold stays empty until you bless a house back into it.

An age begins only when its facts are true: enough years, people, meals, wood, shelter, tools, faith, learning, drive, or power. The right-hand panel says what is still missing. **The years turn** resolves one year of labor, kinship, and building, so later ages can be reached without watching every day. Divine acts that lack the wood, the field, the smithy, the hall, the mill, the engine, or the power say so and change nothing.

The record is `elyon-first-light.json` in the persistent data folder, version 2. It keeps the people, their parents, the age they were born into, the line's memory of the garden, the pact, the raid, a death, a planted hold, and a dark year, the settlements, and the chronicle. It does not keep the key. Older tiny records are ignored.

This machine has no Unity editor license and no GPU, so the valley was not rendered here. Open the project in a licensed Unity 6000 editor and press Play to see it.

Ground, sand, bark, and rock photographs are CC0 maps from Poly Haven. See `ElyonFirstLight/Assets/Elyon/THIRD-PARTY.txt`.

## Earlier eight-day campaign

The Electron window is an earlier campaign, not this game. Requirements: Node.js 20 or newer.

```bash
npm install
npm start
```

`npm start` opens the desktop window. The garden is drawn on a canvas. Menus, dialogue, and the divine log sit over it.

### Install a build

```bash
npm run dist
```

On Linux this writes:

- `dist/linux-unpacked/elyon` — run that file directly
- `dist/Elyon-1.0.0.AppImage` — one file you can mark executable and launch

Windows NSIS and macOS DMG targets are declared in `package.json`. Build those on the matching operating system (`npx electron-builder --win` or `--mac`).

You can also open `index.html` from a local static server (`npx serve .`). Opening the file directly in a browser blocks ES modules on some systems. The desktop app does not have that limit.

## Campaign controls

1. **Begin** (or **Continue** if a record already exists).
2. **Open your eyes**, then follow the gold action at the bottom of the screen through the days of making.
3. After dry land appears, press **M** to walk the garden. Drag to look. **WASD** or the arrow keys move with your gaze. Click open ground to walk there. In the sky, drag orbits and a ground click moves your presence.
4. Press **E** beside Adam or Eve to speak. Sky view can also address them by clicking them.
5. After the grove is planted, number keys **1–8** select brushes (water, meadow, bloom, tree, bless, beast, fish, bird). They spend Breath.
6. **Esc** pauses. **H** opens help. **F** toggles fullscreen. The scroll wheel zooms.

The campaign has four endings: harmony, exile, wonder, and order. After an ending you may keep walking the garden.

The campaign window still draws with Three.js. That view is the earlier campaign, not First Light.

Adam, Eve, and the creatures can answer through Grok on the current xAI Responses API (`POST https://api.x.ai/v1/responses`, model `grok-4.7` unless you choose another). Each one is instructed to believe they really are that person in Eden. They do not admit to being a model. **Hear them** on the action bar opens that conversation. The campaign's own dialogue still carries the eight days and the four endings.

Paste an xAI key in the pause menu. It is stored only in `localStorage` under `elyon-xai-key`. The garden record (`elyon-save-v1` in the browser, `elyon-save.json` in the desktop app) never contains it. With no key, the rest of the game runs and Hear them explains that a key is needed.

## Saves

The game keeps one record automatically:

- In the desktop app: Electron `userData` / `elyon-save.json`
- In a browser: `localStorage` key `elyon-save-v1`

If both exist, the newer `updatedAt` wins. Pause menu **Export record** writes `elyon-save.json`. **Import record** reads one back. A new creation replaces the record on this computer.

## Tests

```bash
npm test
```

The campaign rules (ritual order, dialogue, the four endings, movement, and save repair) live in `js/sim.js` and `js/save.js` and are covered by `test/game.test.js`.

## Fonts

Cormorant Garamond and Cinzel are included as WOFF2 files under `assets/fonts/` and are licensed under the SIL Open Font License. See `assets/fonts/OFL.txt`.
