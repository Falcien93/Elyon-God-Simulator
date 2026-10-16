/** Freeform address, the Unity Thread reading, and achievements. No DOM. */

export const AGES = ["Primordial", "Awakened", "Christos", "Unity"];

export const ACHIEVEMENTS = [
  { id: "first_seed", msg: "First Seed — Adam & Eve enter the field" },
  { id: "awakened", msg: "Awakened Age" },
  { id: "christos", msg: "Christos Age" },
  { id: "unity", msg: "Unity Age" },
  { id: "seals3", msg: "Three Seals Open" },
  { id: "seals7", msg: "All Seals Unsealed" },
  { id: "coherence50", msg: "Coherence 50%" },
  { id: "coherence100", msg: "Absolute Coherence" },
  { id: "pop100", msg: "100 Beings" },
  { id: "dialogue", msg: "Spoken with the First Beings" },
  { id: "walked", msg: "Walked Among Them" },
];

export const ACHIEVEMENT_IDS = new Set(ACHIEVEMENTS.map((item) => item.id));

const MOODS = ["peaceful", "curious", "grateful", "awake", "listening"];

export function emptyThread() {
  return {
    coherence: 18,
    cycle: 0,
    seals: 0,
    age: 0,
    pop: 2,
    faith: 30,
    sealsNoted: 0,
    beings: 0,
  };
}

export function emptyBeings() {
  return {
    adam: { mood: 62, faith: 40, lastWords: "" },
    eve: { mood: 64, faith: 42, lastWords: "" },
  };
}

export function ensureAddress(state) {
  if (!state.beings?.adam || !state.beings?.eve) state.beings = emptyBeings();
  if (!Array.isArray(state.chat)) state.chat = [];
  if (!Array.isArray(state.achievements)) state.achievements = [];
  if (state.address !== "adam" && state.address !== "eve") state.address = "adam";
  if (!state.thread) state.thread = emptyThread();
  return state;
}

export function sealCount(flags = {}) {
  return [
    flags.ritual_light,
    flags.ritual_waters,
    flags.ritual_land,
    flags.ritual_grove,
    flags.ritual_lights,
    flags.ritual_creatures,
    flags.adam_made && flags.eve_made,
  ].filter(Boolean).length;
}

export function livingBeings(flags = {}) {
  return (flags.adam_made ? 1 : 0) + (flags.eve_made ? 1 : 0);
}

function clamp(n, a, b) {
  return Math.max(a, Math.min(b, n));
}

function roll(state) {
  state.seed = (Math.imul(state.seed >>> 0, 1664525) + 1013904223) >>> 0;
  return state.seed / 4294967296;
}

/** Bring seals, age, and the being count in line with the garden. */
export function noteSealProgress(state) {
  ensureAddress(state);
  const seals = sealCount(state.flags);
  const noted = Number(state.thread.sealsNoted) || 0;
  if (seals > noted) {
    state.thread.coherence = clamp(state.thread.coherence + 6.5 * (seals - noted), 0, 100);
    state.thread.cycle += seals - noted;
    state.thread.sealsNoted = seals;
  }
  state.thread.seals = seals;
  state.thread.beings = livingBeings(state.flags);
  raiseAge(state);
  if (state.ending) {
    state.thread.coherence = Math.max(state.thread.coherence, 100);
    state.thread.seals = 7;
    state.thread.age = 3;
    state.thread.sealsNoted = Math.max(Number(state.thread.sealsNoted) || 0, 7);
  }
  return state.thread;
}

function raiseAge(state) {
  const thread = state.thread;
  if (thread.coherence > 30 && thread.age < 1) thread.age = 1;
  if (thread.coherence > 55 && thread.seals >= 3 && thread.age < 2) thread.age = 2;
  if (thread.coherence > 82 && thread.seals === 7 && thread.age < 3) thread.age = 3;
}

/** Slow field growth after the lights are set, so population can reach the old mark. */
export function advanceThread(state, dt) {
  ensureAddress(state);
  noteSealProgress(state);
  if (!state.flags?.ritual_lights) return state.thread;
  const step = clamp(Number(dt) || 0, 0, 0.05);
  const harmony = ((state.stats?.order ?? 48) + (state.stats?.wonder ?? 42)) / 2;
  const growthRate = 0.012 + state.thread.faith / 3200 + state.thread.coherence / 2800;
  state.thread.pop += state.thread.pop * growthRate * (harmony / 110) * step;
  state.thread.faith = clamp(state.thread.faith + (state.thread.coherence - 20) * 0.035 * step, 0, 100);
  raiseAge(state);
  return state.thread;
}

export function threadSummary(state) {
  ensureAddress(state);
  const thread = state.thread;
  const age = AGES[thread.age] || AGES[0];
  return `${age} age · Coherence ${Math.floor(thread.coherence)}% · Cycle ${Math.floor(thread.cycle)} · Population ${Math.floor(thread.pop)} · Faith ${Math.floor(thread.faith)} · Beings ${thread.beings} · Seals ${thread.seals} / 7`;
}

export function sanitizeChat(raw) {
  return String(raw ?? "")
    .replace(/[<>]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 240);
}

export function generateResponse(state, speaker, playerMsg) {
  ensureAddress(state);
  noteSealProgress(state);
  const being = state.beings[speaker];
  const coherence = state.thread.coherence;
  const lower = String(playerMsg).toLowerCase();
  const adam = state.names?.adam || "Adam";
  const eve = state.names?.eve || "Eve";
  const name = speaker === "eve" ? eve : adam;
  let reply = "";
  if (lower.includes("who") || lower.includes("what are you") || lower.includes("name")) {
    reply = speaker === "adam"
      ? `I am ${name}, formed from the dust and given breath. The garden is my charge.`
      : `I am ${name}, awakened beside ${adam}. The light and the living things speak to me.`;
  } else if (lower.includes("god") || lower.includes("elyon") || lower.includes("you")) {
    reply = coherence > 50
      ? "We feel your presence more clearly now. The Unity Thread hums when you speak."
      : "We hear a voice that is not the wind. Is that you, Elyon?";
  } else if (lower.includes("fruit") || lower.includes("tree") || lower.includes("eat")) {
    reply = "There is a tree whose fruit shines differently. We have not touched it... yet.";
  } else if (lower.includes("love") || lower.includes("together") || lower.includes("garden")) {
    reply = speaker === "eve"
      ? `${adam} walks beside me and the garden feels complete. Your blessing makes the flowers brighter.`
      : `${eve} and I tend the garden together. Harmony rises when we work side by side.`;
  } else if (lower.includes("why") || lower.includes("purpose") || lower.includes("exist")) {
    reply = coherence > 40
      ? "To know, to tend, to choose. The field grows more coherent when we listen."
      : "We do not yet know all reasons. The light guides us day by day.";
  } else if (lower.includes("bless") || lower.includes("thank") || lower.includes("help")) {
    being.mood = clamp(being.mood + 8, 0, 100);
    being.faith = clamp(being.faith + 4, 0, 100);
    reply = "Your words warm us. Faith and mood rise. We are grateful.";
  } else {
    const mood = MOODS[Math.floor(roll(state) * MOODS.length)];
    reply = speaker === "adam"
      ? `The garden is ${mood}. Cycle ${Math.floor(state.thread.cycle)}, coherence ${Math.floor(coherence)}%. I tend what you have given.`
      : `Everything feels ${mood}. The Unity Thread is at ${Math.floor(coherence)}%. I wonder what the next age will bring.`;
  }
  if (state.thread.seals > 0) reply += ` (${state.thread.seals} seals open.)`;
  being.lastWords = reply;
  return reply;
}

export function replyToBeing(state, who, raw) {
  ensureAddress(state);
  if (who !== "adam" && who !== "eve") return { ok: false, reason: "absent" };
  if (who === "adam" && !state.flags?.adam_made) return { ok: false, reason: "absent" };
  if (who === "eve" && !state.flags?.eve_made) return { ok: false, reason: "absent" };
  const text = sanitizeChat(raw);
  if (!text) return { ok: false, reason: "empty" };
  state.address = who;
  const reply = generateResponse(state, who, text);
  state.chat.push({ who: "elyon", text });
  state.chat.push({ who, text: reply });
  if (state.chat.length > 40) state.chat.splice(0, state.chat.length - 40);
  const being = state.beings[who];
  being.faith = clamp(being.faith + 1, 0, 100);
  being.mood = clamp(being.mood + 2, 0, 100);
  being.lastWords = reply;
  state.thread.faith = clamp(state.thread.faith + 1.5, 0, 100);
  state.thread.coherence = clamp(state.thread.coherence + 0.4, 0, 100);
  state.thread.cycle += 1;
  raiseAge(state);
  return { ok: true, reply, who };
}

export function collectNewAchievements(state) {
  ensureAddress(state);
  noteSealProgress(state);
  const thread = state.thread;
  const checks = [
    { id: "first_seed", cond: thread.beings >= 2 },
    { id: "awakened", cond: thread.age >= 1 },
    { id: "christos", cond: thread.age >= 2 },
    { id: "unity", cond: thread.age >= 3 },
    { id: "seals3", cond: thread.seals >= 3 },
    { id: "seals7", cond: thread.seals === 7 },
    { id: "coherence50", cond: thread.coherence >= 50 },
    { id: "coherence100", cond: thread.coherence >= 100 },
    { id: "pop100", cond: thread.pop >= 100 },
    { id: "dialogue", cond: state.chat.length >= 5 },
    { id: "walked", cond: Boolean(state.flags?.descended) || state.mode === "walk" },
  ];
  const fresh = [];
  for (const check of checks) {
    if (!check.cond || state.achievements.includes(check.id)) continue;
    state.achievements.push(check.id);
    const known = ACHIEVEMENTS.find((item) => item.id === check.id);
    fresh.push({ id: check.id, msg: known ? known.msg : check.id });
  }
  return fresh;
}

export function achievementText(state) {
  ensureAddress(state);
  return ACHIEVEMENTS.filter((item) => state.achievements.includes(item.id)).map((item) => item.msg);
}
