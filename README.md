# Elyon

Elyon: First Light is a Unity HDRP garden. Adam and Eve are already awake. You stay above them or walk among them, and you speak. They have bodies, they answer as those people through the xAI Responses API, and they live a day: wake, eat, drink, work, rest. They follow the shore. They do not walk through the lake. Only you can step on the water.

Unreal Engine 5 could not be installed or run on the machine that built this (no Epic account, no GPU device). The game is Unity 6000.0.64f1 with the High Definition Render Pipeline.

This is an original telling, not a scripture. Linen, no sexual content. "A child" on a body card is a burden, not a scene.

## Play First Light

Open `ElyonFirstLight` in Unity 6000.0.64f1 or newer with HDRP. Use **Elyon → Open First Light**, then press Play. The outdoors scene builds the garden when it starts.

- **M**, or the Sky / Walk button, switches between the sky and walking among them.
- Drag to look. **WASD** or the arrows move. In the sky that pans your presence. On the ground it walks, including across the lake.
- Click Adam or Eve, type, and press Enter or **Speak**. **C** or **Come here** calls the chosen person along the shore.
- Hunger, thirst, and fatigue change through the day. A tired person moves slowly, and the card says so.

Paste an xAI key into the panel and press **Keep the key here**. It is written only to `elyon-xai-key.txt` in the app's persistent data folder (`Application.persistentDataPath`). A file named `xai-key.local.txt` next to the Unity project is also read and is gitignored. The garden record never contains the key. With no key, the day still runs and the panel explains that a key is needed.

Speech uses `POST https://api.x.ai/v1/responses` with model `grok-4.7`. Adam and Eve are instructed to believe they are those people. They do not say they are an assistant, a language model, or Grok. A new line can start before the last one finishes, and they can talk while they walk.

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
