/** Three save slots and global settings. Pure data: no Electron, no DOM. */

import { DAYS, ENDINGS } from "./content.js";
import { normalize } from "./save.js";

export const STORE_FORMAT = 1;
export const SLOT_COUNT = 3;
export const SETTINGS_VERSION = 1;
export const TEXT_SPEEDS = ["slow", "normal", "fast"];
export const LIBRARY_KEY = "elyon-saves-v1";
export const SETTINGS_KEY = "elyon-settings-v1";

export function emptyLibrary() {
  return {
    format: STORE_FORMAT,
    active: 0,
    updatedAt: 0,
    seen: [],
    slots: [null, null, null],
  };
}

export function defaultSettings() {
  return {
    version: SETTINGS_VERSION,
    master: 0.8,
    fullscreen: false,
    textSpeed: "normal",
    voice: true,
    updatedAt: 0,
  };
}

export function charsPerSecond(speed) {
  if (speed === "slow") return 28;
  if (speed === "fast") return 100000;
  return 72;
}

export function normalizeSettings(raw) {
  let data = raw;
  if (typeof raw === "string") {
    try {
      data = JSON.parse(raw);
    } catch {
      return null;
    }
  }
  if (!data || typeof data !== "object" || Array.isArray(data)) return null;
  if (data.version !== undefined && data.version !== SETTINGS_VERSION) return null;
  return {
    version: SETTINGS_VERSION,
    master: clamp01(data.master, 0.8),
    fullscreen: Boolean(data.fullscreen),
    textSpeed: TEXT_SPEEDS.includes(data.textSpeed) ? data.textSpeed : "normal",
    voice: data.voice === undefined ? true : Boolean(data.voice),
    updatedAt: Number.isFinite(Number(data.updatedAt)) ? Number(data.updatedAt) : 0,
  };
}

export function writeSettingsRecord(storage, settings) {
  const next = normalizeSettings(settings) || defaultSettings();
  next.updatedAt = Date.now();
  storage.setItem(SETTINGS_KEY, JSON.stringify(next));
  return next;
}

export function readSettingsRecord(storage) {
  try {
    if (!storage) return null;
    const text = storage.getItem(SETTINGS_KEY);
    if (!text) return null;
    return normalizeSettings(text);
  } catch {
    return null;
  }
}

export function pickSettings(a, b) {
  if (!a) return b || null;
  if (!b) return a;
  return (a.updatedAt || 0) >= (b.updatedAt || 0) ? a : b;
}

export function writeSlot(library, index, state) {
  if (!library || !Number.isInteger(index) || index < 0 || index >= SLOT_COUNT || !state) return library;
  remember(library, library.slots[index]?.savedAt || 0);
  state.updatedAt = Date.now();
  const game = normalize(JSON.parse(JSON.stringify(state)));
  if (!game) return library;
  game.updatedAt = state.updatedAt;
  library.slots[index] = { savedAt: state.updatedAt, game };
  remember(library, state.updatedAt);
  library.active = index;
  library.updatedAt = state.updatedAt;
  return library;
}

export function readSlot(library, index) {
  const slot = library?.slots?.[index];
  if (!slot?.game) return null;
  return normalize(slot.game);
}

export function slotLabel(slot) {
  if (!slot?.game) return "Empty";
  const game = slot.game;
  const day = DAYS[game.dayIndex] || DAYS[0];
  const names = [];
  if (game.flags?.adam_made) names.push(game.names?.adam || "Adam");
  if (game.flags?.eve_made) names.push(game.names?.eve || "Eve");
  const who = names.length ? names.join(" and ") : "Before the people";
  const ending = game.ending?.id && ENDINGS[game.ending.id] ? ENDINGS[game.ending.id].title : null;
  const when = slot.savedAt ? new Date(slot.savedAt).toLocaleString() : "";
  return [day?.title || "The garden", who, ending, when].filter(Boolean).join(" · ");
}

export function parseLibrary(raw) {
  if (raw == null || raw === "") return null;
  let data = raw;
  if (typeof raw === "string") {
    try {
      data = JSON.parse(raw);
    } catch {
      return null;
    }
  }
  if (!data || typeof data !== "object" || Array.isArray(data)) return null;
  if (data.format === STORE_FORMAT && Array.isArray(data.slots)) {
    const library = emptyLibrary();
    library.updatedAt = Number(data.updatedAt) || 0;
    library.active = clampSlot(data.active);
    library.seen = cleanSeen(data.seen);
    for (let i = 0; i < SLOT_COUNT; i += 1) {
      const slot = data.slots[i];
      if (!slot || typeof slot !== "object") continue;
      const game = normalize(slot.game);
      if (!game) continue;
      const savedAt = Number(slot.savedAt) || game.updatedAt || 0;
      game.updatedAt = game.updatedAt || savedAt;
      library.slots[i] = { savedAt, game };
      remember(library, savedAt);
    }
    if (!library.slots[library.active]) {
      const first = library.slots.findIndex(Boolean);
      if (first >= 0) library.active = first;
    }
    return library;
  }
  const game = normalize(data);
  if (!game) return null;
  const library = emptyLibrary();
  const savedAt = game.updatedAt || 0;
  library.slots[0] = { savedAt, game };
  library.updatedAt = savedAt;
  remember(library, savedAt);
  return library;
}

export function importGame(library, raw) {
  const game = normalize(raw);
  if (!game || !library) return library;
  const stamp = game.updatedAt || 0;
  if (stamp !== 0 && knownStamp(library, stamp)) return library;
  const packed = { savedAt: stamp, game };
  const empty = library.slots.findIndex((slot) => !slot);
  if (empty >= 0) {
    library.slots[empty] = packed;
    remember(library, stamp);
    if (!library.slots[library.active]) library.active = empty;
    return library;
  }
  let oldest = 0;
  for (let i = 1; i < SLOT_COUNT; i += 1) {
    if ((library.slots[i]?.savedAt || 0) < (library.slots[oldest]?.savedAt || 0)) oldest = i;
  }
  if (stamp > (library.slots[oldest]?.savedAt || 0)) {
    remember(library, library.slots[oldest]?.savedAt || 0);
    library.slots[oldest] = packed;
    remember(library, stamp);
  }
  return library;
}

export function mergeLibraries(a, b) {
  if (!a && !b) return emptyLibrary();
  if (!a) return cloneLibrary(b);
  if (!b) return cloneLibrary(a);
  const primary = libraryStamp(a) >= libraryStamp(b) ? a : b;
  const secondary = primary === a ? b : a;
  const out = cloneLibrary(primary);
  for (const slot of secondary.slots) {
    if (slot?.game) importGame(out, slot.game);
  }
  for (const stamp of secondary.seen || []) remember(out, stamp);
  return out;
}

export function assembleLibrary({ diskText, legacyText, browserText, localText } = {}) {
  const library = mergeLibraries(parseLibrary(diskText), parseLibrary(browserText));
  if (legacyText) importGame(library, legacyText);
  if (localText) importGame(library, localText);
  return library;
}

export function serializeLibrary(library) {
  const source = library || emptyLibrary();
  source.updatedAt = Date.now();
  const slots = [];
  for (let i = 0; i < SLOT_COUNT; i += 1) {
    const slot = source.slots?.[i];
    if (!slot?.game) {
      slots.push(null);
      continue;
    }
    slots.push({
      savedAt: slot.savedAt || slot.game.updatedAt || 0,
      game: slot.game,
    });
  }
  return JSON.stringify({
    format: STORE_FORMAT,
    active: clampSlot(source.active),
    updatedAt: source.updatedAt,
    seen: cleanSeen(source.seen),
    slots,
  });
}

function cloneLibrary(library) {
  return parseLibrary(JSON.stringify({
    format: STORE_FORMAT,
    active: library.active || 0,
    updatedAt: library.updatedAt || 0,
    seen: library.seen || [],
    slots: library.slots,
  })) || emptyLibrary();
}

function libraryStamp(library) {
  let stamp = library.updatedAt || 0;
  for (const slot of library.slots || []) {
    if (slot && (slot.savedAt || 0) > stamp) stamp = slot.savedAt;
  }
  return stamp;
}

function knownStamp(library, stamp) {
  if (!stamp) return false;
  if (library.slots?.some((slot) => slot && slot.savedAt === stamp)) return true;
  return Array.isArray(library.seen) && library.seen.includes(stamp);
}

function remember(library, stamp) {
  if (!Number.isFinite(stamp) || stamp === 0) return;
  if (!Array.isArray(library.seen)) library.seen = [];
  if (!library.seen.includes(stamp)) library.seen.push(stamp);
  if (library.seen.length > 48) library.seen.splice(0, library.seen.length - 48);
}

function cleanSeen(seen) {
  if (!Array.isArray(seen)) return [];
  return seen.filter((n) => Number.isFinite(n) && n !== 0).slice(-48);
}

function clampSlot(index) {
  const value = Number(index);
  if (!Number.isInteger(value)) return 0;
  return Math.max(0, Math.min(SLOT_COUNT - 1, value));
}

function clamp01(n, fallback) {
  const value = Number(n);
  if (!Number.isFinite(value)) return fallback;
  return Math.max(0, Math.min(1, value));
}
