import assert from "node:assert/strict";
import test from "node:test";
import { createNewGame } from "../js/sim.js";
import {
  SETTINGS_KEY,
  SLOT_COUNT,
  assembleLibrary,
  defaultSettings,
  emptyLibrary,
  importGame,
  normalizeSettings,
  parseLibrary,
  pickSettings,
  readSlot,
  serializeLibrary,
  writeSettingsRecord,
  writeSlot,
} from "../js/slots.js";

function memoryStorage() {
  const map = new Map();
  return {
    getItem(key) {
      return map.has(key) ? map.get(key) : null;
    },
    setItem(key, value) {
      map.set(key, String(value));
    },
    removeItem(key) {
      map.delete(key);
    },
  };
}

test("three slots round-trip and an overwrite leaves the other gardens", () => {
  const library = emptyLibrary();
  const first = createNewGame(2);
  first.names.adam = "Adam";
  first.dayIndex = 2;
  const third = createNewGame(6);
  third.names.adam = "Kept";
  third.dayIndex = 5;
  writeSlot(library, 0, first);
  writeSlot(library, 2, third);
  assert.equal(readSlot(library, 0).names.adam, "Adam");
  assert.equal(readSlot(library, 0).dayIndex, 2);
  assert.equal(readSlot(library, 1), null);
  assert.equal(readSlot(library, 2).names.adam, "Kept");
  assert.equal(readSlot(library, 2).dayIndex, 5);
  assert.equal(library.slots.length, SLOT_COUNT);

  const again = createNewGame(8);
  again.names.adam = "New";
  again.dayIndex = 1;
  writeSlot(library, 0, again);
  assert.equal(readSlot(library, 0).names.adam, "New");
  assert.equal(readSlot(library, 0).dayIndex, 1);
  assert.equal(readSlot(library, 2).names.adam, "Kept");
  assert.equal(readSlot(library, 2).dayIndex, 5);

  writeSlot(library, 9, again);
  writeSlot(library, -1, again);
  assert.equal(readSlot(library, 2).names.adam, "Kept");
  assert.equal(library.slots.length, SLOT_COUNT);
});

test("legacy disk and localStorage saves migrate into slots once", () => {
  const legacy = createNewGame(4);
  legacy.updatedAt = 1000;
  legacy.names.adam = "Disk";
  const local = createNewGame(5);
  local.updatedAt = 2000;
  local.names.eve = "LocalEve";
  const library = assembleLibrary({
    legacyText: JSON.stringify(legacy),
    localText: JSON.stringify(local),
  });
  assert.equal(readSlot(library, 0).seed, legacy.seed);
  assert.equal(readSlot(library, 0).names.adam, "Disk");
  assert.equal(readSlot(library, 1).seed, local.seed);
  assert.equal(readSlot(library, 2), null);

  const again = assembleLibrary({
    diskText: JSON.stringify(library),
    legacyText: JSON.stringify(legacy),
    localText: JSON.stringify(local),
  });
  assert.equal(again.slots.filter(Boolean).length, 2);
  assert.equal(readSlot(again, 0).updatedAt, 1000);
  assert.equal(readSlot(again, 1).updatedAt, 2000);
});

test("browser and disk libraries merge unique slots and drop an invalid game", () => {
  const older = createNewGame(1);
  older.updatedAt = 10;
  const newer = createNewGame(2);
  newer.updatedAt = 50;
  const disk = assembleLibrary({ legacyText: JSON.stringify(older) });
  disk.updatedAt = 10;
  const browser = assembleLibrary({ legacyText: JSON.stringify(newer) });
  browser.updatedAt = 50;
  const merged = assembleLibrary({
    diskText: JSON.stringify(disk),
    browserText: JSON.stringify(browser),
  });
  const seeds = merged.slots.filter(Boolean).map((slot) => slot.game.seed).sort((a, b) => a - b);
  assert.deepEqual(seeds, [older.seed, newer.seed].sort((a, b) => a - b));

  const bad = createNewGame(3);
  bad.version = 99;
  const dropped = assembleLibrary({ legacyText: JSON.stringify(bad) });
  assert.equal(dropped.slots.every((slot) => slot === null), true);
});

test("a full library keeps a newer arrival and ignores a repeated stamp", () => {
  const library = emptyLibrary();
  for (let i = 0; i < 3; i += 1) {
    const game = createNewGame(i + 1);
    game.updatedAt = 100 + i;
    importGame(library, game);
  }
  const newer = createNewGame(9);
  newer.updatedAt = 500;
  importGame(library, newer);
  const stamps = library.slots.map((slot) => slot.savedAt);
  assert.equal(stamps.includes(500), true);
  assert.equal(stamps.includes(100), false);
  importGame(library, JSON.parse(JSON.stringify(newer)));
  assert.equal(library.slots.filter((slot) => slot.savedAt === 500).length, 1);
});

test("serializing a library does not restamp the garden inside a slot", () => {
  const game = createNewGame(3);
  game.updatedAt = 42;
  const library = assembleLibrary({ legacyText: JSON.stringify(game) });
  const text = serializeLibrary(library);
  const back = parseLibrary(text);
  assert.equal(back.format, 1);
  assert.equal(back.slots[0].game.updatedAt, 42);
  assert.equal(back.slots[0].savedAt, 42);
  assert.notEqual(back.updatedAt, 42);
});

test("settings round-trip, defaults, clamps, and the newer record wins", () => {
  const storage = memoryStorage();
  const saved = writeSettingsRecord(storage, {
    version: 1,
    master: 0.25,
    fullscreen: true,
    textSpeed: "slow",
    voice: false,
  });
  assert.equal(saved.master, 0.25);
  assert.equal(saved.fullscreen, true);
  assert.equal(saved.textSpeed, "slow");
  assert.equal(saved.voice, false);
  assert.ok(saved.updatedAt > 0);

  const loaded = normalizeSettings(storage.getItem(SETTINGS_KEY));
  assert.equal(loaded.master, 0.25);
  assert.equal(loaded.fullscreen, true);
  assert.equal(loaded.textSpeed, "slow");
  assert.equal(loaded.voice, false);
  assert.equal(loaded.version, 1);

  const migrated = normalizeSettings({ master: 0.5 });
  assert.equal(migrated.version, 1);
  assert.equal(migrated.master, 0.5);
  assert.equal(migrated.voice, true);
  assert.equal(migrated.textSpeed, "normal");
  assert.equal(migrated.fullscreen, false);

  const clamped = normalizeSettings({ version: 1, master: 4, textSpeed: "nope", fullscreen: 1 });
  assert.equal(clamped.master, 1);
  assert.equal(clamped.textSpeed, "normal");
  assert.equal(clamped.fullscreen, true);

  assert.equal(normalizeSettings({ version: 2, master: 0.2 }), null);

  const older = { ...defaultSettings(), updatedAt: 10, master: 0.2 };
  const newer = { ...defaultSettings(), updatedAt: 20, master: 0.9 };
  assert.equal(pickSettings(older, newer).master, 0.9);
  assert.equal(pickSettings(newer, older).master, 0.9);
  assert.equal(pickSettings(newer, null).master, 0.9);
  assert.equal(pickSettings(null, null), null);
});
