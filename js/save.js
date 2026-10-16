/** Save validation and browser/desktop persistence. */

import { NODES } from "./content.js";
import { SAVE_VERSION, createNewGame, sanitizeName } from "./sim.js";
import { TILE, WORLD_H, WORLD_W } from "./world.js";

const STORAGE_KEY = "elyon-save-v1";
const KINDS = new Set([
  "tree",
  "tree_life",
  "tree_knowledge",
  "fish",
  "bird",
  "deer",
  "sheep",
  "lion",
  "adam",
  "eve",
  "serpent",
]);

export function serialize(state) {
  state.updatedAt = Date.now();
  return JSON.stringify(state);
}

export function normalize(raw) {
  let data = raw;
  if (typeof raw === "string") {
    try {
      data = JSON.parse(raw);
    } catch {
      return null;
    }
  }
  if (!data || typeof data !== "object" || data.version !== SAVE_VERSION) return null;
  const world = data.world;
  if (!world || !Array.isArray(world.tiles) || world.tiles.length !== WORLD_W * WORLD_H) return null;
  if (world.w !== WORLD_W || world.h !== WORLD_H) return null;
  for (const tile of world.tiles) {
    if (!Number.isInteger(tile) || tile < TILE.CHAOS || tile > TILE.FLOWER) return null;
  }
  if (!Array.isArray(world.entities) || world.entities.length > 80) return null;

  const state = createNewGame(Number.isFinite(data.seed) ? data.seed : 1);
  state.seed = data.seed >>> 0 || 1;
  state.updatedAt = Number(data.updatedAt) || 0;
  state.mode = data.mode === "walk" ? "walk" : "sky";
  state.dayIndex = clampIndex(data.dayIndex);
  state.time = finite(data.time, 0.3) % 1;
  if (state.time < 0) state.time += 1;
  state.timeFlows = Boolean(data.timeFlows);
  state.breath = clampNum(data.breath, 0, 100, 72);
  state.breathMax = 100;
  state.stats.order = clampNum(data.stats?.order, 0, 100, 48);
  state.stats.wonder = clampNum(data.stats?.wonder, 0, 100, 42);
  state.flags = sanitizeFlags(data.flags);
  state.names.adam = sanitizeName(data.names?.adam) || "Adam";
  state.names.eve = sanitizeName(data.names?.eve) || "Eve";
  state.species = {
    deer: sanitizeName(data.species?.deer) || "",
    sheep: sanitizeName(data.species?.sheep) || "",
    lion: sanitizeName(data.species?.lion) || "",
  };
  state.log = Array.isArray(data.log) ? data.log.filter((line) => typeof line === "string").slice(-200) : state.log;
  state.commandments = Array.isArray(data.commandments)
    ? data.commandments.filter((line) => typeof line === "string").map((line) => line.slice(0, 180)).slice(0, 1)
    : [];
  state.codex = Array.isArray(data.codex) ? data.codex.filter((id) => typeof id === "string").slice(0, 32) : [];
  state.world.tiles = world.tiles.slice();
  state.world.entities = world.entities.map(sanitizeEntity).filter(Boolean);
  const player = data.player || {};
  state.player = {
    x: clampNum(player.x, 0.3, WORLD_W - 0.3, 20.5),
    y: clampNum(player.y, 0.3, WORLD_H - 0.3, 17.4),
    facing: ["n", "e", "s", "w"].includes(player.facing) ? player.facing : "s",
  };
  state.dest = null;
  state.relations.adam = sanitizeRel(data.relations?.adam);
  state.relations.eve = sanitizeRel(data.relations?.eve);
  if (data.ending && typeof data.ending.id === "string") {
    state.ending = { id: data.ending.id, at: Number(data.ending.at) || 0 };
  }
  state.talk = sanitizeTalk(data.talk);
  state.nextEntity = clampNum(data.nextEntity, 1, 100000, state.world.entities.length + 1);
  state.beastBrush = clampNum(data.beastBrush, 0, 1000, 0);
  state.settings = {
    music: clampNum(data.settings?.music, 0, 1, 0.32),
    sfx: clampNum(data.settings?.sfx, 0, 1, 0.7),
  };
  if (state.mode === "walk" && !state.flags.ritual_land) state.mode = "sky";
  return state;
}

function sanitizeTalk(talk) {
  if (!talk || typeof talk !== "object") return null;
  if (talk.who !== "adam" && talk.who !== "eve" && talk.who !== "serpent") return null;
  if (typeof talk.nodeId !== "string" || !NODES[talk.nodeId]) return null;
  const lines = NODES[talk.nodeId].lines?.length || 1;
  return { who: talk.who, nodeId: talk.nodeId, line: clampNum(talk.line, 0, lines - 1, 0) };
}

function sanitizeEntity(entity) {
  if (!entity || typeof entity !== "object") return null;
  if (typeof entity.id !== "string" || entity.id.length > 40) return null;
  if (!KINDS.has(entity.kind)) return null;
  const x = Number(entity.x);
  const y = Number(entity.y);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
  return {
    id: entity.id,
    kind: entity.kind,
    x: Math.max(0, Math.min(WORLD_W, x)),
    y: Math.max(0, Math.min(WORLD_H, y)),
    tx: Number.isFinite(entity.tx) ? entity.tx : x,
    ty: Number.isFinite(entity.ty) ? entity.ty : y,
    pause: Number.isFinite(entity.pause) ? entity.pause : 0,
    facing: ["n", "e", "s", "w"].includes(entity.facing) ? entity.facing : "s",
    name: sanitizeName(entity.name) || "",
    homeX: Number.isFinite(entity.homeX) ? entity.homeX : undefined,
    homeY: Number.isFinite(entity.homeY) ? entity.homeY : undefined,
  };
}

function sanitizeFlags(flags) {
  const out = {};
  if (!flags || typeof flags !== "object") return out;
  for (const [key, value] of Object.entries(flags)) {
    if (!/^[\w]{1,40}$/.test(key)) continue;
    if (value === true) out[key] = true;
  }
  return out;
}

function sanitizeRel(rel) {
  return {
    trust: clampNum(rel?.trust, 0, 100, 20),
    wonder: clampNum(rel?.wonder, 0, 100, 40),
    will: clampNum(rel?.will, 0, 100, 30),
  };
}

function finite(n, fallback) {
  return Number.isFinite(n) ? n : fallback;
}

function clampNum(n, min, max, fallback) {
  const value = Number(n);
  if (!Number.isFinite(value)) return fallback;
  return Math.max(min, Math.min(max, value));
}

function clampIndex(n) {
  const value = Number(n);
  if (!Number.isInteger(value)) return 0;
  return Math.max(0, Math.min(8, value));
}

export function pickNewer(a, b) {
  if (!a) return b || null;
  if (!b) return a;
  return (a.updatedAt || 0) >= (b.updatedAt || 0) ? a : b;
}

export function loadLocal() {
  try {
    if (typeof localStorage === "undefined") return null;
    const text = localStorage.getItem(STORAGE_KEY);
    if (!text) return null;
    return normalize(text);
  } catch {
    return null;
  }
}

export function writeLocal(state) {
  try {
    if (typeof localStorage === "undefined") return false;
    localStorage.setItem(STORAGE_KEY, serialize(state));
    return true;
  } catch {
    return false;
  }
}

export function clearLocal() {
  try {
    if (typeof localStorage === "undefined") return;
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore quota and private-mode failures */
  }
}

export async function loadBest() {
  const local = loadLocal();
  let disk = null;
  try {
    if (typeof window !== "undefined" && window.elyonDesktop?.loadSave) {
      const text = await Promise.race([
        window.elyonDesktop.loadSave(),
        new Promise((_resolve, reject) => {
          setTimeout(() => reject(new Error("timeout")), 2500);
        }),
      ]);
      if (text) disk = normalize(text);
    }
  } catch {
    disk = null;
  }
  return pickNewer(disk, local);
}

export async function writeBest(state) {
  const text = serialize(state);
  writeLocal(state);
  try {
    if (typeof window !== "undefined" && window.elyonDesktop?.writeSave) {
      await window.elyonDesktop.writeSave(text);
    }
  } catch {
    /* the browser copy still stands */
  }
}
