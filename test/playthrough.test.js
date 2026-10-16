import assert from "node:assert/strict";
import test from "node:test";
import { DAYS } from "../js/content.js";
import { normalize, serialize } from "../js/save.js";
import {
  advanceTalk,
  chooseSilence,
  chooseTalk,
  createNewGame,
  currentNode,
  dialogueEntry,
  drawNear,
  enterWalk,
  formatLine,
  linePending,
  performRitual,
  primaryAction,
  setCommandment,
  startDialogue,
} from "../js/sim.js";

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

function follow(state) {
  const action = primaryAction(state);
  if (action.type === "ritual") return performRitual(state, action.id);
  if (action.type === "walk") return enterWalk(state);
  if (action.type === "talk") return startDialogue(state, action.who);
  if (action.type === "near") return drawNear(state);
  return { ok: false, reason: action.type };
}

function nameBeastsFromHub(state) {
  assert.equal(startDialogue(state, "adam").ok, true);
  pump(state);
  assert.equal(currentNode(state).id, "adam_hub_unnamed");
  assert.equal(chooseTalk(state, 0).ok, true);
  pump(state);
  for (const id of ["adam_name_deer", "adam_name_sheep", "adam_name_lion"]) {
    assert.equal(currentNode(state).id, id);
    assert.equal(chooseTalk(state, 0).ok, true);
    pump(state);
  }
  assert.equal(currentNode(state).id, "adam_named_done");
  assert.equal(state.flags.beasts_named, true);
  assert.equal(chooseTalk(state, 0).ok, true);
  assert.equal(state.talk, null);
}

function gardenToChoice(seed, { silence }) {
  const state = createNewGame(seed);
  const days = ["light", "waters", "land", "grove", "lights", "creatures"];
  for (const id of days) {
    assert.equal(primaryAction(state).id, id);
    const result = follow(state);
    assert.equal(result.ok, true, id);
  }
  assert.equal(performRitual(state, "grove").reason, "already");
  assert.equal(state.dayIndex, 6);

  assert.equal(primaryAction(state).id, "form_adam");
  assert.equal(performRitual(state, "form_adam").ok, true);
  assert.equal(primaryAction(state).type, "walk");
  assert.notEqual(primaryAction(state).type, "sky");
  assert.equal(follow(state).ok, true);
  assert.equal(state.mode, "walk");
  const speak = primaryAction(state);
  assert.equal(speak.type, "talk");
  assert.equal(speak.who, "adam");
  assert.equal(follow(state).ok, true);
  pump(state);
  assert.equal(currentNode(state).id, "adam_first");
  assert.equal(chooseTalk(state, 0).ok, true);
  pump(state);
  assert.equal(state.flags.adam_asked_companion, true);
  assert.equal(chooseTalk(state, 2).ok, true);
  assert.equal(state.talk, null);

  assert.equal(primaryAction(state).id, "form_eve");
  assert.equal(performRitual(state, "form_eve").ok, true);
  assert.equal(state.dayIndex, 7);
  assert.equal(DAYS[state.dayIndex].id, "rest");
  assert.equal(state.mode, "walk");
  assert.equal(primaryAction(state).type, "near");
  let draws = 0;
  while (state.dayIndex < 8 && draws < 4) {
    assert.equal(primaryAction(state).type, "near");
    assert.equal(drawNear(state).ok, true);
    draws += 1;
  }
  assert.equal(state.dayIndex, 8);
  assert.equal(state.flags.rest_adam, true);
  assert.equal(state.flags.rest_eve, true);
  assert.equal(drawNear(state).reason, "locked");

  const naming = primaryAction(state);
  assert.equal(naming.type, "talk");
  assert.equal(naming.who, "adam");
  assert.equal(follow(state).ok, true);
  pump(state);
  assert.equal(chooseTalk(state, 0).ok, true);
  pump(state);
  for (const id of ["adam_name_deer", "adam_name_sheep", "adam_name_lion"]) {
    assert.equal(currentNode(state).id, id);
    assert.equal(chooseTalk(state, 0).ok, true);
    pump(state);
  }
  assert.equal(state.flags.beasts_named, true);
  assert.equal(chooseTalk(state, 0).ok, true);

  assert.equal(primaryAction(state).type, "word");
  if (silence) assert.equal(chooseSilence(state).ok, true);
  else assert.equal(setCommandment(state, "Do not eat of the tree of knowledge.").ok, true);
  assert.equal(state.flags.serpent_present, true);

  const greet = primaryAction(state);
  assert.equal(greet.type, "talk");
  assert.equal(greet.who, "eve");
  assert.equal(follow(state).ok, true);
  pump(state);
  assert.equal(currentNode(state).id, "eve_first");
  assert.equal(chooseTalk(state, 2).ok, true);
  assert.equal(state.flags.eve_greeted, true);
  assert.equal(dialogueEntry(state, "eve"), "eve_choice");
  assert.equal(primaryAction(state).who, "eve");
  assert.equal(startDialogue(state, "eve").ok, true);
  pump(state);
  assert.equal(currentNode(state).id, "eve_choice");
  return state;
}

test("gold action plays every day and will not skip ahead", () => {
  const state = createNewGame(21);
  assert.equal(performRitual(state, "form_adam").reason, "locked");
  assert.equal(state.dayIndex, 0);
  const stateAtChoice = gardenToChoice(21, { silence: false });
  assert.equal(stateAtChoice.dayIndex, 8);
  assert.equal(currentNode(stateAtChoice).id, "eve_choice");
  assert.equal(state.dayIndex, 0);
});

test("walk mode after Adam speaks with him instead of ascending", () => {
  const state = createNewGame(3);
  for (const id of ["light", "waters", "land", "grove", "lights", "creatures", "form_adam"]) {
    assert.equal(performRitual(state, id).ok, true);
  }
  assert.equal(enterWalk(state).ok, true);
  const action = primaryAction(state);
  assert.deepEqual(
    { type: action.type, who: action.who },
    { type: "talk", who: "adam" },
  );
});

test("naming early does not replace the rest-day gold action", () => {
  const state = createNewGame(9);
  for (const id of ["light", "waters", "land", "grove", "lights", "creatures", "form_adam"]) {
    performRitual(state, id);
  }
  assert.equal(startDialogue(state, "adam").ok, true);
  pump(state);
  chooseTalk(state, 0);
  state.talk = null;
  assert.equal(performRitual(state, "form_eve").ok, true);
  nameBeastsFromHub(state);
  assert.equal(state.dayIndex, 7);
  assert.equal(primaryAction(state).type, "walk");
  assert.equal(enterWalk(state).ok, true);
  assert.equal(primaryAction(state).type, "near");
});

test("all four endings follow the gold action", () => {
  const paths = [
    { id: "harmony", silence: false, choice: 0 },
    { id: "exile", silence: false, choice: 1 },
    { id: "order", silence: false, choice: 2 },
    { id: "wonder", silence: true, choice: 1 },
  ];
  for (const path of paths) {
    const state = gardenToChoice(40 + path.choice + (path.silence ? 10 : 0), { silence: path.silence });
    assert.equal(state.ending, null);
    assert.equal(chooseTalk(state, path.choice).ok, true, path.id);
    assert.equal(state.ending.id, path.id);
    assert.equal(state.flags.serpent_gone, true);
  }
});

test("an unread line finishes before the next line or its choices", () => {
  const state = createNewGame(5);
  for (const id of ["light", "waters", "land", "grove", "lights", "creatures", "form_adam"]) {
    performRitual(state, id);
  }
  enterWalk(state);
  assert.equal(startDialogue(state, "adam").ok, true);
  const full = formatLine(state, currentNode(state).lines[0]);
  assert.equal(linePending(state, 0, "normal"), true);
  assert.equal(linePending(state, full.length - 1, "slow"), true);
  assert.equal(linePending(state, full.length, "normal"), false);
  assert.equal(linePending(state, 0, "fast"), false);
  assert.equal(linePending({ talk: null }, 0, "normal"), false);

  assert.equal(state.talk.line, 0);
  assert.equal(chooseTalk(state, 0).reason, "locked");
  assert.equal(linePending(state, 1e9, "normal"), false);
  assert.equal(state.talk.line, 0);
  assert.equal(advanceTalk(state).ok, true);
  assert.equal(state.talk.line, 1);
  const last = formatLine(state, currentNode(state).lines[1]);
  assert.equal(linePending(state, 0, "normal"), true);
  assert.equal(linePending(state, last.length, "normal"), false);
});

test("a save with an unknown ending id loads without that ending", () => {
  const state = createNewGame(6);
  performRitual(state, "light");
  const raw = JSON.parse(serialize(state));
  raw.ending = { id: "bogus", at: 12 };
  const dropped = normalize(raw);
  assert.equal(dropped.ending, null);
  raw.ending = { id: "harmony", at: 12 };
  const kept = normalize(raw);
  assert.equal(kept.ending.id, "harmony");
});
