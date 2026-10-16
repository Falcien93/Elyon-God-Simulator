import { createAudio } from "./audio.js";
import { ENDINGS } from "./content.js";
import { render, screenToWorld } from "./render.js";
import { clearLocal, loadBest, normalize, serialize, writeBest } from "./save.js";
import {
  REASONS,
  availableShapes,
  chooseSilence,
  chooseTalk,
  clickWorld,
  createNewGame,
  enterSky,
  enterWalk,
  movePlayer,
  performRitual,
  primaryAction,
  setCommandment,
  startDialogue,
  submitTalkInput,
  tick,
  advanceTalk,
  interact,
  addressBeing,
  selectAddress,
} from "./sim.js";
import { speakText, startListening } from "./voice.js";
import { WORLD_H, WORLD_W } from "./world.js";
import { mount, nearestHint, resetPanels, setContinueEnabled, sync } from "./ui.js";

const canvas = document.getElementById("view");
const ctx = canvas.getContext("2d");
const audio = createAudio();

const preview = createNewGame(11);
for (const id of ["light", "waters", "land", "grove", "lights", "creatures"]) performRitual(preview, id);

let state = null;
let live = false;
const view = {
  screen: "title",
  pause: false,
  overlay: null,
  confirm: null,
  tool: null,
  status: "",
  statusUntil: 0,
  toast: "",
  toastUntil: 0,
  endingText: null,
  listening: false,
  voiceWarned: false,
};

let camX = WORLD_W / 2;
let camY = WORLD_H / 2;
let zoom = 1;
let hover = null;
let drag = null;
let flash = 0;
let last = 0;
let cssW = 1;
let cssH = 1;
const keys = new Set();
let reported = false;
let listener = null;

function stopListening() {
  if (listener) listener.stop();
  listener = null;
  view.listening = false;
}

function sendAddressMessage(text) {
  if (!state) return;
  const result = addressBeing(state, state.address, text);
  if (!result.ok) {
    applyResult(result);
    return;
  }
  const input = document.getElementById("chat-input");
  if (input) input.value = "";
  applyResult(result);
  const voice = speakText(result.reply, result.who, window);
  if (!voice.ok && !view.voiceWarned) {
    view.voiceWarned = true;
    setStatus("Spoken voice is not available here. The reply is in the address log.");
  }
  resetPanels();
}

mount({
  begin() {
    state = createNewGame((Date.now() ^ Math.floor(Math.random() * 1e9)) >>> 0 || 1);
    live = true;
    view.screen = "prologue";
    view.pause = false;
    view.overlay = null;
    view.tool = null;
    resetPanels();
    writeBest(state);
  },
  async continue() {
    const saved = await loadBest();
    if (!saved) {
      setStatus("No record was found on this computer.");
      setContinueEnabled(false);
      return;
    }
    adopt(saved);
  },
  finishPrologue() {
    if (!state) return;
    state.flags.seen_intro = true;
    view.screen = "play";
    resetPanels();
    writeBest(state);
    audio.resume();
  },
  resume() {
    view.pause = false;
  },
  fullscreen() {
    toggleFullscreen();
  },
  exportSave() {
    if (!state) return;
    const blob = new Blob([serialize(state)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "elyon-save.json";
    link.click();
    URL.revokeObjectURL(url);
  },
  importSave(file) {
    const reader = new FileReader();
    reader.onload = () => {
      const next = normalize(String(reader.result || ""));
      if (!next) {
        setStatus("That record could not be read.");
        return;
      }
      adopt(next);
      writeBest(state);
      setToast("The record is restored.");
    };
    reader.readAsText(file);
  },
  showEnding() {
    if (!state?.ending) return;
    view.pause = false;
    openEnding();
  },
  requestNew() {
    view.confirm = {
      text: "Begin a new creation? The garden on this computer will be replaced. Export a record first if you want to keep it.",
      action: "new",
    };
  },
  toTitle() {
    if (state && live) writeBest(state);
    view.pause = false;
    view.overlay = null;
    view.confirm = null;
    view.screen = "title";
    live = false;
  },
  primary() {
    if (!state) return;
    const action = primaryAction(state);
    if (action.confirm) {
      view.confirm = { text: `${action.label}?`, action: "primary" };
      return;
    }
    runPrimary(action);
  },
  tool(id) {
    view.tool = view.tool === id ? null : id;
    resetPanels();
  },
  mode(next) {
    if (!state) return;
    applyResult(next === "walk" ? enterWalk(state) : enterSky(state));
    zoom = 1;
  },
  openVoice() {
    view.overlay = "voice";
  },
  openAddress() {
    if (!state?.flags.adam_made) return;
    stopListening();
    view.overlay = "address";
    resetPanels();
  },
  selectAddress(who) {
    if (!state) return;
    applyResult(selectAddress(state, who));
  },
  sendAddress(text) {
    sendAddressMessage(text);
  },
  speakLast() {
    if (!state) return;
    const being = state.beings?.[state.address];
    const words = being?.lastWords;
    if (!words) {
      setStatus("They have not answered yet.");
      return;
    }
    const voice = speakText(words, state.address, window);
    if (!voice.ok) setStatus("Spoken voice is not available here. The reply is in the address log.");
  },
  toggleVoice() {
    if (!state) return;
    if (listener) {
      stopListening();
      setStatus("Voice stopped.");
      return;
    }
    const session = startListening(
      window,
      (transcript) => {
        const input = document.getElementById("chat-input");
        if (input) input.value = transcript;
        sendAddressMessage(transcript);
      },
      (kind) => {
        listener = null;
        view.listening = false;
        if (kind === "error") setStatus("Voice recognition stopped. Type to Adam or Eve instead.");
      },
    );
    if (!session.ok) {
      setStatus("Voice input is not available in this window. Type to Adam or Eve instead.");
      return;
    }
    listener = session;
    view.listening = true;
    setStatus("Listening. Speak now.");
  },
  openOverlay(name) {
    view.overlay = name;
  },
  closeOverlay() {
    stopListening();
    view.overlay = null;
  },
  inscribe(text) {
    applyResult(setCommandment(state, text));
    if (state.flags.commandment_spoken || state.flags.silence) view.overlay = null;
  },
  silence() {
    applyResult(chooseSilence(state));
    if (state.flags.silence) view.overlay = null;
  },
  confirmYes() {
    const action = view.confirm?.action;
    view.confirm = null;
    if (action === "new") {
      state = createNewGame((Date.now() ^ Math.floor(Math.random() * 1e9)) >>> 0 || 1);
      live = true;
      view.screen = "prologue";
      view.pause = false;
      view.overlay = null;
      view.tool = null;
      resetPanels();
      clearLocal();
      writeBest(state);
    } else if (action === "primary") {
      runPrimary(primaryAction(state));
    }
  },
  confirmNo() {
    view.confirm = null;
  },
  advance() {
    if (!state?.talk) return;
    applyResult(advanceTalk(state));
    resetPanels();
  },
  choose(index) {
    applyResult(chooseTalk(state, index));
    resetPanels();
  },
  submit(text) {
    applyResult(submitTalkInput(state, text));
    resetPanels();
  },
  remain() {
    if (!state) return;
    state.flags.ending_seen = true;
    view.overlay = null;
    writeBest(state);
  },
  volume(channel, value) {
    if (!state) return;
    state.settings[channel] = value;
    audio.setVolumes(state.settings.music, state.settings.sfx);
  },
});

function adopt(next) {
  state = next;
  live = true;
  view.pause = false;
  view.overlay = null;
  view.confirm = null;
  view.tool = null;
  view.screen = next.flags.seen_intro ? "play" : "prologue";
  document.getElementById("music").value = String(Math.round(next.settings.music * 100));
  document.getElementById("sfx").value = String(Math.round(next.settings.sfx * 100));
  audio.setVolumes(next.settings.music, next.settings.sfx);
  resetPanels();
  if (next.ending && !next.flags.ending_seen && view.screen === "play") openEnding();
}

function runPrimary(action) {
  if (action.type === "ritual") applyResult(performRitual(state, action.id));
  else if (action.type === "walk") applyResult(enterWalk(state));
  else if (action.type === "sky") applyResult(enterSky(state));
  zoom = action.type === "walk" || action.type === "sky" ? 1 : zoom;
  resetPanels();
}

function applyResult(result) {
  if (!result) return;
  if (!result.ok) {
    if (result.reason && result.reason !== "empty" && result.reason !== "bounds") {
      setStatus(REASONS[result.reason] || "That did not take.");
    }
    return;
  }
  if (result.cue) audio.cue(result.cue);
  if (result.flash) flash = result.flash;
  announce(result.day, result.achievements);
  if (state?.ending && !state.flags.ending_seen && !state.talk) openEnding();
}

function announce(day, achievements) {
  const notes = (achievements || []).map((item) => item.msg);
  if (day?.evening && notes.length) setToast(`${day.evening} Achievement: ${notes.join(" · ")}`);
  else if (day?.evening) setToast(day.evening);
  else if (notes.length) setToast(`Achievement: ${notes.join(" · ")}`);
}

function openEnding() {
  view.endingText = ENDINGS[state.ending.id] || null;
  view.overlay = "ending";
}

function setStatus(message) {
  view.status = message;
  view.statusUntil = performance.now() + 3200;
}

function setToast(message) {
  view.toast = message;
  view.toastUntil = performance.now() + 4200;
}

function toggleFullscreen() {
  if (window.elyonDesktop?.toggleFullscreen) {
    window.elyonDesktop.toggleFullscreen();
    return;
  }
  if (!document.fullscreenElement) document.documentElement.requestFullscreen?.();
  else document.exitFullscreen?.();
}

function resize() {
  cssW = window.innerWidth;
  cssH = window.innerHeight;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.max(1, Math.floor(cssW * dpr));
  canvas.height = Math.max(1, Math.floor(cssH * dpr));
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function frameMetrics(subject) {
  const walk = subject?.mode === "walk";
  const tile = walk
    ? 70 * zoom
    : Math.max(8, Math.min(cssW / WORLD_W, (cssH - 150) / WORLD_H) * zoom);
  return { w: cssW, h: cssH, tile, camX, camY, hover, now: performance.now(), flash, mode: subject?.mode };
}

function placeCamera(subject, dt) {
  const metrics = frameMetrics(subject);
  if (!subject || subject.mode !== "walk") {
    if (zoom <= 1.01) {
      camX = WORLD_W / 2;
      camY = WORLD_H / 2 + 0.4;
    }
  } else {
    const targetX = subject.player.x;
    const targetY = subject.player.y + 1.05;
    const blend = 1 - Math.exp(-7 * dt);
    camX += (targetX - camX) * blend;
    camY += (targetY - camY) * blend;
  }
  const halfW = cssW / metrics.tile / 2;
  const halfH = cssH / metrics.tile / 2;
  if (halfW * 2 >= WORLD_W) camX = WORLD_W / 2;
  else camX = clamp(camX, halfW, WORLD_W - halfW);
  if (halfH * 2 >= WORLD_H) camY = WORLD_H / 2;
  else camY = clamp(camY, halfH, WORLD_H - halfH);
}

function clamp(n, a, b) {
  return Math.max(a, Math.min(b, n));
}

function playing() {
  return live && state && view.screen === "play" && !view.pause && !view.confirm;
}

window.addEventListener("resize", resize);
resize();

canvas.addEventListener("pointerdown", (event) => {
  if (event.button !== 0) return;
  audio.resume();
  drag = { x: event.clientX, y: event.clientY, camX, camY, moved: false };
});

canvas.addEventListener("pointermove", (event) => {
  const metrics = frameMetrics(live ? state : preview);
  const world = screenToWorld(event.clientX, event.clientY, metrics);
  hover = { x: Math.floor(world.x), y: Math.floor(world.y) };
  if (!drag) return;
  if (Math.hypot(event.clientX - drag.x, event.clientY - drag.y) > 6) {
    drag.moved = true;
    const metricsNow = frameMetrics(live ? state : preview);
    if (zoom > 1 || (live && state?.mode === "walk")) {
      camX = drag.camX - (event.clientX - drag.x) / metricsNow.tile;
      camY = drag.camY - (event.clientY - drag.y) / metricsNow.tile;
    }
  }
});

window.addEventListener("pointerup", (event) => {
  if (!drag) return;
  const moved = drag.moved;
  drag = null;
  if (moved || !playing() || view.overlay) return;
  const metrics = frameMetrics(state);
  const world = screenToWorld(event.clientX, event.clientY, metrics);
  const tx = Math.floor(world.x);
  const ty = Math.floor(world.y);
  applyResult(clickWorld(state, tx, ty, state.mode === "sky" ? view.tool : null));
  resetPanels();
});

canvas.addEventListener("wheel", (event) => {
  event.preventDefault();
  const walk = live && state?.mode === "walk";
  const min = walk ? 0.85 : 1;
  const max = walk ? 1.4 : 2.4;
  zoom = clamp(zoom + (event.deltaY > 0 ? -0.08 : 0.08), min, max);
}, { passive: false });

canvas.addEventListener("contextmenu", (event) => event.preventDefault());

window.addEventListener("keydown", (event) => {
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
    if (event.key === "Escape") event.target.blur();
    return;
  }
  keys.add(event.code);
  if (event.code === "Space") event.preventDefault();
  if (event.key === "Escape") {
    if (view.confirm) view.confirm = null;
    else if (view.overlay) {
      stopListening();
      view.overlay = null;
    }
    else if (state?.talk && view.screen === "play") {
      state.talk = null;
      resetPanels();
    } else if (view.screen === "play") view.pause = !view.pause;
    else if (view.screen === "prologue") handlersFallbackPrologue();
    return;
  }
  if (!playing() || view.overlay) return;
  if (event.key === "e" || event.key === "E") {
    if (state.talk) applyResult(advanceTalk(state));
    else applyResult(interact(state));
    resetPanels();
  } else if (event.key === "m" || event.key === "M") {
    applyResult(state.mode === "walk" ? enterSky(state) : enterWalk(state));
    zoom = 1;
  } else if (event.key === "h" || event.key === "H") view.overlay = "help";
  else if (event.key === "f" || event.key === "F") toggleFullscreen();
  else if (event.key === "Enter" || event.code === "Space") {
    if (state.talk) {
      applyResult(advanceTalk(state));
      resetPanels();
    }
  } else if (/^[1-8]$/.test(event.key) && state.mode === "sky") {
    const shapes = availableShapes(state);
    const next = shapes[Number(event.key) - 1];
    if (next) {
      view.tool = next;
      resetPanels();
    }
  }
});

window.addEventListener("keyup", (event) => keys.delete(event.code));
window.addEventListener("blur", () => keys.clear());

function handlersFallbackPrologue() {
  if (state) {
    state.flags.seen_intro = true;
    view.screen = "play";
    writeBest(state);
  }
}

window.addEventListener("pointerdown", () => audio.resume(), { once: false });

function loop(now) {
  requestAnimationFrame(loop);
  const dt = Math.min(0.05, last ? (now - last) / 1000 : 0);
  last = now;
  try {
    if (view.screen === "title") tick(preview, dt);
    if (playing() && !view.overlay) {
      const beat = tick(state, dt);
      if (beat) announce(beat.day, beat.achievements);
      if (!state.talk && state.mode === "walk") steer(dt);
      if (state.ending && !state.flags.ending_seen && !state.talk && !view.overlay) openEnding();
    }
    if (view.status && now > view.statusUntil) view.status = "";
    if (!view.status && playing() && !view.overlay) view.status = nearestHint(state);
    if (view.toast && now > view.toastUntil) view.toast = "";
    flash = Math.max(0, flash - dt * 0.8);
    const subject = view.screen === "title" || !state ? preview : state;
    placeCamera(subject, dt);
    const metrics = frameMetrics(subject);
    metrics.camX = camX;
    metrics.camY = camY;
    render(ctx, subject, metrics);
    sync(state, view);
  } catch (error) {
    if (!reported) {
      reported = true;
      setStatus(error instanceof Error ? error.message : "The garden stumbled.");
    }
  }
}

function steer(dt) {
  let x = 0;
  let y = 0;
  if (keys.has("KeyW") || keys.has("ArrowUp")) y -= 1;
  if (keys.has("KeyS") || keys.has("ArrowDown")) y += 1;
  if (keys.has("KeyA") || keys.has("ArrowLeft")) x -= 1;
  if (keys.has("KeyD") || keys.has("ArrowRight")) x += 1;
  if (x || y) {
    state.dest = null;
    movePlayer(state, x, y, dt);
  }
}

setInterval(() => {
  if (live && state && view.screen === "play") writeBest(state);
}, 5000);

document.addEventListener("visibilitychange", () => {
  if (document.hidden && live && state) writeBest(state);
});
window.addEventListener("beforeunload", () => {
  if (live && state) writeBest(state);
});

loadBest().then((saved) => {
  setContinueEnabled(Boolean(saved));
});

requestAnimationFrame(loop);
