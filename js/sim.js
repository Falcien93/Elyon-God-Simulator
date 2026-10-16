/** Pure game rules. No DOM. */

import {
  BEAST_CYCLE,
  CODEX,
  DAYS,
  ENDINGS,
  NODES,
  SHAPES,
} from "./content.js";
import {
  SPOT,
  TILE,
  WORLD_H,
  WORLD_W,
  blocksFoot,
  carveWaters,
  countKind,
  createWorld,
  entityAt,
  fillNight,
  findKind,
  inBounds,
  isCreature,
  isTree,
  placeHuman,
  placeSerpent,
  plantGrove,
  raiseLand,
  seedCreatures,
  setTile,
  tileAt,
} from "./world.js";

export const SAVE_VERSION = 1;
export const BREATH_MAX = 100;

const CREATURE_CAP = 28;

export function createNewGame(seed = 1) {
  const state = {
    version: SAVE_VERSION,
    seed: seed >>> 0 || 1,
    updatedAt: 0,
    mode: "sky",
    dayIndex: 0,
    time: 0.08,
    timeFlows: false,
    breath: 72,
    breathMax: BREATH_MAX,
    stats: { order: 48, wonder: 42 },
    flags: { seen_intro: false },
    names: { adam: "Adam", eve: "Eve" },
    species: { deer: "", sheep: "", lion: "" },
    log: [],
    commandments: [],
    codex: [],
    world: createWorld(),
    player: { x: SPOT.descend.x, y: SPOT.descend.y, facing: "n" },
    dest: null,
    relations: {
      adam: { trust: 20, wonder: 36, will: 28 },
      eve: { trust: 20, wonder: 44, will: 34 },
    },
    ending: null,
    talk: null,
    works: [],
    minds: { adam: [], eve: [], creatures: [] },
    nextEntity: 1,
    beastBrush: 0,
    settings: { music: 0.32, sfx: 0.7 },
  };
  addLog(state, "In the beginning there was a hush, and you were already listening.");
  return state;
}

export function rand(state) {
  state.seed = (Math.imul(state.seed, 1664525) + 1013904223) >>> 0;
  return state.seed / 4294967296;
}

export function clamp(n, a, b) {
  return Math.max(a, Math.min(b, n));
}

export function addLog(state, text) {
  state.log.push(String(text));
  if (state.log.length > 200) state.log.splice(0, state.log.length - 200);
}

function unlockCodex(state, id) {
  if (!CODEX[id]) return;
  if (!state.codex.includes(id)) state.codex.push(id);
}

export function phaseName(state) {
  if (!state.flags.ritual_light) return "The deep";
  const h = sunHeight(state.time);
  if (h > 0.85) return "Noon";
  if (h > 0.35) return state.time < 0.5 ? "Morning" : "Afternoon";
  if (h > 0.05) return state.time < 0.5 ? "Dawn" : "Dusk";
  return "Night";
}

export function sunHeight(time) {
  return Math.sin((time - 0.25) * Math.PI * 2);
}

export function derivedStats(state) {
  const light = state.flags.ritual_light
    ? clamp(
        Math.round(58 + sunHeight(state.time) * 28 + (state.flags.ritual_lights ? 12 : 0)),
        8,
        100,
      )
    : 4;
  const creatures = state.world.entities.filter((e) => isCreature(e.kind)).length;
  const green = state.world.tiles.filter((t) => t === TILE.GRASS || t === TILE.FLOWER).length;
  let life = Math.round((green / (WORLD_W * WORLD_H)) * 70 + creatures * 2);
  if (state.flags.adam_made) life += 8;
  if (state.flags.eve_made) life += 8;
  return {
    light,
    life: clamp(life, 0, 100),
    order: clamp(Math.round(state.stats.order), 0, 100),
    wonder: clamp(Math.round(state.stats.wonder), 0, 100),
  };
}

export function currentObjective(state) {
  if (state.dayIndex < DAYS.length) return DAYS[state.dayIndex];
  if (!state.flags.beasts_named) {
    return {
      id: "names",
      numeral: "the garden",
      title: "Names",
      detail: "Descend and name the creatures with Adam. A name lets them answer.",
    };
  }
  if (!state.flags.commandment_spoken && !state.flags.silence) {
    return {
      id: "word",
      numeral: "the garden",
      title: "The word",
      detail: "Speak a commandment about the Tree of Knowledge, or keep silent. Both will matter.",
    };
  }
  if (!state.ending) {
    return {
      id: "choice",
      numeral: "the garden",
      title: "The choice",
      detail: state.flags.serpent_present
        ? "A low voice is at the Tree of Knowledge. Speak with Eve before the garden decides itself."
        : "Walk the garden. The choice is ripening.",
    };
  }
  return {
    id: "epilogue",
    numeral: "after",
    title: "Epilogue",
    detail: "The garden is open. Walk it as long as you wish.",
  };
}

export function primaryAction(state) {
  if (!state.flags.ritual_light) return { type: "ritual", id: "light", label: "Let there be light" };
  if (!state.flags.ritual_waters) return { type: "ritual", id: "waters", label: "Divide the waters" };
  if (!state.flags.ritual_land) return { type: "ritual", id: "land", label: "Let the dry land appear" };
  if (!state.flags.ritual_grove) return { type: "ritual", id: "grove", label: "Bring forth the grove" };
  if (!state.flags.ritual_lights) return { type: "ritual", id: "lights", label: "Set the lights in the sky" };
  if (!state.flags.ritual_creatures) return { type: "ritual", id: "creatures", label: "Fill earth and water" };
  if (!state.flags.adam_made) return { type: "ritual", id: "form_adam", label: "Form Adam", confirm: true };
  if (!state.flags.adam_asked_companion) {
    if (state.mode !== "walk") return { type: "walk", label: "Descend and speak with Adam" };
  } else if (!state.flags.eve_made) {
    return { type: "ritual", id: "form_eve", label: "Form Eve", confirm: true };
  }
  if (DAYS[state.dayIndex]?.id === "rest" && state.mode !== "walk") {
    return { type: "walk", label: "Walk with them" };
  }
  if (state.mode === "walk") return { type: "sky", label: "Ascend to the sky" };
  return { type: "walk", label: "Descend into the garden" };
}

export function availableShapes(state) {
  const tools = [];
  if (state.flags.ritual_waters) tools.push("water");
  if (state.flags.ritual_land) tools.push("meadow", "bloom", "tree", "bless");
  if (state.flags.ritual_creatures) tools.push("beast", "fish", "bird");
  return tools;
}

function nextId(state) {
  const id = `e${state.nextEntity}`;
  state.nextEntity += 1;
  return id;
}

function bumpRelation(state, who, key, amount) {
  const bag = state.relations[who];
  if (!bag || !Number.isFinite(amount)) return;
  bag[key] = clamp((bag[key] || 0) + amount, 0, 100);
}

function acknowledgeDay(state) {
  const day = DAYS[state.dayIndex];
  if (!day || !dayComplete(state, day.id)) return null;
  state.dayIndex += 1;
  addLog(state, day.evening);
  return day;
}

function dayComplete(state, id) {
  switch (id) {
    case "light":
      return Boolean(state.flags.ritual_light);
    case "waters":
      return Boolean(state.flags.ritual_waters);
    case "land":
      return Boolean(state.flags.ritual_land);
    case "grove":
      return Boolean(state.flags.ritual_grove);
    case "lights":
      return Boolean(state.flags.ritual_lights);
    case "creatures":
      return Boolean(state.flags.ritual_creatures);
    case "humanity":
      return Boolean(state.flags.adam_made && state.flags.eve_made);
    case "rest":
      return Boolean(state.flags.rest_adam && state.flags.rest_eve);
    default:
      return false;
  }
}

function finish(state, extra = {}) {
  const day = acknowledgeDay(state);
  refreshStory(state);
  return { ok: true, day, ...extra };
}

export function performRitual(state, id) {
  if (state.ending && (id === "form_adam" || id === "form_eve")) {
    return { ok: false, reason: "already" };
  }
  switch (id) {
    case "light": {
      if (state.flags.ritual_light) return { ok: false, reason: "already" };
      if (state.dayIndex !== 0) return { ok: false, reason: "locked" };
      fillNight(state.world);
      state.flags.ritual_light = true;
      state.time = 0.34;
      unlockCodex(state, "light");
      addLog(state, "Let there be light. The hush took a surface.");
      return finish(state, { cue: "ritual", flash: 1 });
    }
    case "waters": {
      if (state.flags.ritual_waters) return { ok: false, reason: "already" };
      if (!state.flags.ritual_light) return { ok: false, reason: "locked" };
      carveWaters(state.world);
      state.flags.ritual_waters = true;
      unlockCodex(state, "waters");
      addLog(state, "The waters divided. A sea took the south, a river the east, a lake the west.");
      return finish(state, { cue: "ritual", flash: 0.45 });
    }
    case "land": {
      if (state.flags.ritual_land) return { ok: false, reason: "already" };
      if (!state.flags.ritual_waters) return { ok: false, reason: "locked" };
      raiseLand(state.world);
      state.flags.ritual_land = true;
      unlockCodex(state, "land");
      addLog(state, "Dry land rose. Grass took the garden floor.");
      return finish(state, { cue: "ritual", flash: 0.35 });
    }
    case "grove": {
      if (state.flags.ritual_grove) return { ok: false, reason: "already" };
      if (!state.flags.ritual_land) return { ok: false, reason: "locked" };
      plantGrove(state.world, () => rand(state));
      state.flags.ritual_grove = true;
      unlockCodex(state, "grove");
      addLog(state, "You set the Tree of Life and the Tree of Knowledge, and the grove stood up around them.");
      return finish(state, { cue: "ritual", flash: 0.3 });
    }
    case "lights": {
      if (state.flags.ritual_lights) return { ok: false, reason: "already" };
      if (!state.flags.ritual_grove) return { ok: false, reason: "locked" };
      state.flags.ritual_lights = true;
      state.timeFlows = true;
      state.time = 0.48;
      unlockCodex(state, "lights");
      addLog(state, "A greater light and a lesser light took their watches. The garden learned hours.");
      return finish(state, { cue: "ritual", flash: 0.7 });
    }
    case "creatures": {
      if (state.flags.ritual_creatures) return { ok: false, reason: "already" };
      if (!state.flags.ritual_lights) return { ok: false, reason: "locked" };
      seedCreatures(state.world, () => rand(state), () => nextId(state));
      state.flags.ritual_creatures = true;
      unlockCodex(state, "creatures");
      addLog(state, "Fish took the water, birds the air, beasts the grass. The garden moved.");
      return finish(state, { cue: "ritual", flash: 0.25 });
    }
    case "form_adam": {
      if (state.flags.adam_made) return { ok: false, reason: "already" };
      if (!state.flags.ritual_creatures) return { ok: false, reason: "locked" };
      placeHuman(state.world, "adam");
      state.flags.adam_made = true;
      state.names.adam = "Adam";
      addLog(state, "You formed a man from the willing ground and breathed. He opened his eyes.");
      return finish(state, { cue: "ritual", flash: 0.4 });
    }
    case "form_eve": {
      if (state.flags.eve_made) return { ok: false, reason: "already" };
      if (!state.flags.adam_asked_companion) return { ok: false, reason: "lonely" };
      if (!state.flags.adam_made) return { ok: false, reason: "locked" };
      placeHuman(state.world, "eve");
      state.flags.eve_made = true;
      state.names.eve = "Eve";
      addLog(state, "You formed a companion, awake in her own right. Adam was no longer the only voice.");
      return finish(state, { cue: "ritual", flash: 0.4 });
    }
    default:
      return { ok: false, reason: "unknown" };
  }
}

export function enterWalk(state) {
  if (!state.flags.ritual_land) return { ok: false, reason: "locked" };
  state.mode = "walk";
  if (!state.flags.descended) {
    state.player.x = SPOT.descend.x;
    state.player.y = SPOT.descend.y;
    state.player.facing = "n";
    state.flags.descended = true;
    addLog(state, "You descended. The grass held your presence without breaking.");
  }
  return { ok: true, cue: "ui" };
}

export function enterSky(state) {
  state.mode = "sky";
  return { ok: true, cue: "ui" };
}

export function toggleMode(state) {
  if (state.mode === "walk") return enterSky(state);
  return enterWalk(state);
}

function occupied(world, x, y) {
  return entityAt(world, x + 0.01, y + 0.01, () => true);
}

export function paint(state, x, y, tool) {
  if (!availableShapes(state).includes(tool)) return { ok: false, reason: "locked" };
  if (!inBounds(x, y)) return { ok: false, reason: "bounds" };
  const spec = SHAPES[tool];
  if (!spec) return { ok: false, reason: "unknown" };
  if (state.breath < spec.cost) return { ok: false, reason: "breath" };

  const tile = tileAt(state.world, x, y);
  const here = occupied(state.world, x, y);

  if (tool === "bless") {
    state.breath -= spec.cost;
    state.stats.order = clamp(state.stats.order + 2, 0, 100);
    state.stats.wonder = clamp(state.stats.wonder + 1, 0, 100);
    if (tile === TILE.GRASS) setTile(state.world, x, y, TILE.FLOWER);
    if (!state.flags.hint_bless) {
      state.flags.hint_bless = true;
      addLog(state, "You blessed a place. Order gathered there like warm dust.");
    }
    return { ok: true, cue: "bless" };
  }

  if (here && (isTree(here.kind) || here.kind === "adam" || here.kind === "eve" || here.kind === "serpent")) {
    return { ok: false, reason: "occupied" };
  }

  if (tool === "water") {
    if (tile === TILE.STONE) return { ok: false, reason: "tile" };
    setTile(state.world, x, y, TILE.WATER);
  } else if (tool === "meadow") {
    if (tile === TILE.DEEP) return { ok: false, reason: "tile" };
    setTile(state.world, x, y, TILE.GRASS);
  } else if (tool === "bloom") {
    if (tile !== TILE.GRASS && tile !== TILE.FLOWER && tile !== TILE.SAND) {
      return { ok: false, reason: "land" };
    }
    setTile(state.world, x, y, TILE.FLOWER);
  } else if (tool === "tree") {
    if (tile !== TILE.GRASS && tile !== TILE.FLOWER) return { ok: false, reason: "land" };
    if (countKind(state.world, "tree") >= 40) return { ok: false, reason: "cap" };
    state.world.entities.push({
      id: nextId(state),
      kind: "tree",
      x: x + 0.5,
      y: y + 0.5,
      tx: x + 0.5,
      ty: y + 0.5,
      pause: 0,
      facing: "s",
      name: "",
    });
  } else if (tool === "fish" || tool === "bird" || tool === "beast") {
    const creatureCount = state.world.entities.filter((e) => isCreature(e.kind)).length;
    if (creatureCount >= CREATURE_CAP) return { ok: false, reason: "cap" };
    let kind = tool;
    if (tool === "fish") {
      if (tile !== TILE.WATER && tile !== TILE.DEEP) return { ok: false, reason: "water" };
      kind = "fish";
    } else if (tool === "bird") {
      if (tile === TILE.STONE || tile === TILE.CHAOS) return { ok: false, reason: "tile" };
      kind = "bird";
    } else {
      if (tile !== TILE.GRASS && tile !== TILE.FLOWER && tile !== TILE.SAND) {
        return { ok: false, reason: "land" };
      }
      kind = BEAST_CYCLE[state.beastBrush % BEAST_CYCLE.length];
      state.beastBrush += 1;
    }
    state.world.entities.push({
      id: nextId(state),
      kind,
      x: x + 0.5,
      y: y + 0.5,
      tx: x + 0.5,
      ty: y + 0.5,
      pause: 0.2,
      facing: "s",
      name: state.species[kind] || "",
    });
  }

  state.breath -= spec.cost;
  return { ok: true, cue: "paint" };
}

export const REASONS = {
  locked: "That word is not yet yours to speak.",
  already: "It has already been spoken.",
  breath: "Your breath is thin. Wait, and it returns.",
  tile: "The ground will not take that.",
  bounds: "Beyond the garden’s edge.",
  water: "Fish must be set in the water.",
  land: "That needs dry ground.",
  occupied: "Something sacred already stands there.",
  cap: "The garden is full enough.",
  lonely: "Speak with Adam first. He has not yet asked.",
  unknown: "Nothing answers to that.",
  ended: "That chapter is already closed.",
  name: "Give a name made of letters.",
  empty: "There is nothing to say.",
};

export function sanitizeName(raw) {
  const cleaned = String(raw ?? "")
    .replace(/[^\p{L}\p{N} '\-]/gu, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 16);
  return cleaned.length ? cleaned : null;
}

export function sanitizeCommandment(raw) {
  const cleaned = String(raw ?? "")
    .replace(/[<>]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 180);
  return cleaned.length ? cleaned : null;
}

export function setCommandment(state, raw) {
  if (state.ending || state.flags.serpent_present || state.flags.serpent_gone) {
    return { ok: false, reason: "already" };
  }
  if (!state.flags.eve_made) return { ok: false, reason: "locked" };
  const text = sanitizeCommandment(raw);
  if (!text) return { ok: false, reason: "empty" };
  state.commandments = [text];
  state.flags.commandment_spoken = true;
  state.flags.silence = false;
  unlockCodex(state, "word");
  addLog(state, `You spoke a commandment: “${text}”`);
  refreshStory(state);
  return finish(state, { cue: "ritual" });
}

export function chooseSilence(state) {
  if (state.ending || state.flags.serpent_present || state.flags.serpent_gone) {
    return { ok: false, reason: "already" };
  }
  if (!state.flags.eve_made) return { ok: false, reason: "locked" };
  if (state.flags.silence) return { ok: false, reason: "already" };
  state.flags.silence = true;
  state.flags.commandment_spoken = false;
  state.commandments = [];
  unlockCodex(state, "word");
  addLog(state, "You kept silent. No prohibition was set upon the tree.");
  state.stats.wonder = clamp(state.stats.wonder + 8, 0, 100);
  refreshStory(state);
  return finish(state, { cue: "ui" });
}

export function refreshStory(state) {
  if (state.ending) return;
  if (
    state.flags.beasts_named &&
    (state.flags.commandment_spoken || state.flags.silence) &&
    !state.flags.serpent_present &&
    !state.flags.serpent_gone
  ) {
    state.flags.serpent_present = true;
    placeSerpent(state.world);
    unlockCodex(state, "choice");
    addLog(state, "Something low and bright coiled in the Tree of Knowledge.");
  }
}

export function dialogueEntry(state, who) {
  if (who === "adam") {
    if (!findKind(state.world, "adam")) return null;
    if (state.ending) return `adam_epilogue_${state.ending.id}`;
    if (!state.flags.adam_named) return "adam_first";
    if (!state.flags.eve_made && state.flags.adam_asked_companion) {
      return state.flags.beasts_named ? "adam_waiting_named" : "adam_waiting_eve";
    }
    if (!state.flags.beasts_named) return "adam_hub_unnamed";
    return "adam_hub";
  }
  if (who === "eve") {
    if (!findKind(state.world, "eve")) return null;
    if (state.ending) return `eve_epilogue_${state.ending.id}`;
    if (!state.flags.eve_greeted) return "eve_first";
    if (state.flags.serpent_present && !state.flags.serpent_gone) return "eve_choice";
    return "eve_hub";
  }
  if (who === "serpent") {
    if (!state.flags.serpent_present || state.flags.serpent_gone) return null;
    if (state.ending) return null;
    return "serpent_meet";
  }
  return null;
}

export function nearestTalkTarget(state) {
  const talkers = state.world.entities.filter((e) => e.kind === "adam" || e.kind === "eve" || e.kind === "serpent");
  let best = null;
  let bestD = 1.45;
  for (const e of talkers) {
    if (e.kind === "serpent" && (state.flags.serpent_gone || state.ending)) continue;
    const d = Math.hypot(e.x - state.player.x, e.y - state.player.y);
    if (d < bestD) {
      bestD = d;
      best = e;
    }
  }
  return best;
}

export function startDialogue(state, who, mode = state.mode) {
  const entry = dialogueEntry(state, who);
  if (!entry || !NODES[entry]) return { ok: false, reason: "empty" };
  state.dest = null;
  if (who === "adam" || who === "eve") {
    const person = findKind(state.world, who);
    if (
      DAYS[state.dayIndex]?.id === "rest" &&
      mode === "walk" &&
      person &&
      Math.hypot(person.x - state.player.x, person.y - state.player.y) < 1.7
    ) {
      state.flags[`rest_${who}`] = true;
    }
  }
  state.talk = { who, nodeId: entry, line: 0 };
  runOnEnter(state, NODES[entry]);
  const day = acknowledgeDay(state);
  refreshStory(state);
  return { ok: true, day, cue: "ui" };
}

export function currentNode(state) {
  if (!state.talk) return null;
  return NODES[state.talk.nodeId] || null;
}

function runOnEnter(state, node) {
  if (!node?.onEnter || !node.onEnter.length) return;
  const key = `entered_${node.id}`;
  if (state.flags[key]) return;
  state.flags[key] = true;
  applyFxList(state, node.onEnter);
}

function applyFxList(state, fxList) {
  for (const fx of fxList || []) applyFx(state, fx);
}

function applyFx(state, fx) {
  const [head, a, b] = fx.split(":");
  if (head === "flag") state.flags[a] = true;
  else if (head === "codex") unlockCodex(state, a);
  else if (head === "trust" || head === "wonder" || head === "will") {
    if (a === "adam" || a === "eve") bumpRelation(state, a, head, Number(b));
    else if (head === "wonder") state.stats.wonder = clamp(state.stats.wonder + Number(a), 0, 100);
  } else if (head === "order") {
    state.stats.order = clamp(state.stats.order + Number(a), 0, 100);
  } else if (head === "name" && a === "adam") {
    const name = sanitizeName(b);
    if (name) state.names.adam = name;
  } else if (head === "namekind") {
    const name = sanitizeName(b);
    if (name) {
      state.species[a] = name;
      for (const e of state.world.entities) if (e.kind === a) e.name = name;
      addLog(state, `The ${a} are called ${name}.`);
    }
  } else if (head === "ending") {
    resolveEnding(state, a);
  }
}

function resolveEnding(state, id) {
  if (state.ending) return;
  let endingId = id;
  if (id === "hands") endingId = state.flags.silence ? "wonder" : "exile";
  const ending = ENDINGS[endingId];
  if (!ending) return;
  state.ending = { id: endingId, at: Date.now() };
  state.flags.ending_seen = false;
  state.flags.serpent_gone = true;
  if (endingId === "order") {
    state.flags.serpent_gone = true;
    state.flags.tree_guarded = true;
  }
  if (endingId === "exile") {
    state.flags.clothed = true;
    const adam = findKind(state.world, "adam");
    const eve = findKind(state.world, "eve");
    if (adam) {
      adam.homeX = 38.2;
      adam.homeY = 22.4;
    }
    if (eve) {
      eve.homeX = 37.4;
      eve.homeY = 23.1;
    }
  }
  if (endingId === "harmony" || endingId === "wonder") state.flags.serpent_gone = true;
  addLog(state, ending.title + ".");
  unlockCodex(state, "choice");
}

export function formatLine(state, text) {
  const cmd = state.commandments[0] || (state.flags.silence ? "You kept silent, and set no prohibition." : "the word not yet spoken");
  return String(text)
    .replaceAll("{adam}", state.names.adam || "Adam")
    .replaceAll("{eve}", state.names.eve || "Eve")
    .replaceAll("{commandment}", cmd);
}

export function advanceTalk(state) {
  const node = currentNode(state);
  if (!node || !state.talk) return { ok: false, reason: "empty" };
  const last = state.talk.line >= node.lines.length - 1;
  if (!last) {
    state.talk.line += 1;
    return { ok: true };
  }
  if (node.input) return { ok: false, reason: "name" };
  if (node.choices && node.choices.length) return { ok: false, reason: "empty" };
  if (node.next && NODES[node.next]) {
    return gotoNode(state, node.next);
  }
  state.talk = null;
  return { ok: true, closed: true };
}

function gotoNode(state, id) {
  if (id === "close") {
    state.talk = null;
    const day = acknowledgeDay(state);
    refreshStory(state);
    return { ok: true, closed: true, day };
  }
  const node = NODES[id];
  if (!node) {
    state.talk = null;
    return { ok: false, reason: "unknown" };
  }
  state.talk.nodeId = id;
  state.talk.line = 0;
  runOnEnter(state, node);
  const day = acknowledgeDay(state);
  refreshStory(state);
  return { ok: true, day };
}

export function visibleChoices(state, node) {
  if (!node?.choices) return [];
  return node.choices.filter((choice) => {
    if (choice.when === "commandment") return Boolean(state.flags.commandment_spoken);
    if (choice.when === "silence") return Boolean(state.flags.silence);
    if (choice.when === "eve") return Boolean(state.flags.eve_made);
    return true;
  });
}

export function chooseTalk(state, index) {
  const node = currentNode(state);
  if (!node || !state.talk) return { ok: false, reason: "empty" };
  if (state.talk.line < node.lines.length - 1) return { ok: false, reason: "locked" };
  const choice = visibleChoices(state, node)[index];
  if (!choice) return { ok: false, reason: "unknown" };
  applyFxList(state, choice.fx || []);
  return gotoNode(state, choice.goto);
}

export function submitTalkInput(state, raw) {
  const node = currentNode(state);
  if (!node?.input || !state.talk) return { ok: false, reason: "empty" };
  if (state.talk.line < node.lines.length - 1) return { ok: false, reason: "locked" };
  const name = sanitizeName(raw);
  if (!name) return { ok: false, reason: "name" };
  const save = node.input.save;
  if (save === "adam") state.names.adam = name;
  else if (save === "eve") state.names.eve = name;
  else if (save === "deer" || save === "sheep" || save === "lion") {
    state.species[save] = name;
    for (const e of state.world.entities) if (e.kind === save) e.name = name;
    addLog(state, `The ${save} are called ${name}.`);
  }
  applyFxList(state, node.fx || []);
  return gotoNode(state, node.then || "close");
}

export function noteRestIfNear(state) {
  if (DAYS[state.dayIndex]?.id !== "rest" || state.mode !== "walk") return null;
  for (const who of ["adam", "eve"]) {
    const e = findKind(state.world, who);
    if (!e) continue;
    const d = Math.hypot(e.x - state.player.x, e.y - state.player.y);
    if (d < 1.6) state.flags[`rest_${who}`] = true;
  }
  return acknowledgeDay(state);
}

export function tick(state, dt) {
  const step = clamp(dt, 0, 0.05);
  if (state.timeFlows) state.time = (state.time + step / 210) % 1;
  state.breath = clamp(state.breath + step * 7, 0, state.breathMax);
  if (state.mode === "walk" && state.dest && !state.talk) {
    const dx = state.dest.x - state.player.x;
    const dy = state.dest.y - state.player.y;
    if (Math.hypot(dx, dy) < 0.1) state.dest = null;
    else {
      const beforeX = state.player.x;
      const beforeY = state.player.y;
      movePlayer(state, dx, dy, step);
      if (Math.hypot(state.player.x - beforeX, state.player.y - beforeY) < 0.001) state.dest = null;
    }
  }
  stepEntities(state, step);
  return noteRestIfNear(state);
}

function stepEntities(state, dt) {
  for (const e of state.world.entities) {
    if (isTree(e.kind) || e.kind === "serpent") continue;
    if (state.talk && state.talk.who === e.kind) continue;
    e.pause = (e.pause || 0) - dt;
    const dist = Math.hypot((e.tx ?? e.x) - e.x, (e.ty ?? e.y) - e.y);
    if (e.pause > 0 || dist < 0.08) {
      if (e.pause <= 0) {
        const spot = pickTarget(state, e);
        e.tx = spot.x;
        e.ty = spot.y;
        e.pause = 1.2 + rand(state) * 3.4;
      }
      continue;
    }
    const speed = e.kind === "bird" ? 1.1 : e.kind === "lion" ? 0.72 : e.kind === "fish" ? 0.45 : 0.48;
    const dx = e.tx - e.x;
    const dy = e.ty - e.y;
    const len = Math.hypot(dx, dy) || 1;
    const nx = e.x + (dx / len) * speed * dt;
    const ny = e.y + (dy / len) * speed * dt;
    if (canEntityStep(state, e, nx, ny)) {
      e.facing = Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? "e" : "w") : dy > 0 ? "s" : "n";
      e.x = nx;
      e.y = ny;
    } else {
      e.pause = 0;
      e.tx = e.x;
      e.ty = e.y;
    }
  }
}

function canEntityStep(state, e, x, y) {
  if (x < 0.4 || y < 0.4 || x > WORLD_W - 0.4 || y > WORLD_H - 0.4) return false;
  const tile = tileAt(state.world, Math.floor(x), Math.floor(y));
  if (e.kind === "fish") return tile === TILE.WATER || tile === TILE.DEEP;
  if (e.kind === "bird") return tile !== TILE.STONE && tile !== TILE.CHAOS;
  if (tile === TILE.STONE || tile === TILE.CHAOS || tile === TILE.WATER || tile === TILE.DEEP) return false;
  return true;
}

function pickTarget(state, e) {
  if (e.kind === "adam" || e.kind === "eve") {
    const hx = e.homeX ?? (e.kind === "eve" ? SPOT.eve.x : SPOT.adam.x);
    const hy = e.homeY ?? (e.kind === "eve" ? SPOT.eve.y : SPOT.adam.y);
    for (let i = 0; i < 8; i += 1) {
      const x = hx + (rand(state) - 0.5) * 7;
      const y = hy + (rand(state) - 0.5) * 6;
      if (!blocksFoot(state.world, x, y)) return { x, y };
    }
    return { x: hx, y: hy };
  }
  for (let i = 0; i < 8; i += 1) {
    const x = e.x + (rand(state) - 0.5) * 8;
    const y = e.y + (rand(state) - 0.5) * 6;
    if (canEntityStep(state, e, x, y)) return { x, y };
  }
  return { x: e.x, y: e.y };
}

export function movePlayer(state, dx, dy, dt) {
  if (state.mode !== "walk") return;
  const len = Math.hypot(dx, dy);
  if (len === 0) return;
  const speed = 3.5;
  const step = clamp(dt, 0, 0.05) * speed;
  const vx = (dx / len) * step;
  const vy = (dy / len) * step;
  const tryX = clamp(state.player.x + vx, 0.35, WORLD_W - 0.35);
  const tryY = clamp(state.player.y + vy, 0.35, WORLD_H - 0.35);
  if (!blocksFoot(state.world, tryX, state.player.y)) state.player.x = tryX;
  if (!blocksFoot(state.world, state.player.x, tryY)) state.player.y = tryY;
  state.player.facing = Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? "e" : "w") : dy > 0 ? "s" : "n";
}

export function interact(state) {
  if (state.mode !== "walk") return { ok: false, reason: "locked" };
  const target = nearestTalkTarget(state);
  if (!target) {
    const creature = nearestCreature(state);
    if (creature) return { ok: true, hear: creature.kind, id: creature.id, cue: "ui" };
    return { ok: false, reason: "empty" };
  }
  return startDialogue(state, target.kind, "walk");
}

export function hearTarget(state) {
  const near = state.mode === "walk" ? nearestTalkTarget(state) || nearestCreature(state) : null;
  if (near) return { hear: near.kind, id: near.id };
  const adam = findKind(state.world, "adam");
  if (adam) return { hear: "adam", id: adam.id };
  const eve = findKind(state.world, "eve");
  if (eve) return { hear: "eve", id: eve.id };
  const creature = state.world.entities.find((entity) => isCreature(entity.kind));
  if (creature) return { hear: creature.kind, id: creature.id };
  return null;
}

function mindBucket(who) {
  if (who === "adam" || who === "eve") return who;
  return "creatures";
}

function remember(state, who, line) {
  if (!state.minds) state.minds = { adam: [], eve: [], creatures: [] };
  const bucket = mindBucket(who);
  if (!Array.isArray(state.minds[bucket])) state.minds[bucket] = [];
  const text = String(line || "").trim().slice(0, 180);
  if (!text) return;
  state.minds[bucket].push(text);
  if (state.minds[bucket].length > 12) state.minds[bucket].splice(0, state.minds[bucket].length - 12);
}

function beingBy(state, who, id) {
  if (id) {
    const match = state.world.entities.find((entity) => entity.id === id);
    if (match) return match;
  }
  return findKind(state.world, who);
}

export function placeWork(state, work) {
  if (!state.works) state.works = [];
  const label = String(work?.label || work?.what || "a made thing").replace(/\s+/g, " ").trim().slice(0, 80);
  if (!label) return null;
  const x = clamp(Number(work?.x), 1, WORLD_W - 1.2);
  const y = clamp(Number(work?.y), 1, WORLD_H - 1.2);
  const made = {
    id: `w${state.nextEntity}`,
    x: Number.isFinite(x) ? x : 20,
    y: Number.isFinite(y) ? y : 15,
    label,
    verb: String(work?.verb || work?.do || "make").slice(0, 32),
  };
  state.nextEntity += 1;
  state.works.push(made);
  if (state.works.length > 24) state.works.splice(0, state.works.length - 24);
  addLog(state, `${label} stands in the garden.`);
  return made;
}

function enactDeed(state, who, id, deed) {
  if (!deed || typeof deed !== "object") return;
  const verb = String(deed.do || deed.verb || "make").toLowerCase();
  const person = beingBy(state, who, id);
  const x = Number(deed.x);
  const y = Number(deed.y);
  if (person && (verb === "go" || verb === "walk" || verb === "move" || verb === "approach_elyon" || verb === "approach")) {
    if (verb === "approach_elyon" || verb === "approach") {
      person.tx = state.player.x;
      person.ty = state.player.y;
    } else if (Number.isFinite(x) && Number.isFinite(y)) {
      person.tx = clamp(x, 0.6, WORLD_W - 0.6);
      person.ty = clamp(y, 0.6, WORLD_H - 0.6);
    }
    person.pause = 0;
    return;
  }
  if (person && (verb === "rest" || verb === "sleep")) {
    person.pause = 8;
    return;
  }
  const anchor = person || state.player;
  placeWork(state, {
    label: deed.what || deed.detail || verb,
    verb,
    x: Number.isFinite(x) ? x : anchor.x + 0.8,
    y: Number.isFinite(y) ? y : anchor.y + 0.4,
  });
}

export function applyMind(state, who, reply, heard) {
  if (!reply || typeof reply !== "object") return { ok: false, reason: "empty" };
  if (heard) remember(state, who, `Elyon said: ${String(heard).slice(0, 160)}`);
  if (typeof reply.speech === "string" && reply.speech.trim()) {
    const speaker = who === "adam" ? state.names.adam : who === "eve" ? state.names.eve : who;
    addLog(state, `${speaker}: ${reply.speech.trim().slice(0, 400)}`);
    remember(state, who, reply.remember || reply.speech);
  } else if (reply.remember) {
    remember(state, who, reply.remember);
  }
  if ((who === "adam" || who === "eve") && Number.isFinite(Number(reply.trust))) {
    bumpRelation(state, who, "trust", clamp(Number(reply.trust), -8, 8));
  }
  const deeds = Array.isArray(reply.deeds) ? reply.deeds.slice(0, 3) : [];
  for (const deed of deeds) enactDeed(state, who, reply.id, deed);
  return { ok: true };
}

export function applyMoments(state, moments) {
  if (!Array.isArray(moments)) return { ok: false };
  for (const moment of moments.slice(0, 4)) {
    if (!moment || typeof moment.who !== "string") continue;
    applyMind(state, moment.who, moment);
  }
  return { ok: true };
}

function nearestCreature(state) {
  let best = null;
  let bestD = 1.3;
  for (const e of state.world.entities) {
    if (!isCreature(e.kind)) continue;
    const d = Math.hypot(e.x - state.player.x, e.y - state.player.y);
    if (d < bestD) {
      best = e;
      bestD = d;
    }
  }
  return best;
}

function entityUnder(state, x, y, radius) {
  const hits = state.world.entities.filter(
    (e) => Math.hypot(e.x - (x + 0.5), e.y - (y + 0.5)) < radius,
  );
  return (
    hits.find((e) => e.kind === "adam" || e.kind === "eve" || e.kind === "serpent") ||
    hits[0] ||
    null
  );
}

export function clickWorld(state, x, y, tool) {
  if (state.talk) return { ok: false, reason: "locked" };
  if (!inBounds(x, y)) return { ok: false, reason: "bounds" };
  if (state.mode === "walk") {
    const near = nearestTalkTarget(state);
    const clicked = entityUnder(state, x, y, 0.85);
    if (near && clicked && near.id === clicked.id) return interact(state);
    if (!blocksFoot(state.world, x + 0.5, y + 0.5)) {
      state.dest = { x: x + 0.5, y: y + 0.5 };
      return { ok: true };
    }
    return { ok: false, reason: "tile" };
  }
  const entity = entityUnder(state, x, y, 0.9);
  if (entity && (entity.kind === "adam" || entity.kind === "eve" || entity.kind === "serpent")) {
    if (entity.kind === "serpent" && (state.flags.serpent_gone || !state.flags.serpent_present || state.ending)) {
      return { ok: false, reason: "empty" };
    }
    return startDialogue(state, entity.kind, state.mode);
  }
  if (entity && isCreature(entity.kind)) {
    return { ok: true, hear: entity.kind, id: entity.id, cue: "ui" };
  }
  if (tool) return paint(state, x, y, tool);
  if (!blocksFoot(state.world, x + 0.5, y + 0.5)) {
    state.player.x = x + 0.5;
    state.player.y = y + 0.5;
    return { ok: true, cue: "ui" };
  }
  return { ok: false, reason: "empty" };
}

export { DAYS, ENDINGS, NODES, SHAPES, CODEX };
