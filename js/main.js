import { createAudio } from "./audio.js";
import { DAYS, ENDINGS } from "./content.js";
import { acceptAddress } from "./converse.js";
import { chooseAnswer, livingRoute, sanitizeModelName } from "./living.js";
import { encodeWav, wavToBase64 } from "./wav.js";
import { render, screenToWorld } from "./render.js";
import { STORAGE_KEY, normalize, serialize } from "./save.js";
import {
  LIBRARY_KEY,
  SETTINGS_KEY,
  TEXT_SPEEDS,
  assembleLibrary,
  charsPerSecond,
  defaultSettings,
  emptyLibrary,
  normalizeSettings,
  pickSettings,
  readSlot,
  serializeLibrary,
  writeSlot,
} from "./slots.js";
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
import { RELEASE } from "./release.js";
import { mount, nearestHint, resetPanels, setContinueEnabled, sync } from "./ui.js";

const canvas = document.getElementById("view");
const ctx = canvas.getContext("2d");
const audio = createAudio();

const preview = createNewGame(11);
for (const id of ["light", "waters", "land", "grove", "lights", "creatures"]) performRitual(preview, id);

let state = null;
let live = false;
let library = emptyLibrary();
let settings = defaultSettings();
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
  library,
  settings,
  reveal: 0,
  talkSig: "",
  livingNote: "",
  livingBusy: false,
  livingFraction: 0,
  livingLabel: "",
  livingOllama: false,
  livingSlow: false,
  livingWhisper: false,
  livingPiper: false,
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

async function beginListening() {
  if (!state) return;
  if (settings.voice === false) {
    setStatus("Voice is off. Turn it on in Settings.");
    return;
  }
  if (listener) {
    stopListening();
    setStatus("Voice stopped.");
    return;
  }
  if (currentRoute().listen === "whisper") {
    const heard = await startWhisperListen();
    if (heard) return;
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
      if (kind === "error") setStatus("Voice recognition stopped. Type to Adam, Eve, or the people instead.");
    },
  );
  if (!session.ok) {
    setStatus("Voice input is not available in this window. Type to Adam, Eve, or the people instead.");
    return;
  }
  listener = session;
  view.listening = true;
  setStatus("Listening. Speak now.");
}

async function startWhisperListen() {
  const desktop = window.elyonDesktop;
  if (!desktop?.voicesTranscribe || !navigator.mediaDevices?.getUserMedia) return false;
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    return false;
  }
  const context = new AudioContext({ sampleRate: 16000 });
  const source = context.createMediaStreamSource(stream);
  const processor = context.createScriptProcessor(4096, 1, 1);
  const chunks = [];
  let samples = 0;
  const maxSamples = 16000 * 8;
  processor.onaudioprocess = (event) => {
    const data = event.inputBuffer.getChannelData(0);
    const copy = new Float32Array(data);
    chunks.push(copy);
    samples += copy.length;
    if (samples >= maxSamples) stopListening();
  };
  source.connect(processor);
  processor.connect(context.destination);
  view.listening = true;
  listener = {
    stop() {
      processor.onaudioprocess = null;
      processor.disconnect();
      source.disconnect();
      stream.getTracks().forEach((track) => track.stop());
      context.close();
      const merged = new Float32Array(Math.min(samples, maxSamples));
      let offset = 0;
      for (const chunk of chunks) {
        const take = Math.min(chunk.length, merged.length - offset);
        if (take <= 0) break;
        merged.set(chunk.subarray(0, take), offset);
        offset += take;
      }
      transcribeWav(merged);
    },
  };
  setStatus("Listening. Speak now.");
  return true;
}

async function transcribeWav(samples) {
  view.listening = false;
  listener = null;
  if (!samples?.length) {
    setStatus("Nothing was heard. Type instead.");
    return;
  }
  const desktop = window.elyonDesktop;
  try {
    const encoded = wavToBase64(encodeWav(samples, 16000));
    const heard = await withTimeout(desktop.voicesTranscribe(encoded), 25000);
    if (heard?.ok && heard.text) {
      const input = document.getElementById("chat-input");
      if (input) input.value = heard.text;
      sendAddressMessage(heard.text);
      return;
    }
  } catch {
    /* keyword path stays available by typing */
  }
  setStatus("Local hearing did not catch that. Type instead.");
}

async function turnLiving(on) {
  if (!on) {
    settings.livingVoices = false;
    settings.livingConsent = false;
    view.livingBusy = false;
    view.livingNote = "Keyword replies and this window's voice stay in use.";
    view.settings = settings;
    commitSettings();
    return;
  }
  const desktop = window.elyonDesktop;
  if (!desktop?.voicesStatus) {
    settings.livingVoices = false;
    view.livingNote = "Living Voices runs in the desktop app. This window keeps keyword replies and Web Speech.";
    view.settings = settings;
    commitSettings();
    return;
  }
  view.livingBusy = true;
  view.livingLabel = "Checking this computer…";
  view.livingNote = "Checking whether Ollama is on this computer.";
  let status = null;
  try {
    status = await withTimeout(desktop.voicesStatus(settings.whisperSize), 4000);
  } catch {
    status = null;
  }
  view.livingBusy = false;
  if (!status || status.slow || !status.ollama) {
    settings.livingVoices = false;
    view.livingSlow = Boolean(status?.slow);
    view.livingOllama = Boolean(status?.ollama);
    view.livingNote = !status
      ? "Living Voices could not start. Keyword replies and Web Speech stay in use."
      : status.slow
        ? "This computer is too small for local voices. Keyword replies and Web Speech stay in use."
        : "Ollama is not running on this computer. Keyword replies and Web Speech stay in use.";
    view.settings = settings;
    commitSettings();
    return;
  }
  const size = settings.whisperSize === "small" ? "small" : "base";
  view.confirm = {
    action: "living",
    text: `Living Voices will download the Whisper ${size} model, Piper voices for Adam, Eve, and the people, and ask Ollama for ${settings.ollamaModel}. The files stay on this computer. The game does not include them. Enable them?`,
  };
}

async function enableLiving() {
  const desktop = window.elyonDesktop;
  if (!desktop?.voicesPrepare) {
    settings.livingVoices = false;
    settings.livingConsent = false;
    view.livingNote = "Living Voices runs in the desktop app. This window keeps keyword replies and Web Speech.";
    commitSettings();
    return;
  }
  settings.livingConsent = true;
  settings.livingVoices = true;
  view.livingBusy = true;
  view.livingFraction = 0;
  view.livingLabel = "Preparing local voices…";
  view.settings = settings;
  commitSettings();
  let result = null;
  try {
    result = await withTimeout(desktop.voicesPrepare({
      consent: true,
      model: settings.ollamaModel,
      whisperSize: settings.whisperSize,
    }), 480000);
  } catch {
    result = null;
  }
  view.livingBusy = false;
  if (!result?.ok) {
    settings.livingVoices = false;
    settings.livingConsent = false;
    view.livingOllama = false;
    view.livingNote = result?.reason === "slow"
      ? "This computer is too small for local voices. Keyword replies and Web Speech stay in use."
      : result?.reason === "ollama"
        ? "Ollama is not running on this computer. Keyword replies and Web Speech stay in use."
        : "The local voices could not be prepared. Keyword replies and Web Speech stay in use.";
    view.settings = settings;
    commitSettings();
    return;
  }
  view.livingOllama = true;
  view.livingSlow = false;
  view.livingWhisper = Boolean(result.whisper);
  view.livingPiper = Boolean(result.piper);
  view.livingFraction = 1;
  view.livingLabel = "Ready";
  view.livingNote = result.whisper && result.piper
    ? "Living Voices is on. Speech, replies, and spoken lines stay on this computer."
    : "Living Voices is on for replies. Hearing and speaking use this window when Whisper or Piper is not installed.";
  view.settings = settings;
  commitSettings();
}

async function refreshLivingStatus() {
  const desktop = window.elyonDesktop;
  if (!desktop?.voicesStatus || !settings.livingVoices || !settings.livingConsent) return;
  try {
    const status = await withTimeout(desktop.voicesStatus(settings.whisperSize), 4000);
    view.livingOllama = Boolean(status?.ollama);
    view.livingSlow = Boolean(status?.slow);
    view.livingWhisper = Boolean(status?.whisper);
    view.livingPiper = Boolean(status?.piper);
    if (status?.slow || !status?.ollama) {
      view.livingNote = status?.slow
        ? "This computer is too small for local voices. Keyword replies and Web Speech stay in use."
        : "Ollama is not running on this computer. Keyword replies and Web Speech stay in use.";
    }
  } catch {
    view.livingOllama = false;
    view.livingNote = "Ollama is not running on this computer. Keyword replies and Web Speech stay in use.";
  }
}

function addressContext() {
  const day = DAYS[state.dayIndex];
  return {
    adam: state.names?.adam || "",
    eve: state.names?.eve || "",
    day: day?.title || "",
    word: state.commandments?.[0] || (state.flags?.silence ? "silence" : ""),
    ending: state.ending?.id || "",
  };
}

function currentRoute() {
  return livingRoute({
    enabled: settings.livingVoices === true,
    consent: settings.livingConsent === true,
    ollama: view.livingOllama === true,
    slow: view.livingSlow === true,
    ready: settings.livingVoices === true && settings.livingConsent === true,
    whisper: view.livingWhisper === true,
    piper: view.livingPiper === true,
  });
}

async function sendAddressMessage(text) {
  if (!state) return;
  const who = state.address;
  const desktop = window.elyonDesktop;
  let living = null;
  if (settings.livingVoices && settings.livingConsent && desktop?.voicesChat && currentRoute().mode === "living") {
    try {
      living = await withTimeout(desktop.voicesChat({
        who,
        text,
        context: addressContext(),
        history: state.chat.slice(-6),
        model: settings.ollamaModel,
      }), 20000);
    } catch {
      living = null;
    }
  }
  const chosen = chooseAnswer("", living);
  const result = chosen.source === "ollama"
    ? acceptAddress(state, who, text, chosen.reply)
    : addressBeing(state, who, text);
  if (!result.ok) {
    applyResult(result);
    return;
  }
  const input = document.getElementById("chat-input");
  if (input) input.value = "";
  applyResult(result);
  if (settings.voice === false) {
    resetPanels();
    return;
  }
  await speakReply(result.reply, result.who);
  resetPanels();
}

async function speakReply(words, who) {
  if (!words) return;
  const desktop = window.elyonDesktop;
  if (currentRoute().speak === "piper" && desktop?.voicesSpeak) {
    try {
      const spoken = await withTimeout(desktop.voicesSpeak({ who, text: words }), 20000);
      if (spoken?.ok && spoken.wavBase64 && await playWavBase64(spoken.wavBase64)) return true;
    } catch {
      /* the window voice still reads the line */
    }
  }
  const voice = speakText(words, who, window);
  if (!voice.ok && !view.voiceWarned) {
    view.voiceWarned = true;
    setStatus("Spoken voice is not available here. The reply is in the address log.");
  }
  return voice.ok;
}

async function playWavBase64(encoded) {
  try {
    const binary = atob(encoded);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    const context = new AudioContext();
    const buffer = await context.decodeAudioData(bytes.buffer.slice(0));
    const node = context.createBufferSource();
    node.buffer = buffer;
    node.connect(context.destination);
    node.onended = () => context.close();
    node.start();
    return true;
  } catch {
    return false;
  }
}

mount({
  begin() {
    const empty = library.slots.findIndex((slot) => !slot);
    if (empty >= 0) {
      startInSlot(empty);
      return;
    }
    view.confirm = {
      text: "All three gardens are written. Begin again in the active one? Export a record first if you want to keep it.",
      action: "new",
      slot: library.active,
    };
  },
  continue() {
    resumeGarden();
  },
  openSlot(index) {
    openGarden(index);
  },
  saveSlot(index) {
    if (!state) return;
    writeSlot(library, index, state);
    view.library = library;
    persistLibrary();
    setToast(`Saved into garden ${index + 1}.`);
  },
  openSettings() {
    view.overlay = "settings";
  },
  openAbout() {
    view.overlay = "about";
  },
  setMaster(value) {
    settings.master = value;
    view.settings = settings;
    audio.setMaster(settings.master);
    if (state?.settings) audio.setVolumes(state.settings.music, state.settings.sfx);
    commitSettings();
  },
  setFullscreen(on) {
    settings.fullscreen = Boolean(on);
    view.settings = settings;
    applyFullscreen(settings.fullscreen);
    commitSettings();
  },
  setTextSpeed(speed) {
    if (!TEXT_SPEEDS.includes(speed)) return;
    settings.textSpeed = speed;
    view.settings = settings;
    if (speed === "fast") view.reveal = 1e9;
    commitSettings();
  },
  setVoice(on) {
    settings.voice = Boolean(on);
    view.settings = settings;
    if (!settings.voice) stopListening();
    commitSettings();
  },
  setLiving(on) {
    turnLiving(on);
  },
  setOllamaModel(name) {
    settings.ollamaModel = sanitizeModelName(name);
    if (settings.livingVoices) {
      settings.livingVoices = false;
      settings.livingConsent = false;
      view.livingNote = "The model changed. Turn Living Voices on again so this computer can download it.";
    }
    view.settings = settings;
    commitSettings();
  },
  setWhisperSize(size) {
    const next = size === "small" ? "small" : "base";
    if (next === settings.whisperSize && !settings.livingVoices) return;
    settings.whisperSize = next;
    if (settings.livingVoices) {
      settings.livingVoices = false;
      settings.livingConsent = false;
      view.livingNote = "The Whisper size changed. Turn Living Voices on again so this computer can download it.";
    }
    view.settings = settings;
    commitSettings();
  },
  finishPrologue() {
    if (!state) return;
    state.flags.seen_intro = true;
    view.screen = "play";
    resetPanels();
    saveActive();
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
      saveActive();
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
    const empty = library.slots.findIndex((slot) => !slot);
    const index = library.slots[library.active] ? library.active : (empty >= 0 ? empty : library.active);
    view.confirm = {
      text: "Begin a new creation in this garden? Only this slot is replaced. The other gardens stay on this computer.",
      action: "new",
      slot: index,
    };
  },
  toTitle() {
    if (state && live) saveActive();
    view.pause = false;
    view.overlay = null;
    view.confirm = null;
    view.screen = "title";
    live = false;
    setContinueEnabled(library.slots.some(Boolean));
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
    if (settings.voice === false) {
      setStatus("Voice is off. Turn it on in Settings to hear them.");
      return;
    }
    speakReply(words, state.address).then((voiceOk) => {
      if (voiceOk === false) setStatus("Spoken voice is not available here. The reply is in the address log.");
    });
  },
  toggleVoice() {
    beginListening();
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
    const slot = Number.isInteger(view.confirm?.slot) ? view.confirm.slot : library.active;
    view.confirm = null;
    if (action === "new") {
      startInSlot(slot);
    } else if (action === "primary") {
      runPrimary(primaryAction(state));
    } else if (action === "living") {
      enableLiving();
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
    saveActive();
  },
  volume(channel, value) {
    if (!state) return;
    state.settings[channel] = value;
    audio.setMaster(settings.master);
    audio.setVolumes(state.settings.music, state.settings.sfx);
  },
});

function freshGame() {
  return createNewGame((Date.now() ^ Math.floor(Math.random() * 1e9)) >>> 0 || 1);
}

function startInSlot(index) {
  const slot = Math.max(0, Math.min(2, index));
  state = freshGame();
  live = true;
  view.screen = "prologue";
  view.pause = false;
  view.overlay = null;
  view.confirm = null;
  view.tool = null;
  resetPanels();
  writeSlot(library, slot, state);
  view.library = library;
  persistLibrary();
  audio.resume();
}

function openGarden(index) {
  const game = readSlot(library, index);
  if (!game) {
    startInSlot(index);
    return;
  }
  library.active = index;
  adopt(game);
  persistLibrary();
}

function resumeGarden() {
  let index = library.slots[library.active] ? library.active : -1;
  if (index < 0) {
    let best = -1;
    let stamp = -1;
    library.slots.forEach((slot, i) => {
      if (slot && (slot.savedAt || 0) >= stamp) {
        best = i;
        stamp = slot.savedAt || 0;
      }
    });
    index = best;
  }
  if (index < 0) {
    setStatus("No record was found on this computer.");
    setContinueEnabled(false);
    return;
  }
  openGarden(index);
}

function saveActive() {
  if (!state) return;
  const index = Number.isInteger(library.active) ? library.active : 0;
  writeSlot(library, index, state);
  view.library = library;
  persistLibrary();
}

function persistLibrary() {
  const text = serializeLibrary(library);
  view.library = library;
  try {
    if (typeof localStorage !== "undefined") localStorage.setItem(LIBRARY_KEY, text);
  } catch {
    /* ignore quota and private-mode failures */
  }
  const desktop = window.elyonDesktop;
  if (desktop?.writeLibrary) desktop.writeLibrary(text);
}

function commitSettings() {
  const next = normalizeSettings({ ...settings, version: 1 }) || defaultSettings();
  next.updatedAt = Date.now();
  settings = next;
  view.settings = settings;
  audio.setMaster(settings.master);
  try {
    if (typeof localStorage !== "undefined") localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch {
    /* ignore quota and private-mode failures */
  }
  const desktop = window.elyonDesktop;
  if (desktop?.writeSettings) desktop.writeSettings(JSON.stringify(settings));
}

function storageGet(key) {
  try {
    if (typeof localStorage === "undefined") return null;
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function withTimeout(promise, ms) {
  return Promise.race([
    promise,
    new Promise((_resolve, reject) => {
      setTimeout(() => reject(new Error("timeout")), ms);
    }),
  ]);
}

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
  audio.setMaster(settings.master);
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
  settings.fullscreen = !settings.fullscreen;
  view.settings = settings;
  applyFullscreen(settings.fullscreen);
  commitSettings();
}

function applyFullscreen(on) {
  const desktop = window.elyonDesktop;
  if (desktop?.setFullscreen) {
    desktop.setFullscreen(Boolean(on));
    return;
  }
  if (on) {
    if (!document.fullscreenElement) {
      const pending = document.documentElement.requestFullscreen?.();
      if (pending && typeof pending.catch === "function") pending.catch(() => {});
    }
  } else if (document.fullscreenElement) {
    const pending = document.exitFullscreen?.();
    if (pending && typeof pending.catch === "function") pending.catch(() => {});
  }
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
    saveActive();
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
      if (state.talk) {
        const sig = `${state.talk.nodeId}:${state.talk.line}`;
        if (sig !== view.talkSig) {
          view.talkSig = sig;
          view.reveal = settings.textSpeed === "fast" ? 1e9 : 0;
        } else if (settings.textSpeed !== "fast") {
          view.reveal += dt * charsPerSecond(settings.textSpeed);
        }
      }
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
  if (live && state && view.screen === "play") saveActive();
}, 5000);

document.addEventListener("visibilitychange", () => {
  if (document.hidden && live && state) saveActive();
});
window.addEventListener("beforeunload", () => {
  if (live && state) saveActive();
});

async function bootSaves() {
  let diskLibrary = null;
  let diskLegacy = null;
  let diskSettings = null;
  const desktop = window.elyonDesktop;
  if (desktop?.loadLibrary) {
    try {
      const payload = await withTimeout(desktop.loadLibrary(), 2500);
      diskLibrary = payload?.library || null;
      diskLegacy = payload?.legacy || null;
    } catch {
      diskLibrary = null;
      diskLegacy = null;
    }
  }
  if (desktop?.loadSettings) {
    try {
      diskSettings = await withTimeout(desktop.loadSettings(), 2500);
    } catch {
      diskSettings = null;
    }
  }
  library = assembleLibrary({
    diskText: diskLibrary,
    legacyText: diskLegacy,
    browserText: storageGet(LIBRARY_KEY),
    localText: storageGet(STORAGE_KEY),
  });
  view.library = library;
  setContinueEnabled(library.slots.some(Boolean));
  settings = pickSettings(normalizeSettings(diskSettings), normalizeSettings(storageGet(SETTINGS_KEY))) || defaultSettings();
  view.settings = settings;
  audio.setMaster(settings.master);
  if (settings.fullscreen && desktop?.setFullscreen) desktop.setFullscreen(true);
  if (desktop?.onVoicesProgress) {
    desktop.onVoicesProgress((report) => {
      if (!report || typeof report !== "object") return;
      const fraction = Number(report.fraction);
      view.livingFraction = Number.isFinite(fraction) ? Math.max(0, Math.min(1, fraction)) : 0;
      view.livingLabel = String(report.label || "").slice(0, 80);
      view.livingBusy = view.livingFraction < 1;
    });
  }
  persistLibrary();
  commitSettings();
  refreshLivingStatus();
}

bootSaves();
paintRelease();

requestAnimationFrame(loop);

function paintAbout(info) {
  const version = `Version ${info.version}`;
  const versionNode = document.getElementById("app-version");
  if (versionNode) versionNode.textContent = version;
  const aboutVersion = document.getElementById("about-version");
  if (aboutVersion) aboutVersion.textContent = version;
  const title = document.getElementById("about-title");
  if (title) title.textContent = info.name || RELEASE.name;
  const description = document.getElementById("about-description");
  if (description) description.textContent = info.description || RELEASE.description;
  const meta = document.getElementById("about-meta");
  if (meta) meta.textContent = `${info.license || RELEASE.license} · ${info.appId || RELEASE.appId} · not code-signed`;
}

async function paintRelease() {
  let info = RELEASE;
  const desktop = window.elyonDesktop;
  if (desktop?.getAbout) {
    try {
      const about = await desktop.getAbout();
      if (about && typeof about.version === "string") info = about;
    } catch {
      info = RELEASE;
    }
  }
  paintAbout(info);
  if (desktop?.onOpenAbout) {
    desktop.onOpenAbout(() => {
      view.overlay = "about";
    });
  }
}
