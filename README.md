# Elyon

A single-player mythic simulator. You play as Elyon and shape the first garden: light, waters, land, the two trees, the lights of the sky, the creatures, and the first people. Then you walk among them, name what lives, speak or keep silent, and see which ending the garden keeps.

This is an original telling, not a scripture.

## Play

Requirements: Node.js 20 or newer.

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

## How to play

1. **Begin** (or **Continue** if a record already exists).
2. **Open your eyes**, then follow the gold action at the bottom of the screen through the days of making.
3. After dry land appears, press **M** to walk the garden. **WASD** or the arrow keys move you. Click open ground to walk there.
4. Press **E** beside Adam or Eve to speak. Sky view can also address them by clicking them.
5. After the grove is planted, number keys **1–8** select brushes (water, meadow, bloom, tree, bless, beast, fish, bird). They spend Breath.
6. **Esc** pauses. **H** opens help. **F** toggles fullscreen. The scroll wheel zooms.

The campaign has four endings: harmony, exile, wonder, and order. After an ending you may keep walking the garden.

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
