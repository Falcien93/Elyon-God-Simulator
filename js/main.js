import { createAudio } from "./audio.js";
import { ENDINGS } from "./content.js";
import { converse, forgetKey, getKey, liveMoment, missingKeyLine, setKey } from "./grok.js";
import { lookBy, orbitBy, pick, render, resize as resizeView, walkAxes, zoomBy } from "./render.js";
import { clearLocal, loadBest, normalize, serialize, writeBest } from "./save.js";
import {
  REASONS,
  applyMind,
  applyMoments,
  availableShapes,
  chooseSilence,
  chooseTalk,
  clickWorld,
  createNewGame,
  enterSky,
  enterWalk,
  hearTarget,
  movePlayer,
  performRitual,
  primaryAction,
  setCommandment,
  startDialogue,
  submitTalkInput,
  tick,
  advanceTalk,
  interact,
} from "./sim.js";
import { WORLD_H, WORLD_W } from "./world.js";
import { mount, nearestHint, resetPanels, setContinueEnabled, sync } from "./ui.js";

const canvas = document.getElementById("view");
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
  openOverlay(name) {
    view.overlay = name;
  },
  closeOverlay() {
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
  keepKey(value) {
    setKey(value);
    setToast(getKey() ? "The key stays on this computer, outside the garden record." : "No key was kept.");
  },
  forgetKey() {
    forgetKey();
    const field = document.getElementById("xai-key");
    if (field) field.value = "";
    setToast("The key is forgotten. The garden record is unchanged.");
  },
  hear() {
    if (!state) return;
    const target = hearTarget(state);
    if (!target) {
      setStatus("No one is awake to hear you yet.");
      return;
    }
    openHear(target.hear, target.id);
  },
  async sendHear(text) {
    if (!state || !view.hear) return;
    const line = String(text || "");
    if (!getKey()) {
      view.hearText = missingKeyLine();
      return;
    }
    view.hearText = "They are listening…";
    const reply = await converse(state, view.hear.kind, line);
    if (!reply.missingKey) applyMind(state, view.hear.kind, { ...reply, id: view.hear.id }, line);
    view.hearText = reply.speech || missingKeyLine();
    const field = document.getElementById("grok-input");
    if (field && reply.ok) field.value = "";
    resetPanels();
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

function openHear(kind, id) {
  const person = state.world.entities.find((entity) => entity.id === id);
  const name = kind === "adam" ? state.names.adam : kind === "eve" ? state.names.eve : person?.name || kind;
  view.hear = { kind, id };
  view.hearName = name;
  view.hearText = getKey() ? `${name} is here. Speak, and they will answer from the life they believe is theirs.` : missingKeyLine();
  view.overlay = "grok";
  resetPanels();
}

function applyResult(result) {
  if (!result) return;
  if (result.ok && result.hear) openHear(result.hear, result.id);
  if (!result.ok) {
    if (result.reason && result.reason !== "empty" && result.reason !== "bounds") {
      setStatus(REASONS[result.reason] || "That did not take.");
    }
    return;
  }
  if (result.cue) audio.cue(result.cue);
  if (result.flash) flash = result.flash;
  if (result.day) setToast(result.day.evening);
  if (state?.ending && !state.flags.ending_seen && !state.talk) openEnding();
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
  resizeView(cssW, cssH);
}

function frameMetrics(subject) {
  const walk = subject?.mode === "walk";
  const tile = walk
    ? 70 * zoom
    : Math.max(8, Math.min(cssW / WORLD_W, (cssH - 150) / WORLD_H) * zoom);
  return { w: cssW, h: cssH, tile, camX, camY, hover, now: performance.now(), flash, mode: subject?.mode };
}

function placeCamera() {
  /* The 3D camera lives in the renderer. */
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
  const world = pick(event.clientX, event.clientY);
  hover = world ? { x: world.x, y: world.y } : null;
  if (!drag) return;
  const dx = event.clientX - drag.x;
  const dy = event.clientY - drag.y;
  if (Math.hypot(dx, dy) > 6) {
    drag.moved = true;
    drag.x = event.clientX;
    drag.y = event.clientY;
    const subject = live ? state : preview;
    if (subject?.mode === "walk") lookBy(dx, dy);
    else orbitBy(dx, dy);
  }
});

window.addEventListener("pointerup", (event) => {
  if (!drag) return;
  const moved = drag.moved;
  drag = null;
  if (moved || !playing() || view.overlay) return;
  const world = pick(event.clientX, event.clientY);
  if (!world) return;
  applyResult(clickWorld(state, world.x, world.y, state.mode === "sky" ? view.tool : null));
  resetPanels();
});

canvas.addEventListener("wheel", (event) => {
  event.preventDefault();
  const subject = live ? state : preview;
  zoomBy(event.deltaY, subject?.mode);
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
    else if (view.overlay) view.overlay = null;
    else if (state?.talk && view.screen === "play") {
      state.talk = null;
      resetPanels();
    } else if (view.screen === "play") {
      view.pause = !view.pause;
      if (view.pause) {
        const field = document.getElementById("xai-key");
        if (field && !field.value) field.value = getKey();
      }
    } else if (view.screen === "prologue") handlersFallbackPrologue();
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
      const day = tick(state, dt);
      if (day) setToast(day.evening);
      if (!state.talk && state.mode === "walk") steer(dt);
      if (state.ending && !state.flags.ending_seen && !state.talk && !view.overlay) openEnding();
    }
    if (view.status && now > view.statusUntil) view.status = "";
    if (!view.status && playing() && !view.overlay) view.status = nearestHint(state);
    if (view.toast && now > view.toastUntil) view.toast = "";
    flash = Math.max(0, flash - dt * 0.8);
    const subject = view.screen === "title" || !state ? preview : state;
    placeCamera();
    const metrics = frameMetrics(subject);
    render(canvas, subject, metrics);
    maybeLife(now);
    sync(state, view);
  } catch (error) {
    if (!reported) {
      reported = true;
      setStatus(error instanceof Error ? error.message : "The garden stumbled.");
    }
  }
}

let lifeAt = 0;
let lifeBusy = false;

function maybeLife(now) {
  if (!playing() || view.overlay || !state?.flags?.ritual_light || !getKey() || lifeBusy) return;
  if (now - lifeAt < 24000) return;
  lifeAt = now;
  lifeBusy = true;
  liveMoment(state).then((moments) => {
    applyMoments(state, moments);
  }).finally(() => {
    lifeBusy = false;
  });
}

function steer(dt) {
  const axes = walkAxes();
  let x = 0;
  let y = 0;
  if (keys.has("KeyW") || keys.has("ArrowUp")) {
    x += axes.fx;
    y += axes.fy;
  }
  if (keys.has("KeyS") || keys.has("ArrowDown")) {
    x -= axes.fx;
    y -= axes.fy;
  }
  if (keys.has("KeyA") || keys.has("ArrowLeft")) {
    x -= axes.rx;
    y -= axes.ry;
  }
  if (keys.has("KeyD") || keys.has("ArrowRight")) {
    x += axes.rx;
    y += axes.ry;
  }
  if (x || y) {
    state.dest = null;
    movePlayer(state, x, y, dt);
    state.player.facing = Math.abs(axes.fx) > Math.abs(axes.fy) ? (axes.fx > 0 ? "e" : "w") : axes.fy > 0 ? "s" : "n";
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
