/** DOM shell around the canvas. User text is never written as HTML. */

import { achievementText, threadSummary } from "./converse.js";
import { CODEX, SHAPES, BEAST_CYCLE } from "./content.js";
import { slotLabel } from "./slots.js";
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
const slotKeys = { "slot-list": "", "pause-slots": "" };

export function mount(next) {
  handlers = next;
  on("btn-begin", "click", () => handlers.begin());
  on("btn-continue", "click", () => handlers.continue());
  on("btn-title-settings", "click", () => handlers.openSettings());
  on("btn-title-about", "click", () => handlers.openAbout());
  on("btn-pause-about", "click", () => handlers.openAbout());
  on("btn-about-close", "click", () => handlers.closeOverlay());
  on("btn-settings", "click", () => handlers.openSettings());
  on("btn-settings-close", "click", () => handlers.closeOverlay());
  on("master-volume", "input", (event) => handlers.setMaster(Number(event.target.value) / 100));
  on("opt-fullscreen", "change", (event) => handlers.setFullscreen(event.target.checked));
  on("opt-voice", "change", (event) => handlers.setVoice(event.target.checked));
  on("opt-living", "change", (event) => handlers.setLiving(event.target.checked));
  on("ollama-model", "change", (event) => handlers.setOllamaModel(event.target.value));
  on("whisper-base", "click", () => handlers.setWhisperSize("base"));
  on("whisper-small", "click", () => handlers.setWhisperSize("small"));
  on("speed-slow", "click", () => handlers.setTextSpeed("slow"));
  on("speed-normal", "click", () => handlers.setTextSpeed("normal"));
  on("speed-fast", "click", () => handlers.setTextSpeed("fast"));
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
  on("btn-address-close", "click", () => handlers.closeOverlay());
  on("btn-adam", "click", () => handlers.selectAddress("adam"));
  on("btn-eve", "click", () => handlers.selectAddress("eve"));
  on("btn-people", "click", () => handlers.selectAddress("people"));
  on("btn-send-chat", "click", () => handlers.sendAddress(document.getElementById("chat-input").value));
  on("chat-input", "keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      handlers.sendAddress(event.target.value);
    }
  });
  on("btn-speak-last", "click", () => handlers.speakLast());
  on("btn-voice-input", "click", () => handlers.toggleVoice());
  on("btn-codex-close", "click", () => handlers.closeOverlay());
  on("btn-journal-close", "click", () => handlers.closeOverlay());
  on("btn-help-close", "click", () => handlers.closeOverlay());
  on("btn-confirm-yes", "click", () => handlers.confirmYes());
  on("btn-confirm-no", "click", () => handlers.confirmNo());
  on("btn-remain", "click", () => handlers.remain());
  on("btn-ending-new", "click", () => handlers.requestNew());
  on("music", "input", (event) => handlers.volume("music", Number(event.target.value) / 100));
  on("sfx", "input", (event) => handlers.volume("sfx", Number(event.target.value) / 100));
}

export function setContinueEnabled(enabled) {
  const button = document.getElementById("btn-continue");
  button.disabled = !enabled;
}

export function sync(state, view) {
  document.body.dataset.screen = view.screen;
  show("screen-title", view.screen === "title");
  show("screen-prologue", view.screen === "prologue");
  show("screen-pause", view.pause && view.overlay !== "settings" && view.overlay !== "about");
  show("panel-settings", view.overlay === "settings");
  show("panel-about", view.overlay === "about");
  show("panel-confirm", Boolean(view.confirm));
  show("screen-ending", view.overlay === "ending");
  renderSlots("slot-list", view.library, "title");
  renderSlots("pause-slots", view.library, "pause");
  paintSettings(view);
  show("panel-help", view.overlay === "help");
  show("panel-codex", view.overlay === "codex");
  show("panel-journal", view.overlay === "journal");
  show("panel-voice", view.overlay === "voice");
  show("panel-address", view.overlay === "address");
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
  text("quest-achievements", state.achievements?.length ? `Achievements: ${state.achievements.length}` : "");
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
  const signature = `${primary.label}|${shapes.join()}|${view.tool}|${beast}|${state.mode}|${state.flags.adam_made ? 1 : 0}|${state.flags.eve_made ? 1 : 0}`;
  if (signature !== dockKey) {
    dockKey = signature;
    buildDock(state, view, primary, shapes, beast);
  }

  if (talking) buildTalk(state, view);
  if (view.overlay === "codex") buildCodex(state);
  if (view.overlay === "journal") buildJournal(state);
  if (view.overlay === "voice") buildVoice(state);
  if (view.overlay === "address") buildAddress(state, view);
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
  if (state.flags.adam_made) utilitySlot.append(actionButton("Address", () => handlers.openAddress()));
  if (state.flags.eve_made) utilitySlot.append(actionButton("The word", () => handlers.openVoice()));
  utilitySlot.append(actionButton("Codex", () => handlers.openOverlay("codex")));
  utilitySlot.append(actionButton("Journal", () => handlers.openOverlay("journal")));
  utilitySlot.append(actionButton("Help", () => handlers.openOverlay("help")));
}

function buildTalk(state, view) {
  const node = currentNode(state);
  if (!node || !state.talk) return;
  const choices = visibleChoices(state, node);
  const full = formatLine(state, node.lines[state.talk.line] || "");
  text("line", shownLine(full, view));
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

function shownLine(full, view) {
  if (!view?.settings || view.settings.textSpeed === "fast") return full;
  const count = Math.max(0, Math.floor(view.reveal || 0));
  if (count >= full.length) return full;
  return full.slice(0, count);
}

function renderSlots(id, library, mode) {
  const root = document.getElementById(id);
  if (!root || !library?.slots) return;
  const key = `${library.active}|${library.slots.map((slot) => slot?.savedAt || 0).join(",")}`;
  if (slotKeys[id] === key) return;
  slotKeys[id] = key;
  root.replaceChildren();
  for (let index = 0; index < library.slots.length; index += 1) {
    const slot = library.slots[index];
    const label = mode === "pause"
      ? `Save into garden ${index + 1}${slot ? ` · ${slotLabel(slot)}` : ""}`
      : (slot ? `Garden ${index + 1} · ${slotLabel(slot)}` : `Garden ${index + 1} · Empty`);
    const control = button(label);
    if (slot && library.active === index) control.setAttribute("aria-current", "true");
    control.addEventListener("click", () => {
      if (mode === "pause") handlers.saveSlot(index);
      else handlers.openSlot(index);
    });
    root.append(control);
  }
}

function paintSettings(view) {
  const settings = view?.settings;
  if (!settings) return;
  const master = document.getElementById("master-volume");
  if (master && document.activeElement !== master) {
    const next = String(Math.round(settings.master * 100));
    if (master.value !== next) master.value = next;
  }
  const fullscreen = document.getElementById("opt-fullscreen");
  if (fullscreen) fullscreen.checked = Boolean(settings.fullscreen);
  const voice = document.getElementById("opt-voice");
  if (voice) voice.checked = settings.voice !== false;
  for (const speed of ["slow", "normal", "fast"]) {
    const control = document.getElementById(`speed-${speed}`);
    if (control) control.setAttribute("aria-pressed", settings.textSpeed === speed ? "true" : "false");
  }
  const living = document.getElementById("opt-living");
  if (living) living.checked = settings.livingVoices === true;
  const model = document.getElementById("ollama-model");
  if (model && document.activeElement !== model && model.value !== settings.ollamaModel) {
    model.value = settings.ollamaModel || "llama3.2:3b";
  }
  for (const size of ["base", "small"]) {
    const control = document.getElementById(`whisper-${size}`);
    if (control) control.setAttribute("aria-pressed", settings.whisperSize === size ? "true" : "false");
  }
  const note = view.livingNote || "Off. Keyword replies and this window's voice stay in use until you turn Living Voices on.";
  const noteNode = document.getElementById("living-note");
  if (noteNode && noteNode.textContent !== note) noteNode.textContent = note;
  const progress = document.getElementById("living-progress");
  const bar = document.getElementById("living-progress-bar");
  const label = document.getElementById("living-progress-label");
  const showBar = Boolean(view.livingBusy);
  if (progress) progress.hidden = !showBar;
  if (bar) bar.style.width = `${Math.round(Math.max(0, Math.min(1, Number(view.livingFraction) || 0)) * 100)}%`;
  if (label && label.textContent !== (view.livingLabel || "")) label.textContent = view.livingLabel || "";
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

let addressKey = "";

function buildAddress(state, view) {
  text("thread-readout", threadSummary(state));
  const adamBtn = document.getElementById("btn-adam");
  const eveBtn = document.getElementById("btn-eve");
  adamBtn.setAttribute("aria-pressed", state.address === "adam" ? "true" : "false");
  eveBtn.disabled = !state.flags.eve_made;
  eveBtn.setAttribute("aria-pressed", state.address === "eve" ? "true" : "false");
  const peopleBtn = document.getElementById("btn-people");
  if (peopleBtn) {
    peopleBtn.disabled = !(state.flags.adam_made && state.flags.eve_made);
    peopleBtn.setAttribute("aria-pressed", state.address === "people" ? "true" : "false");
  }
  const voiceBtn = document.getElementById("btn-voice-input");
  voiceBtn.setAttribute("aria-pressed", view.listening ? "true" : "false");
  voiceBtn.textContent = view.listening ? "Stop voice" : "Voice";
  const earned = achievementText(state);
  text("address-achievements", earned.length ? earned.join(" · ") : "No achievements yet.");
  const key = state.chat.map((entry) => `${entry.who}:${entry.text}`).join("\n");
  if (key === addressKey) return;
  addressKey = key;
  const list = document.getElementById("chat-log");
  list.replaceChildren();
  if (!state.chat.length) {
    const empty = document.createElement("p");
    empty.className = "chat-line";
    empty.textContent = "Speak, and they will answer from the garden as it stands.";
    list.append(empty);
    return;
  }
  for (const entry of state.chat) {
    const line = document.createElement("p");
    line.className = `chat-line chat-${entry.who}`;
    const who = document.createElement("b");
    const label = entry.who === "elyon"
      ? "Elyon"
      : entry.who === "people"
        ? "The people"
        : entry.who === "eve"
          ? state.names.eve
          : state.names.adam;
    who.textContent = `${label}: `;
    line.append(who, document.createTextNode(entry.text));
    list.append(line);
  }
  list.scrollTop = list.scrollHeight;
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
  addressKey = "";
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
