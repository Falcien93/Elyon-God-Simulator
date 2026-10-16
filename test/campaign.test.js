import assert from "node:assert/strict";
import test from "node:test";
import { ENDINGS } from "../js/content.js";
import { clearLocal, loadBest, loadLocal, normalize, pickNewer, serialize, writeLocal } from "../js/save.js";
import {
  chooseSilence,
  chooseTalk,
  createNewGame,
  currentNode,
  dialogueEntry,
  enterWalk,
  noteRestIfNear,
  performRitual,
  primaryAction,
  setCommandment,
  startDialogue,
  advanceTalk,
} from "../js/sim.js";
import { WORLD_H, WORLD_W, findKind } from "../js/world.js";

function pump(state) {
  for (let i = 0; i < 12; i += 1) {
    if (!state.talk) return;
    const node = currentNode(state);
    if (state.talk.line < node.lines.length - 1) {
      advanceTalk(state);
      continue;
    }
    if (node.next) {
      advanceTalk(state);
      continue;
    }
    return;
  }
}

function throughCreatures(seed) {
  const state = createNewGame(seed);
  for (const id of ["light", "waters", "land", "grove", "lights", "creatures", "form_adam"]) {
    assert.equal(performRitual(state, id).ok, true, id);
  }
  return state;
}

function nameAdam(state) {
  assert.equal(startDialogue(state, "adam").ok, true);
  pump(state);
  assert.equal(chooseTalk(state, 0).ok, true);
  state.talk = null;
}

function nameBeasts(state) {
  assert.equal(startDialogue(state, "adam").ok, true);
  pump(state);
  assert.equal(chooseTalk(state, 0).ok, true);
  pump(state);
  assert.equal(chooseTalk(state, 0).ok, true);
  pump(state);
  assert.equal(chooseTalk(state, 0).ok, true);
  pump(state);
  assert.equal(chooseTalk(state, 0).ok, true);
  pump(state);
  state.talk = null;
}

function greetEve(state) {
  assert.equal(startDialogue(state, "eve").ok, true);
  pump(state);
  chooseTalk(state, 2);
  assert.equal(state.talk, null);
}

function reachEveChoice(seed, { silence }) {
  const state = throughCreatures(seed);
  nameAdam(state);
  assert.equal(performRitual(state, "form_eve").ok, true);
  nameBeasts(state);
  if (silence) assert.equal(chooseSilence(state).ok, true);
  else assert.equal(setCommandment(state, "Do not eat of the tree of knowledge.").ok, true);
  greetEve(state);
  assert.equal(dialogueEntry(state, "eve"), "eve_choice");
  assert.equal(startDialogue(state, "eve").ok, true);
  pump(state);
  assert.equal(currentNode(state).id, "eve_choice");
  return state;
}

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
    keys() {
      return [...map.keys()];
    },
  };
}

test("day progression advances one day at a time and rejects skips", () => {
  const state = createNewGame(21);
  const order = [
    { id: "light", day: 1, evening: "first day" },
    { id: "waters", day: 2, evening: "second day" },
    { id: "land", day: 3, evening: "third day" },
    { id: "grove", day: 4, evening: "Fruit took its color" },
    { id: "lights", day: 5, evening: "fourth day" },
    { id: "creatures", day: 6, evening: "began to move" },
  ];

  assert.equal(performRitual(state, "grove").reason, "locked");
  assert.equal(state.dayIndex, 0);
  assert.equal(primaryAction(state).id, "light");

  for (const step of order) {
    const before = state.dayIndex;
    assert.equal(primaryAction(state).id, step.id);
    const result = performRitual(state, step.id);
    assert.equal(result.ok, true, step.id);
    assert.equal(state.dayIndex, before + 1);
    assert.equal(state.dayIndex, step.day);
    assert.match(result.day.evening, new RegExp(step.evening));
    assert.equal(performRitual(state, step.id).reason, "already");
  }

  assert.equal(performRitual(state, "form_eve").reason, "lonely");
  const adam = performRitual(state, "form_adam");
  assert.equal(adam.ok, true);
  assert.equal(state.dayIndex, 6);
  assert.equal(adam.day, null);
  assert.equal(primaryAction(state).type, "walk");

  nameAdam(state);
  assert.equal(primaryAction(state).id, "form_eve");
  const eve = performRitual(state, "form_eve");
  assert.equal(eve.ok, true);
  assert.equal(state.dayIndex, 7);
  assert.match(eve.day.evening, /Two breaths/);
  assert.equal(primaryAction(state).type, "walk");

  assert.equal(enterWalk(state).ok, true);
  const adamBody = findKind(state.world, "adam");
  const eveBody = findKind(state.world, "eve");
  state.player.x = (adamBody.x + eveBody.x) / 2;
  state.player.y = (adamBody.y + eveBody.y) / 2;
  const rest = noteRestIfNear(state);
  assert.equal(state.flags.rest_adam, true);
  assert.equal(state.flags.rest_eve, true);
  assert.equal(rest.id, "rest");
  assert.equal(state.dayIndex, 8);
  assert.equal(noteRestIfNear(state), null);
});

test("all four endings can be selected and stay selected", () => {
  assert.deepEqual(Object.keys(ENDINGS).sort(), ["exile", "harmony", "order", "wonder"]);

  const paths = [
    { id: "harmony", silence: false, choice: 0 },
    { id: "exile", silence: false, choice: 1 },
    { id: "order", silence: false, choice: 2 },
    { id: "wonder", silence: true, choice: 1 },
  ];

  const seen = [];
  for (const path of paths) {
    const state = reachEveChoice(30 + seen.length, { silence: path.silence });
    assert.equal(state.ending, null);
    const chosen = chooseTalk(state, path.choice);
    assert.equal(chosen.ok, true, path.id);
    assert.equal(state.ending.id, path.id);
    assert.equal(state.flags.serpent_gone, true);
    const held = state.ending.id;
    assert.equal(startDialogue(state, "serpent").ok, false);
    assert.equal(startDialogue(state, "eve").ok, true);
    pump(state);
    if (state.talk && currentNode(state).choices?.length) chooseTalk(state, 0);
    assert.equal(state.ending.id, held);
    seen.push(path.id);
  }
  assert.deepEqual(seen, ["harmony", "exile", "order", "wonder"]);
});

test("save and load round-trip and migrate an older record", async () => {
  const state = throughCreatures(11);
  nameAdam(state);
  performRitual(state, "form_eve");
  state.names.eve = "Chava";
  state.mode = "walk";
  state.commandments = ["Do not eat of the tree of knowledge."];
  state.flags.commandment_spoken = true;
  state.chat = [
    { who: "elyon", text: "Be still." },
    { who: "eve", text: "We are listening." },
  ];
  state.achievements = ["first_seed", "walked"];
  state.beings.eve.faith = 77;
  state.beings.eve.lastWords = "We are listening.";
  state.ending = { id: "harmony", at: 50 };
  state.player.x = 18.25;
  state.player.y = 12.5;

  const restored = normalize(serialize(state));
  assert.equal(restored.version, 1);
  assert.equal(restored.dayIndex, state.dayIndex);
  assert.equal(restored.mode, "walk");
  assert.equal(restored.names.eve, "Chava");
  assert.equal(restored.names.adam, state.names.adam);
  assert.equal(restored.commandments[0], state.commandments[0]);
  assert.equal(restored.flags.commandment_spoken, true);
  assert.equal(restored.flags.eve_made, true);
  assert.equal(restored.ending.id, "harmony");
  assert.deepEqual(restored.chat, state.chat);
  assert.ok(restored.achievements.includes("first_seed"));
  assert.equal(restored.beings.eve.faith, 77);
  assert.equal(restored.beings.eve.lastWords, "We are listening.");
  assert.equal(restored.player.x, 18.25);
  assert.equal(restored.world.tiles.length, WORLD_W * WORLD_H);
  assert.equal(restored.world.entities.length, state.world.entities.length);

  const storage = memoryStorage();
  globalThis.localStorage = storage;
  try {
    assert.equal(writeLocal(state), true);
    const loaded = loadLocal();
    assert.equal(loaded.names.eve, "Chava");
    assert.equal(loaded.ending.id, "harmony");
    assert.equal(loaded.chat[1].text, "We are listening.");

    const early = JSON.parse(storage.getItem(storage.keys()[0]));
    delete early.chat;
    delete early.achievements;
    delete early.beings;
    delete early.thread;
    delete early.address;
    early.achievements = ["first_seed", "not-a-real-mark", 4];
    early.chat = [
      { who: "elyon", text: "hello" },
      { who: "serpent", text: "hiss" },
      { who: "adam", text: "<>" },
    ];
    const migrated = normalize(early);
    assert.equal(migrated.names.eve, "Chava");
    assert.equal(migrated.dayIndex, state.dayIndex);
    assert.equal(migrated.flags.ritual_grove, true);
    assert.deepEqual(migrated.chat, [{ who: "elyon", text: "hello" }]);
    assert.deepEqual(migrated.achievements, ["first_seed"]);
    assert.equal(migrated.address, "adam");
    assert.equal(migrated.beings.adam.faith, 40);
    assert.equal(migrated.beings.eve.mood, 64);
    assert.equal(migrated.thread.seals, 7);
    assert.equal(migrated.thread.coherence, 18 + 6.5 * 7);
    assert.equal(migrated.thread.beings, 2);

    const bare = JSON.parse(serialize(createNewGame(1)));
    bare.mode = "walk";
    bare.flags = { seen_intro: true };
    const grounded = normalize(bare);
    assert.equal(grounded.mode, "sky");
    assert.equal(grounded.flags.seen_intro, true);

    assert.equal(normalize({ version: "elyon_v3", coherence: 80, seals: 7 }), null);
    assert.equal(normalize({ version: 2, world: { w: WORLD_W, h: WORLD_H, tiles: [] } }), null);

    const localRaw = JSON.parse(storage.getItem(storage.keys()[0]));
    localRaw.updatedAt = 10;
    localRaw.names.adam = "Older";
    storage.setItem(storage.keys()[0], JSON.stringify(localRaw));
    const disk = createNewGame(4);
    performRitual(disk, "light");
    disk.names.adam = "Newer";
    const diskText = serialize(disk);
    const diskData = JSON.parse(diskText);
    diskData.updatedAt = 90;
    globalThis.window = {
      elyonDesktop: {
        loadSave: async () => JSON.stringify(diskData),
      },
    };
    const best = await loadBest();
    assert.equal(best.names.adam, "Newer");
    assert.equal(best.flags.ritual_light, true);

    diskData.updatedAt = 1;
    globalThis.window.elyonDesktop.loadSave = async () => JSON.stringify(diskData);
    const kept = await loadBest();
    assert.equal(kept.names.adam, "Older");

    globalThis.window.elyonDesktop.loadSave = async () => {
      throw new Error("disk unavailable");
    };
    const fallback = await loadBest();
    assert.equal(fallback.names.adam, "Older");

    assert.equal(pickNewer(null, restored), restored);
    clearLocal();
    assert.equal(loadLocal(), null);
  } finally {
    delete globalThis.localStorage;
    delete globalThis.window;
  }
});
