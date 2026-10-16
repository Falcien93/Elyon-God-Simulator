# Elyon

A single-player mythic simulator you can install. You play as Elyon and shape the first garden: light, waters, land, the two trees, the lights of the sky, the creatures, and Adam and Eve. Then you walk among them, name what lives, speak or keep silent, and see which ending the garden keeps.

Adam and Eve can also be addressed freely. Their replies follow what you say and the living field (age, coherence, cycle, seals). Text chat always works. Voice input and spoken replies use the Web Speech API when the window has it, and stay in the log when it does not.

This is an original telling, not a scripture. The earlier single-page Unity Thread sketch (population, ten Divine Fiat actions, and the seal victory screen) remains in the history of `main`. This desktop game keeps that field’s ages, seals, coherence, and achievements beside the creation campaign.

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

Windows NSIS and macOS DMG targets are declared in `package.json`. Build those on the matching operating system (`npx electron-builder --win` or `--mac`).

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

Campaign rules (ritual order, dialogue, the four endings, movement, and save repair) live in `js/sim.js` and `js/save.js`. Address replies, achievements, and voice fallback live in `js/converse.js` and `js/voice.js`. Slots, migration, and settings live in `js/slots.js`. They are covered by `test/game.test.js`, `test/campaign.test.js`, and `test/saves.test.js`.

## Fonts

Cormorant Garamond and Cinzel are included as WOFF2 files under `assets/fonts/` and are licensed under the SIL Open Font License. See `assets/fonts/OFL.txt`.
