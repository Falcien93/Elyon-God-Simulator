/** Local Living Voices host. Models download only from the fixed catalog. No shell. */

import {
  DEFAULT_OLLAMA_MODEL,
  OLLAMA_ORIGIN,
  downloadsFor,
  isAllowedDownload,
  isOllamaUrl,
  livingRoute,
  machineIsSlow,
  ollamaChatBody,
  parseChatRequest,
  piperArgs,
  progressReport,
  resolveTool,
  sanitizeModelName,
  sanitizeWhisperSize,
  shortenReply,
  voiceFile,
  whisperArgs,
} from "../js/living.js";

function inside(osPath, root, target) {
  const base = osPath.resolve(root);
  const full = osPath.resolve(target);
  return full === base || full.startsWith(base + osPath.sep);
}

async function readStream(response, onChunk) {
  const reader = response.body?.getReader?.();
  if (!reader) return;
  let received = 0;
  for (;;) {
    const step = await reader.read();
    if (step.done) return received;
    const value = step.value || new Uint8Array();
    received += value.byteLength || value.length || 0;
    await onChunk(value, received);
  }
}

export function createLivingHost(deps) {
  const fetchImpl = deps.fetch;
  const osPath = deps.osPath;
  const disk = deps.fs;
  const onProgress = deps.onProgress || (() => {});
  let lastProgress = 0;

  function rootDir() {
    return deps.userData();
  }

  function report(payload) {
    const now = Date.now();
    if (now - lastProgress < 150 && payload.fraction < 1) return;
    lastProgress = now;
    onProgress(payload);
  }

  function tool(name) {
    return resolveTool(name, {
      env: deps.env || {},
      pathEntries: deps.pathEntries || [],
      exists: (file) => disk.existsSync(file),
      join: osPath.join,
      platform: deps.platform || "linux",
    });
  }

  async function ollama(pathname, options = {}) {
    const url = `${OLLAMA_ORIGIN}${pathname}`;
    if (!isOllamaUrl(url)) throw new Error("ollama-origin");
    const response = await fetchImpl(url, options);
    return response;
  }

  async function probe() {
    const machine = deps.machine?.() || {};
    const slow = machineIsSlow(machine);
    let ollamaUp = false;
    let models = [];
    if (!slow) {
      try {
        const response = await ollama("/api/tags");
        if (response?.ok) {
          const body = await response.json();
          models = Array.isArray(body?.models) ? body.models.map((item) => item.name).filter(Boolean) : [];
          ollamaUp = true;
        }
      } catch {
        ollamaUp = false;
      }
    }
    const root = rootDir();
    const whisperSize = sanitizeWhisperSize(deps.whisperSize);
    const whisperReady = disk.existsSync(osPath.join(root, `ggml-${whisperSize}.bin`));
    const voicesReady = ["adam", "eve", "people"].every((who) => disk.existsSync(osPath.join(root, voiceFile(who))));
    return {
      ollama: ollamaUp,
      slow,
      models,
      whisperBin: Boolean(tool("whisper-cli")),
      piperBin: Boolean(tool("piper")),
      whisperReady,
      voicesReady,
    };
  }

  async function downloadOne(entry, index, count) {
    if (!isAllowedDownload(entry.url)) throw new Error("download-refused");
    const dest = osPath.join(rootDir(), entry.file);
    if (!inside(osPath, rootDir(), dest)) throw new Error("path");
    if (disk.existsSync(dest)) {
      report(progressReport(index + 1, count, 1, 1, entry.label));
      return;
    }
    const response = await fetchImpl(entry.url);
    if (!response?.ok) throw new Error("download");
    const total = Number(response.headers?.get?.("content-length")) || 0;
    const chunks = [];
    await readStream(response, async (chunk, received) => {
      chunks.push(Buffer.from(chunk));
      report(progressReport(index, count, received, total, entry.label));
    });
    disk.mkdirSync(rootDir(), { recursive: true });
    disk.writeFileSync(dest, Buffer.concat(chunks));
    report(progressReport(index + 1, count, 1, 1, entry.label));
  }

  async function pullModel(model, index, count) {
    const response = await ollama("/api/pull", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ name: model, stream: true }),
    });
    if (!response?.ok) throw new Error("pull");
    let pending = "";
    await readStream(response, async (chunk, received) => {
      pending += Buffer.from(chunk).toString("utf8");
      const lines = pending.split("\n");
      pending = lines.pop() || "";
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const row = JSON.parse(line);
          const completed = Number(row.completed) || 0;
          const total = Number(row.total) || 0;
          report(progressReport(index, count, total ? completed : received, total || 0, row.status || model));
        } catch {
          /* keep reading */
        }
      }
    });
  }

  function run(bin, args, input) {
    return new Promise((resolve) => {
      const child = deps.spawn(bin, args, { shell: false, windowsHide: true });
      let settled = false;
      const finish = (code) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve(code ?? -1);
      };
      const timer = setTimeout(() => {
        try { child.kill(); } catch { /* already gone */ }
        finish(-1);
      }, 20000);
      child.on("error", () => finish(-1));
      child.on("close", (code) => finish(code));
      if (input != null && child.stdin) {
        child.stdin.write(input);
        child.stdin.end();
      }
    });
  }

  return {
    async status(whisperSize) {
      if (whisperSize) deps.whisperSize = sanitizeWhisperSize(whisperSize);
      const probed = await probe();
      const route = livingRoute({
        enabled: true,
        consent: true,
        ollama: probed.ollama,
        slow: probed.slow,
        ready: true,
        whisper: probed.whisperBin && probed.whisperReady,
        piper: probed.piperBin && probed.voicesReady,
      });
      return {
        ollama: probed.ollama,
        slow: probed.slow,
        whisper: route.listen === "whisper",
        piper: route.speak === "piper",
        models: probed.models,
      };
    },

    async prepare({ consent, model, whisperSize } = {}) {
      if (consent !== true) return { ok: false, reason: "consent", fallback: true };
      const size = sanitizeWhisperSize(whisperSize);
      deps.whisperSize = size;
      const name = sanitizeModelName(model);
      const machine = deps.machine?.() || {};
      if (machineIsSlow(machine)) return { ok: false, reason: "slow", fallback: true };
      let tags;
      try {
        const response = await ollama("/api/tags");
        if (!response?.ok) return { ok: false, reason: "ollama", fallback: true };
        tags = await response.json();
      } catch {
        return { ok: false, reason: "ollama", fallback: true };
      }
      const files = downloadsFor(size);
      const names = new Set((tags.models || []).map((item) => item.name));
      const steps = files.length + (names.has(name) ? 0 : 1);
      try {
        for (let i = 0; i < files.length; i += 1) await downloadOne(files[i], i, steps);
        if (!names.has(name)) await pullModel(name, files.length, steps);
      } catch {
        return { ok: false, reason: "download", fallback: true };
      }
      report({ label: "Ready", fraction: 1, received: 1, total: 1 });
      const probed = await probe();
      return {
        ok: true,
        ready: true,
        model: name,
        whisper: Boolean(probed.whisperBin && probed.whisperReady),
        piper: Boolean(probed.piperBin && probed.voicesReady),
      };
    },

    async chat(raw, model) {
      const request = parseChatRequest(raw);
      if (!request) return { ok: false, reason: "input" };
      const body = ollamaChatBody(request, model || DEFAULT_OLLAMA_MODEL);
      try {
        const response = await ollama("/api/chat", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!response?.ok) return { ok: false, reason: "ollama" };
        const payload = await response.json();
        const reply = shortenReply(payload?.message?.content);
        if (!reply) return { ok: false, reason: "empty" };
        return { ok: true, reply };
      } catch {
        return { ok: false, reason: "ollama" };
      }
    },

    async transcribe(wav, whisperSize) {
      const bin = tool("whisper-cli");
      if (!bin) return { ok: false, reason: "whisper" };
      const size = sanitizeWhisperSize(whisperSize);
      const model = osPath.join(rootDir(), `ggml-${size}.bin`);
      if (!disk.existsSync(model) || !inside(osPath, rootDir(), model)) return { ok: false, reason: "model" };
      const dir = disk.mkdtempSync(osPath.join(rootDir(), "hear-"));
      const wavFile = osPath.join(dir, "speech.wav");
      const outBase = osPath.join(dir, "speech");
      disk.writeFileSync(wavFile, wav);
      const code = await run(bin, whisperArgs(model, wavFile, outBase));
      const textFile = `${outBase}.txt`;
      let text = "";
      if (code === 0 && disk.existsSync(textFile)) text = String(disk.readFileSync(textFile, "utf8") || "").trim();
      try { disk.rmSync(dir, { recursive: true, force: true }); } catch { /* temp */ }
      if (!text) return { ok: false, reason: "empty" };
      return { ok: true, text: text.slice(0, 240) };
    },

    async speak(who, text) {
      const bin = tool("piper");
      if (!bin) return { ok: false, reason: "piper" };
      const speaker = ["adam", "eve", "people"].includes(who) ? who : "people";
      const model = osPath.join(rootDir(), voiceFile(speaker));
      if (!disk.existsSync(model) || !inside(osPath, rootDir(), model)) return { ok: false, reason: "model" };
      const dir = disk.mkdtempSync(osPath.join(rootDir(), "say-"));
      const outFile = osPath.join(dir, "line.wav");
      const code = await run(bin, piperArgs(model, outFile), shortenReply(text));
      if (code !== 0 || !disk.existsSync(outFile)) {
        try { disk.rmSync(dir, { recursive: true, force: true }); } catch { /* temp */ }
        return { ok: false, reason: "piper" };
      }
      const wav = disk.readFileSync(outFile);
      try { disk.rmSync(dir, { recursive: true, force: true }); } catch { /* temp */ }
      return { ok: true, wavBase64: Buffer.from(wav).toString("base64") };
    },
  };
}
