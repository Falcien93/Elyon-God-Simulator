/** DOM shell around the canvas. User text is never written as HTML. */

import { CODEX, SHAPES, BEAST_CYCLE } from "./content.js";
import {
  availableShapes,
  currentNode,
  currentObjective,
  derivedStats,
  formatLine,
  nearestTalkTarget,
  phaseName,
  primaryAction,
  visibleChoices,
} from "./sim.js";

let handlers = {};
let dockKey = "";
let talkKey = "";
let codexKey = "";
let journalKey = "";
let logKey = "";

export function mount(next) {
  handlers = next;
  on("btn-begin", "click", () => handlers.begin());
  on("btn-continue", "click", () => handlers.continue());
  on("btn-prologue", "click", () => handlers.finishPrologue());
  on("btn-resume", "click", () => handlers.resume());
  on("btn-fullscreen", "click", () => handlers.fullscreen());
  on("btn-export", "click", () => handlers.exportSave());
  on("btn-import", "click", () => document.getElementById("import-file").click());
  on("import-file", "change", (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) handlers.importSave(file);
  });
  on("btn-epilogue", "click", () => handlers.showEnding());
  on("btn-new", "click", () => handlers.requestNew());
  on("btn-title", "click", () => handlers.toTitle());
  on("btn-inscribe", "click", () => handlers.inscribe(document.getElementById("commandment").value));
  on("btn-silence", "click", () => handlers.silence());
  on("btn-voice-close", "click", () => handlers.closeOverlay());
  on("btn-codex-close", "click", () => handlers.closeOverlay());
  on("btn-journal-close", "click", () => handlers.closeOverlay());
  on("btn-help-close", "click", () => handlers.closeOverlay());
  on("btn-confirm-yes", "click", () => handlers.confirmYes());
  on("btn-confirm-no", "click", () => handlers.confirmNo());
  on("btn-remain", "click", () => handlers.remain());
  on("btn-ending-new", "click", () => handlers.requestNew());
  on("music", "input", (event) => handlers.volume("music", Number(event.target.value) / 100));
  on("sfx", "input", (event) => handlers.volume("sfx", Number(event.target.value) / 100));
  on("btn-keep-key", "click", () => handlers.keepKey(document.getElementById("xai-key").value));
  on("btn-forget-key", "click", () => handlers.forgetKey());
  on("btn-grok-send", "click", () => handlers.sendHear(document.getElementById("grok-input").value));
  on("btn-grok-close", "click", () => handlers.closeOverlay());
  on("grok-input", "keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handlers.sendHear(event.target.value);
    }
  });
}

export function setContinueEnabled(enabled) {
  const button = document.getElementById("btn-continue");
  button.disabled = !enabled;
}

export function sync(state, view) {
  document.body.dataset.screen = view.screen;
  show("screen-title", view.screen === "title");
  show("screen-prologue", view.screen === "prologue");
  show("screen-pause", view.pause);
  show("panel-confirm", Boolean(view.confirm));
  show("screen-ending", view.overlay === "ending");
  show("panel-help", view.overlay === "help");
  show("panel-codex", view.overlay === "codex");
  show("panel-journal", view.overlay === "journal");
  show("panel-voice", view.overlay === "voice");
  show("panel-grok", view.overlay === "grok");
  const talking = Boolean(state?.talk) && view.screen === "play" && !view.pause && !view.overlay && !view.confirm;
  show("panel-dialogue", talking);
  text("status", view.status || "");
  const toast = document.getElementById("toast");
  toast.hidden = !view.toast;
  text("toast", view.toast || "");
  if (!state || view.screen === "title") return;

  const objective = currentObjective(state);
  text("day-kicker", objective.numeral || "The garden");
  text("day-title", objective.title);
  text("quest-kicker", state.mode === "walk" ? "Among them" : "From the sky");
  text("quest-title", objective.title);
  text("quest-detail", objective.detail);
  text("phase", phaseName(state));
  const stats = derivedStats(state);
  for (const key of ["light", "life", "order", "wonder"]) {
    text(`val-${key}`, String(stats[key]));
    document.getElementById(`meter-${key}`).style.setProperty("--n", `${stats[key]}%`);
  }
  document.getElementById("breath-fill").style.width = `${Math.round(state.breath)}%`;
  document.getElementById("btn-epilogue").hidden = !state.ending;

  const lines = state.log.slice(-5);
  const nextLog = lines.join("|");
  if (nextLog !== logKey) {
    logKey = nextLog;
    const list = document.getElementById("log-list");
    list.replaceChildren();
    for (const line of lines) {
      const item = document.createElement("li");
      item.textContent = line;
      list.append(item);
    }
  }

  const shapes = availableShapes(state);
  const primary = primaryAction(state);
  const beast = BEAST_CYCLE[state.beastBrush % BEAST_CYCLE.length];
  const signature = `${primary.label}|${shapes.join()}|${view.tool}|${beast}|${state.mode}|${state.flags.eve_made ? 1 : 0}`;
  if (signature !== dockKey) {
    dockKey = signature;
    buildDock(state, view, primary, shapes, beast);
  }

  if (talking) buildTalk(state);
  if (view.overlay === "codex") buildCodex(state);
  if (view.overlay === "journal") buildJournal(state);
  if (view.overlay === "voice") buildVoice(state);
  if (view.overlay === "grok") {
    text("grok-who", view.hearName || "A living mind");
    text("grok-line", view.hearText || "");
  }
  if (view.confirm) text("confirm-text", view.confirm.text);
  if (view.overlay === "ending" && state.ending) {
    const ending = view.endingText;
    if (ending) {
      text("ending-title", ending.title);
      text("ending-a", ending.paragraphs[0]);
      text("ending-b", ending.paragraphs[1]);
    }
  }
}

function buildDock(state, view, primary, shapes, beast) {
  const primarySlot = document.getElementById("primary-slot");
  const shapeSlot = document.getElementById("shape-slot");
  const utilitySlot = document.getElementById("utility-slot");
  primarySlot.replaceChildren();
  shapeSlot.replaceChildren();
  utilitySlot.replaceChildren();

  const mainButton = button(primary.label, "primary");
  mainButton.id = "btn-primary";
  mainButton.addEventListener("click", () => handlers.primary());
  primarySlot.append(mainButton);

  for (const id of shapes) {
    const spec = SHAPES[id];
    const label = id === "beast" ? `Beast · ${beast}` : spec.label;
    const control = button(`${label} (${spec.hint})`);
    control.id = `shape-${id}`;
    control.setAttribute("aria-pressed", view.tool === id ? "true" : "false");
    control.addEventListener("click", () => handlers.tool(id));
    shapeSlot.append(control);
  }

  if (state.flags.ritual_land && state.mode === "sky" && primary.type !== "walk") {
    utilitySlot.append(actionButton("Descend", () => handlers.mode("walk")));
  }
  if (state.mode === "walk" && primary.type !== "sky") {
    utilitySlot.append(actionButton("Ascend", () => handlers.mode("sky")));
  }
  if (state.flags.eve_made) utilitySlot.append(actionButton("The word", () => handlers.openVoice()));
  if (state.flags.adam_made || state.flags.ritual_creatures) {
    utilitySlot.append(actionButton("Hear them", () => handlers.hear()));
  }
  utilitySlot.append(actionButton("Codex", () => handlers.openOverlay("codex")));
  utilitySlot.append(actionButton("Journal", () => handlers.openOverlay("journal")));
  utilitySlot.append(actionButton("Help", () => handlers.openOverlay("help")));
}

function buildTalk(state) {
  const node = currentNode(state);
  if (!node || !state.talk) return;
  const choices = visibleChoices(state, node);
  const key = `${state.talk.nodeId}:${state.talk.line}:${choices.map((choice) => choice.label).join("~")}`;
  if (key === talkKey) return;
  talkKey = key;
  const who = node.speaker;
  const portrait = document.getElementById("portrait");
  portrait.dataset.who = who;
  portrait.textContent = who === "serpent" ? "S" : (who === "eve" ? state.names.eve : state.names.adam).slice(0, 1);
  text("speaker-name", who === "serpent" ? "The serpent" : who === "eve" ? state.names.eve : state.names.adam);
  const rel = state.relations[who];
  text("speaker-meta", rel ? `Trust ${Math.round(rel.trust)} · Wonder ${Math.round(rel.wonder)}` : "A question with scales");
  text("line", formatLine(state, node.lines[state.talk.line] || ""));
  const slot = document.getElementById("choice-slot");
  slot.replaceChildren();
  const last = state.talk.line >= node.lines.length - 1;
  if (!last || node.next || (!node.input && choices.length === 0)) {
    const next = button(node.next && last ? "Continue" : "Continue", "primary");
    next.id = "btn-advance";
    next.addEventListener("click", () => handlers.advance());
    slot.append(next);
    return;
  }
  if (node.input) {
    const row = document.createElement("div");
    row.className = "row";
    const input = document.createElement("input");
    input.id = "talk-input";
    input.maxLength = node.input.max || 16;
    input.placeholder = node.input.placeholder || "A name";
    input.autocomplete = "off";
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        handlers.submit(input.value);
      }
    });
    const submit = button("Give the name", "primary");
    submit.addEventListener("click", () => handlers.submit(input.value));
    row.append(input, submit);
    slot.append(row);
    queueMicrotask(() => input.focus());
    return;
  }
  choices.forEach((choice, index) => {
    const control = button(formatLine(state, choice.label));
    control.id = `choice-${index}`;
    control.addEventListener("click", () => handlers.choose(index));
    slot.append(control);
  });
}

function buildCodex(state) {
  const key = state.codex.join("|");
  if (key === codexKey) return;
  codexKey = key;
  const list = document.getElementById("codex-list");
  list.replaceChildren();
  if (!state.codex.length) {
    const empty = document.createElement("p");
    empty.textContent = "Nothing has been revealed yet. Speak light.";
    list.append(empty);
    return;
  }
  for (const id of state.codex) {
    const entry = CODEX[id];
    if (!entry) continue;
    const article = document.createElement("article");
    const title = document.createElement("h3");
    const body = document.createElement("p");
    title.textContent = entry.title;
    body.textContent = entry.body;
    article.append(title, body);
    list.append(article);
  }
}

function buildJournal(state) {
  const key = `${state.log.length}:${state.log.at(-1) || ""}`;
  if (key === journalKey) return;
  journalKey = key;
  const list = document.getElementById("journal-list");
  list.replaceChildren();
  for (const line of state.log) {
    const item = document.createElement("li");
    item.textContent = line;
    list.append(item);
  }
}

function buildVoice(state) {
  const locked = Boolean(state.ending || state.flags.serpent_present || state.flags.serpent_gone);
  const fixed = document.getElementById("voice-fixed");
  const field = document.getElementById("commandment");
  fixed.hidden = !locked;
  field.hidden = locked;
  document.getElementById("btn-inscribe").hidden = locked;
  document.getElementById("btn-silence").hidden = locked;
  if (locked) {
    fixed.textContent = state.flags.silence
      ? "You kept silent. The silence has already gone out into the garden."
      : `You spoke: “${state.commandments[0] || ""}”`;
  }
}

export function resetPanels() {
  dockKey = "";
  talkKey = "";
  codexKey = "";
  journalKey = "";
  logKey = "";
}

export function nearestHint(state) {
  if (!state || state.mode !== "walk" || state.talk) return "";
  const near = nearestTalkTarget(state);
  if (!near) return "Click the ground to walk.";
  if (near.kind === "serpent") return "Press E to question the serpent.";
  const name = near.kind === "eve" ? state.names.eve : state.names.adam;
  return `Press E to speak with ${name}.`;
}

function actionButton(label, fn) {
  const control = button(label);
  control.addEventListener("click", fn);
  return control;
}

function button(label, kind) {
  const control = document.createElement("button");
  control.type = "button";
  control.textContent = label;
  if (kind) control.className = kind;
  return control;
}

function on(id, type, fn) {
  document.getElementById(id).addEventListener(type, fn);
}

function show(id, visible) {
  document.getElementById(id).hidden = !visible;
}

function text(id, value) {
  const node = document.getElementById(id);
  if (node.textContent !== value) node.textContent = value;
}
