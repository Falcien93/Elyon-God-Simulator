import assert from "node:assert/strict";
import test from "node:test";
import { NODES } from "../js/content.js";
import { normalize, serialize } from "../js/save.js";
import {
  addressBeing,
  advanceTalk,
  chooseSilence,
  chooseTalk,
  clickWorld,
  createNewGame,
  currentNode,
  dialogueEntry,
  enterSky,
  enterWalk,
  movePlayer,
  paint,
  performRitual,
  primaryAction,
  sanitizeCommandment,
  sanitizeName,
  setCommandment,
  startDialogue,
  submitTalkInput,
  tick,
  visibleChoices,
} from "../js/sim.js";
import { speakText, startListening, voiceSupport } from "../js/voice.js";
import { TILE, WORLD_H, WORLD_W, blocksFoot, findKind, tileAt } from "../js/world.js";

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

function nameAdam(state) {
  assert.equal(startDialogue(state, "adam").ok, true);
  pump(state);
  assert.equal(chooseTalk(state, 0).ok, true);
  assert.equal(state.names.adam, "Adam");
  assert.equal(state.flags.adam_asked_companion, true);
  state.talk = null;
}

function nameBeasts(state) {
  assert.equal(startDialogue(state, "adam").ok, true);
  pump(state);
  assert.equal(currentNode(state).id, "adam_hub_unnamed");
  assert.equal(chooseTalk(state, 0).ok, true);
  pump(state);
  assert.equal(currentNode(state).id, "adam_name_deer");
  assert.equal(chooseTalk(state, 0).ok, true);
  pump(state);
  assert.equal(chooseTalk(state, 0).ok, true);
  pump(state);
  assert.equal(chooseTalk(state, 0).ok, true);
  pump(state);
  assert.equal(state.flags.beasts_named, true);
  assert.equal(state.species.deer, "Hart");
  state.talk = null;
}

function greetEve(state) {
  assert.equal(startDialogue(state, "eve").ok, true);
  pump(state);
  assert.equal(currentNode(state).id, "eve_first");
  chooseTalk(state, 2);
  assert.equal(state.talk, null);
  assert.equal(state.flags.eve_greeted, true);
}

function garden(seed = 3) {
  const state = createNewGame(seed);
  for (const id of ["light", "waters", "land", "grove", "lights", "creatures", "form_adam"]) {
    const result = performRitual(state, id);
    assert.equal(result.ok, true, id);
  }
  assert.equal(performRitual(state, "form_eve").ok, false);
  nameAdam(state);
  assert.equal(performRitual(state, "form_eve").ok, true);
  assert.equal(state.dayIndex, 7);
  return state;
}

test("creation days advance in order and reject skips", () => {
  const state = createNewGame(1);
  assert.equal(performRitual(state, "waters").ok, false);
  assert.equal(performRitual(state, "light").ok, true);
  assert.equal(state.dayIndex, 1);
  assert.equal(performRitual(state, "light").ok, false);
  assert.equal(primaryAction(state).id, "waters");
  performRitual(state, "waters");
  performRitual(state, "land");
  assert.equal(state.flags.ritual_land, true);
  assert.ok(tileAt(state.world, 20, 14) === TILE.GRASS);
  assert.equal(enterWalk(state).ok, true);
});

test("campaign reaches the choice and every ending once", () => {
  const endings = [
    { id: "harmony", act: (state) => chooseTalk(state, 0) },
    { id: "exile", act: (state) => chooseTalk(state, 1) },
    { id: "order", act: (state) => chooseTalk(state, 2) },
  ];
  for (const ending of endings) {
    const state = garden(4);
    nameBeasts(state);
    assert.equal(setCommandment(state, "Do not eat of the tree of knowledge.").ok, true);
    assert.equal(state.flags.serpent_present, true);
    assert.ok(findKind(state.world, "serpent"));
    greetEve(state);
    assert.equal(dialogueEntry(state, "eve"), "eve_choice");
    startDialogue(state, "eve");
    pump(state);
    assert.equal(ending.act(state).ok, true);
    assert.equal(state.ending.id, ending.id);
    const again = startDialogue(state, "serpent");
    assert.equal(again.ok, false);
  }

  const quiet = garden(5);
  nameBeasts(quiet);
  assert.equal(chooseSilence(quiet).ok, true);
  assert.equal(quiet.flags.serpent_present, true);
  greetEve(quiet);
  startDialogue(quiet, "eve");
  pump(quiet);
  assert.equal(chooseTalk(quiet, 1).ok, true);
  assert.equal(quiet.ending.id, "wonder");
});

test("custom names and dialogue graph targets exist", () => {
  const state = createNewGame(8);
  for (const id of ["light", "waters", "land", "grove", "lights", "creatures", "form_adam"]) {
    performRitual(state, id);
  }
  startDialogue(state, "adam");
  pump(state);
  assert.equal(chooseTalk(state, 1).ok, true);
  assert.equal(currentNode(state).id, "adam_name_input");
  assert.equal(submitTalkInput(state, "  Havel  ").ok, true);
  assert.equal(state.names.adam, "Havel");
  assert.equal(sanitizeName("<script>"), "script");
  assert.equal(sanitizeName("!!!"), null);
  assert.equal(sanitizeCommandment("  <be kind>  "), "be kind");

  for (const node of Object.values(NODES)) {
    if (node.next) assert.ok(NODES[node.next], node.id);
    if (node.then) assert.ok(NODES[node.then], node.id);
    for (const choice of node.choices || []) {
      assert.ok(choice.goto === "close" || NODES[choice.goto], `${node.id} -> ${choice.goto}`);
    }
  }
});

test("paint respects breath, terrain, and sacred trees", () => {
  const state = garden(9);
  state.breath = 3;
  assert.equal(paint(state, 4, 8, "tree").reason, "breath");
  state.breath = 100;
  assert.equal(paint(state, -1, 0, "meadow").reason, "bounds");
  const tree = findKind(state.world, "tree_knowledge");
  const tx = Math.floor(tree.x);
  const ty = Math.floor(tree.y);
  assert.equal(paint(state, tx, ty, "water").reason, "occupied");
  assert.equal(paint(state, 4, 8, "fish").reason, "water");
  assert.equal(paint(state, 6, 28, "fish").ok, true);
  assert.equal(paint(state, 18, 16, "bloom").ok, true);
  assert.equal(tileAt(state.world, 18, 16), TILE.FLOWER);
});

test("the player cannot walk into the sea", () => {
  const state = garden(2);
  enterWalk(state);
  state.player.x = 12.5;
  state.player.y = 25.2;
  for (let i = 0; i < 40; i += 1) movePlayer(state, 0, 1, 0.05);
  assert.equal(blocksFoot(state.world, state.player.x, state.player.y), false);
  assert.ok(state.player.y < 26);
});

test("save round-trip rejects damaged records", () => {
  const state = garden(6);
  state.names.eve = "Chava";
  const restored = normalize(serialize(state));
  assert.equal(restored.names.eve, "Chava");
  assert.equal(restored.dayIndex, state.dayIndex);
  assert.equal(restored.world.tiles.length, WORLD_W * WORLD_H);
  assert.equal(normalize("{"), null);
  assert.equal(normalize({ version: 2 }), null);
  assert.equal(normalize({ version: 1, world: { w: WORLD_W, h: WORLD_H, tiles: [1, 2] } }), null);
});

test("word choices hide until a word or a silence exists", () => {
  const state = garden(1);
  startDialogue(state, "adam");
  state.talk = { who: "adam", nodeId: "adam_hub", line: 0 };
  const labels = visibleChoices(state, currentNode(state)).map((choice) => choice.goto);
  assert.equal(labels.includes("adam_topic_word"), false);
  state.flags.commandment_spoken = true;
  const later = visibleChoices(state, currentNode(state)).map((choice) => choice.goto);
  assert.equal(later.includes("adam_topic_word"), true);
});

test("click to walk does not cross water and sky click speaks", () => {
  const state = garden(3);
  state.mode = "sky";
  const adam = findKind(state.world, "adam");
  state.world.entities.unshift({ id: "blocker", kind: "deer", x: adam.x + 0.2, y: adam.y, name: "" });
  const result = clickWorld(state, Math.floor(adam.x), Math.floor(adam.y), null);
  assert.equal(result.ok, true);
  assert.equal(state.talk.who, "adam");
  state.talk = null;
  enterWalk(state);
  const moved = clickWorld(state, 12, 28, null);
  assert.equal(moved.ok, false);
  tick(state, 0.016);
  assert.ok(state.breath > 70);
});

test("address chat, achievements, and field replies survive a save", () => {
  const absent = createNewGame(2);
  assert.equal(addressBeing(absent, "adam", "who are you").reason, "absent");

  const state = garden(12);
  assert.ok(state.achievements.includes("first_seed"));
  assert.ok(state.achievements.includes("seals7"));
  assert.equal(addressBeing(state, "serpent", "hello").reason, "absent");

  const who = addressBeing(state, "eve", "Who are you?");
  assert.equal(who.ok, true);
  assert.match(who.reply, /I am Eve/);
  assert.match(who.reply, /seals open/);
  const god = addressBeing(state, "adam", "Is that you, Elyon?");
  assert.match(god.reply, /Unity Thread/);
  const fruit = addressBeing(state, "eve", "What of the fruit of the tree?");
  assert.match(fruit.reply, /have not touched it/);
  assert.ok(state.achievements.includes("dialogue"));
  assert.equal(state.chat.length >= 5, true);

  const faithBefore = state.beings.adam.faith;
  const blessed = addressBeing(state, "adam", "bless us");
  assert.match(blessed.reply, /grateful/);
  assert.ok(state.beings.adam.faith > faithBefore);

  enterWalk(state);
  assert.ok(state.achievements.includes("walked"));
  enterSky(state);
  assert.ok(state.achievements.includes("walked"));

  state.thread.pop = 100;
  addressBeing(state, "adam", "the river is bright");
  assert.ok(state.achievements.includes("pop100"));

  const again = createNewGame(12);
  for (const id of ["light", "waters", "land", "grove", "lights", "creatures", "form_adam"]) performRitual(again, id);
  const first = addressBeing(again, "adam", "the river is bright").reply;
  const twin = createNewGame(12);
  for (const id of ["light", "waters", "land", "grove", "lights", "creatures", "form_adam"]) performRitual(twin, id);
  assert.equal(addressBeing(twin, "adam", "the river is bright").reply, first);

  const restored = normalize(serialize(state));
  assert.equal(restored.chat.at(-1).text, state.chat.at(-1).text);
  assert.ok(restored.achievements.includes("dialogue"));
  assert.ok(restored.achievements.includes("walked"));
  assert.equal(restored.address, "adam");
});

test("voice chat degrades when speech recognition is missing", () => {
  assert.deepEqual(voiceSupport({}), { speak: false, listen: false });
  assert.equal(speakText("peace", "eve", {}).reason, "no-tts");
  const missing = startListening({}, () => {}, () => {});
  assert.equal(missing.ok, false);
  assert.equal(missing.reason, "no-recognition");
  missing.stop();

  const thrown = speakText("peace", "adam", {
    speechSynthesis: {
      cancel() {},
      speak() {
        throw new Error("speech service unavailable");
      },
    },
    SpeechSynthesisUtterance: class {
      constructor(text) {
        this.text = text;
      }
    },
  });
  assert.equal(thrown.ok, false);
  assert.equal(thrown.reason, "no-tts");

  const spoken = [];
  const said = speakText("peace", "eve", {
    speechSynthesis: {
      cancel() {},
      speak(utter) {
        spoken.push(utter);
      },
    },
    SpeechSynthesisUtterance: class {
      constructor(text) {
        this.text = text;
      }
    },
  });
  assert.equal(said.ok, true);
  assert.equal(spoken[0].pitch, 1.15);
  assert.equal(spoken[0].rate, 0.95);

  let transcript = "";
  let ended = "";
  class FakeRecognition {
    start() {
      this.onresult({ results: [[{ transcript: "  who are you  " }]] });
    }
    stop() {
      this.onend();
    }
  }
  const session = startListening(
    { SpeechRecognition: FakeRecognition },
    (text) => {
      transcript = text;
    },
    (kind) => {
      ended = kind;
    },
  );
  assert.equal(session.ok, true);
  assert.equal(transcript, "who are you");
  session.stop();
  assert.equal(ended, "end");
});
