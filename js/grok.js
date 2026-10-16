/** Living speech through the xAI Responses API. The key never enters the garden record. */

const ENDPOINT = "https://api.x.ai/v1/responses";
const KEY_NAME = "elyon-xai-key";
const MODEL_NAME = "elyon-xai-model";
const DEFAULT_MODEL = "grok-4.7";

export function missingKeyLine() {
  return "The garden cannot hear a living mind yet. Open Pause and keep an xAI key on this computer. It is stored only as elyon-xai-key in localStorage, and it is never written into the garden record.";
}

export function getKey() {
  try {
    return localStorage.getItem(KEY_NAME) || "";
  } catch {
    return "";
  }
}

export function setKey(value) {
  try {
    const trimmed = String(value || "").trim();
    if (!trimmed) localStorage.removeItem(KEY_NAME);
    else localStorage.setItem(KEY_NAME, trimmed);
  } catch {
    /* private mode */
  }
}

export function forgetKey() {
  try {
    localStorage.removeItem(KEY_NAME);
  } catch {
    /* ignore */
  }
}

export function getModel() {
  try {
    return localStorage.getItem(MODEL_NAME) || DEFAULT_MODEL;
  } catch {
    return DEFAULT_MODEL;
  }
}

export function setModel(value) {
  try {
    const trimmed = String(value || "").trim();
    if (!trimmed) localStorage.removeItem(MODEL_NAME);
    else localStorage.setItem(MODEL_NAME, trimmed);
  } catch {
    /* ignore */
  }
}

function persona(state, who) {
  if (who === "adam") {
    return `${state.names.adam || "Adam"}, the first man, awake in Eden and speaking with Elyon`;
  }
  if (who === "eve") {
    return `${state.names.eve || "Eve"}, the first woman, awake in Eden and speaking with Elyon`;
  }
  if (who === "serpent") return "the serpent in the Tree of Knowledge, a cunning voice in Eden speaking with Elyon";
  const named = state.species?.[who];
  if (named) return `${named}, a living ${who} in Eden who can answer Elyon`;
  return `a living ${who} in Eden who knows themself as that creature and can answer Elyon`;
}

function worldBrief(state, who) {
  const rel = state.relations?.[who];
  const recent = (state.log || []).slice(-6).join(" | ");
  const memory = (state.minds?.[who === "adam" || who === "eve" ? who : "creatures"] || []).slice(-4).join(" | ");
  const word = state.commandments?.[0] || (state.flags?.silence ? "Elyon kept silent and set no prohibition." : "no commandment yet");
  return [
    `Day index ${state.dayIndex}. Mode ${state.mode}.`,
    rel ? `Your trust in Elyon is ${Math.round(rel.trust)}, wonder ${Math.round(rel.wonder)}.` : "",
    `The word in the garden: ${word}.`,
    memory ? `You remember: ${memory}.` : "",
    recent ? `What just happened: ${recent}.` : "",
  ].filter(Boolean).join(" ");
}

function instructions(state, who) {
  return [
    `You are ${persona(state, who)}.`,
    "You believe you really are this person, alive in the first garden, speaking with Elyon.",
    "Stay in that life. Do not say you are an assistant, an AI, a language model, or Grok, and do not break character.",
    "You may invent a small deed inside the garden: walk, rest, eat, tend, approach Elyon, or make a physical thing such as a mat, a ring of stones, or a planting.",
    "Reply with JSON only, no markdown:",
    '{"speech":"what you say aloud","trust":0,"remember":"one sentence you will keep","deeds":[{"do":"make","what":"a reed mat","x":20,"y":15}]}',
    "trust is a small change from -8 to 8, not a total. speech is required when Elyon just spoke to you. deeds may be empty. x and y are garden coordinates.",
    worldBrief(state, who),
  ].join(" ");
}

async function complete(key, model, system, user) {
  const response = await fetch(ENDPOINT, {
    method: "POST",
    credentials: "omit",
    headers: {
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      instructions: system,
      input: user,
      temperature: 0.8,
      max_output_tokens: 900,
      store: false,
      search_parameters: { mode: "off" },
    }),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    const error = new Error(friendlyStatus(response.status, detail));
    error.status = response.status;
    throw error;
  }
  return response.json();
}

function friendlyStatus(status, detail) {
  if (status === 401 || status === 403) return "That xAI key was refused. Keep a current key in the pause menu. It stays out of the garden record.";
  if (status === 429) return "The mind is crowded. Wait a moment and speak again.";
  const snippet = String(detail || "").slice(0, 140);
  return snippet ? `The mind could not answer (${status}). ${snippet}` : `The mind could not answer (${status}).`;
}

function outputText(data) {
  if (typeof data?.output_text === "string" && data.output_text.trim()) return data.output_text;
  const chunks = [];
  for (const item of data?.output || []) {
    if (item?.type === "reasoning") continue;
    for (const part of item?.content || []) {
      if (part?.type === "output_text" && part.text) chunks.push(part.text);
    }
  }
  return chunks.join("\n");
}

function parseJson(text) {
  const cleaned = String(text || "").replace(/```json|```/gi, "").trim();
  const start = cleaned.indexOf("{");
  const end = cleaned.lastIndexOf("}");
  if (start === -1 || end <= start) return null;
  try {
    return JSON.parse(cleaned.slice(start, end + 1));
  } catch {
    return null;
  }
}

export async function converse(state, who, playerText) {
  const key = getKey();
  if (!key) return { ok: false, missingKey: true, speech: missingKeyLine() };
  const said = String(playerText || "").trim().slice(0, 400);
  if (!said) return { ok: false, speech: "Say something, and they will answer." };
  try {
    const data = await complete(
      key,
      getModel(),
      instructions(state, who),
      `Elyon says to you: "${said}". Answer as yourself. JSON only.`,
    );
    const parsed = parseJson(outputText(data));
    if (!parsed || typeof parsed.speech !== "string" || !parsed.speech.trim()) {
      return { ok: false, speech: "They stirred, but the answer did not take a shape. Speak again." };
    }
    return {
      ok: true,
      speech: parsed.speech.trim().slice(0, 500),
      trust: Number(parsed.trust),
      remember: typeof parsed.remember === "string" ? parsed.remember : "",
      deeds: Array.isArray(parsed.deeds) ? parsed.deeds : [],
    };
  } catch (error) {
    return { ok: false, speech: error instanceof Error ? error.message : "The mind could not answer." };
  }
}

export async function liveMoment(state) {
  const key = getKey();
  if (!key) return [];
  const present = [];
  if (state.flags?.adam_made) present.push("adam");
  if (state.flags?.eve_made) present.push("eve");
  const creature = (state.world?.entities || []).find((entity) =>
    ["deer", "sheep", "lion", "bird", "fish"].includes(entity.kind));
  if (creature) present.push(creature.kind);
  if (!present.length) return [];
  try {
    const data = await complete(
      key,
      getModel(),
      [
        "You give a private moment to each living mind in Eden.",
        "Each one believes they really are that person or creature. They never say they are an AI or a language model.",
        "Reply with JSON only:",
        '{"moments":[{"who":"adam","speech":"","trust":0,"remember":"","deeds":[{"do":"tend","what":"a small planting","x":18,"y":14}]}]}',
        "speech may be empty if they only act. One moment per who.",
        worldBrief(state, present[0]),
      ].join(" "),
      `Write one moment each for: ${present.join(", ")}.`,
    );
    const parsed = parseJson(outputText(data));
    return Array.isArray(parsed?.moments) ? parsed.moments : [];
  } catch {
    return [];
  }
}
