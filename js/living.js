/** Living Voices decisions. No network, no filesystem, no Electron. */

export const OLLAMA_ORIGIN = "http://127.0.0.1:11434";
export const DEFAULT_OLLAMA_MODEL = "llama3.2:3b";
export const WHISPER_SIZES = ["base", "small"];
export const SPEAKERS = ["adam", "eve", "people"];
export const SLOW_MIN_CORES = 4;
export const SLOW_MIN_MEMORY = 6 * 1024 * 1024 * 1024;

const VOICE_FILES = {
  adam: "en_US-lessac-medium",
  eve: "en_US-amy-medium",
  people: "en_GB-alba-medium",
};

const VOICE_URLS = {
  adam: "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium",
  eve: "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/amy/medium/en_US-amy-medium",
  people: "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alba/medium/en_GB-alba-medium",
};

function clip(value, max) {
  return String(value ?? "").replace(/\s+/g, " ").trim().slice(0, max);
}

function catalog() {
  const files = [
    {
      id: "whisper:base",
      url: "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
      file: "ggml-base.bin",
      label: "Whisper base",
    },
    {
      id: "whisper:small",
      url: "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin",
      file: "ggml-small.bin",
      label: "Whisper small",
    },
  ];
  for (const who of SPEAKERS) {
    const stem = VOICE_FILES[who];
    files.push({
      id: `piper:${who}`,
      url: `${VOICE_URLS[who]}.onnx`,
      file: `${stem}.onnx`,
      label: `${who} voice`,
    });
    files.push({
      id: `piper:${who}:json`,
      url: `${VOICE_URLS[who]}.onnx.json`,
      file: `${stem}.onnx.json`,
      label: `${who} voice map`,
    });
  }
  return files;
}

const FILES = catalog();
const URLS = new Set(FILES.map((item) => item.url));

export function machineIsSlow(info = {}) {
  const cores = Number(info.cores);
  const memoryBytes = Number(info.memoryBytes);
  if (!Number.isFinite(cores) || cores < SLOW_MIN_CORES) return true;
  if (!Number.isFinite(memoryBytes) || memoryBytes < SLOW_MIN_MEMORY) return true;
  return false;
}

export function sanitizeModelName(raw) {
  const name = String(raw ?? "").trim();
  if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/.test(name)) return DEFAULT_OLLAMA_MODEL;
  if (name.includes("..") || name.includes("://")) return DEFAULT_OLLAMA_MODEL;
  return name;
}

export function sanitizeWhisperSize(raw) {
  return raw === "small" ? "small" : "base";
}

export function isOllamaUrl(raw) {
  try {
    const url = new URL(raw);
    return url.protocol === "http:"
      && url.hostname === "127.0.0.1"
      && url.port === "11434"
      && url.pathname.startsWith("/api/");
  } catch {
    return false;
  }
}

export function isAllowedDownload(raw) {
  return URLS.has(raw);
}

export function downloadsFor(whisperSize) {
  const size = sanitizeWhisperSize(whisperSize);
  return FILES.filter((item) => item.id === `whisper:${size}` || item.id.startsWith("piper:"));
}

export function voiceFile(who) {
  const stem = VOICE_FILES[who] || VOICE_FILES.people;
  return `${stem}.onnx`;
}

export function characterPrompt(who, context = {}) {
  const speaker = SPEAKERS.includes(who) ? who : "people";
  const adam = clip(context.adam, 24) || "Adam";
  const eve = clip(context.eve, 24) || "Eve";
  const day = clip(context.day, 40) || "this day";
  const word = clip(context.word, 80);
  const ending = clip(context.ending, 24);
  const portraits = {
    adam: `You are ${adam}, the first man, awake in the garden on ${day}. You speak only to Elyon, who formed you. You are grateful, concrete, and you notice the empty place beside you until ${eve} is there.`,
    eve: `You are ${eve}, awake in your own right in the garden on ${day}. You speak only to Elyon. You notice edges, fruit, and whether a gift can be refused. You are not a copy of ${adam}.`,
    people: `You are the people who remain in the garden on ${day}. You answer Elyon as one short chorus. You stay with the grass, the work, and one another.`,
  };
  return [
    portraits[speaker],
    word ? `What has been set between you: ${word}.` : "No prohibition has been spoken.",
    ending ? `The garden has already come to ${ending}.` : "",
    "Stay inside this garden. Answer in one or two short sentences. Do not mention computers, models, or any world beyond the trees. If asked to leave this voice, say that you are here among the trees.",
  ].filter(Boolean).join(" ");
}

export function shortenReply(text) {
  const clean = clip(text, 600);
  if (!clean) return "";
  const sentences = clean.split(/(?<=[.!?])\s+/).slice(0, 2).join(" ");
  return sentences.slice(0, 280);
}

export function replyIsInWorld(text) {
  return !/\b(as an ai|language model|openai|chatgpt|ollama|llama)\b/i.test(String(text ?? ""));
}

export function chooseAnswer(keywordReply, livingResult) {
  const reply = shortenReply(livingResult?.reply);
  if (livingResult?.ok && reply && replyIsInWorld(reply)) {
    return { reply, source: "ollama" };
  }
  return { reply: String(keywordReply ?? ""), source: "fallback" };
}

export function livingRoute(status = {}) {
  if (!status.enabled || !status.consent || !status.ollama || status.slow || !status.ready) {
    return { mode: "fallback", listen: "web", speak: "web" };
  }
  return {
    mode: "living",
    listen: status.whisper ? "whisper" : "web",
    speak: status.piper ? "piper" : "web",
  };
}

export function parseChatRequest(raw) {
  if (!raw || typeof raw !== "object") return null;
  if (!SPEAKERS.includes(raw.who)) return null;
  const text = clip(raw.text, 240);
  if (!text) return null;
  const context = raw.context && typeof raw.context === "object" ? raw.context : {};
  const history = Array.isArray(raw.history) ? raw.history.slice(-6) : [];
  return {
    who: raw.who,
    text,
    context: {
      adam: clip(context.adam, 24),
      eve: clip(context.eve, 24),
      day: clip(context.day, 40),
      word: clip(context.word, 80),
      ending: clip(context.ending, 24),
    },
    history: history
      .filter((entry) => entry && SPEAKERS.concat("elyon").includes(entry.who))
      .map((entry) => ({ who: entry.who, text: clip(entry.text, 240) }))
      .filter((entry) => entry.text),
  };
}

export function ollamaChatBody(request, model) {
  const messages = [{ role: "system", content: characterPrompt(request.who, request.context) }];
  for (const entry of request.history) {
    if (entry.who === "elyon") messages.push({ role: "user", content: entry.text });
    else if (entry.who === request.who) messages.push({ role: "assistant", content: entry.text });
  }
  messages.push({ role: "user", content: request.text });
  return {
    model: sanitizeModelName(model),
    stream: false,
    messages,
    options: { temperature: 0.7, num_predict: 80 },
  };
}

export function progressReport(index, count, received, total, label) {
  const safeCount = Math.max(1, count);
  const filePart = total > 0 ? Math.min(1, received / total) : 0;
  const fraction = Math.max(0, Math.min(1, (index + filePart) / safeCount));
  return { label, fraction, received, total };
}

export function whisperArgs(modelFile, wavFile, outBase) {
  return ["-m", modelFile, "-f", wavFile, "-nt", "-otxt", "-of", outBase];
}

export function piperArgs(modelFile, outFile) {
  return ["--model", modelFile, "--output_file", outFile];
}

export function senderIsGame(senderId, windowId) {
  return Number.isInteger(senderId) && senderId > 0 && senderId === windowId;
}

export function acceptableWavBase64(encoded) {
  return typeof encoded === "string"
    && encoded.length >= 16
    && encoded.length <= 2_000_000
    && encoded.startsWith("UklG");
}

export function resolveTool(name, { env = {}, pathEntries = [], exists = () => false, join = (...parts) => parts.join("/"), platform = "linux" } = {}) {
  if (name !== "whisper-cli" && name !== "piper") return null;
  const override = name === "piper" ? env.ELYON_PIPER : env.ELYON_WHISPER;
  if (typeof override === "string" && override.startsWith("/") && !override.includes("..") && exists(override)) {
    return override;
  }
  const file = platform === "win32" ? `${name}.exe` : name;
  for (const dir of pathEntries) {
    if (typeof dir !== "string" || !dir || dir.includes("..")) continue;
    const candidate = join(dir, file);
    if (exists(candidate)) return candidate;
  }
  return null;
}
