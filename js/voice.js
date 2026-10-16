/** Web Speech helpers. Missing APIs and thrown calls return a reason instead of failing the chat. */

export function voiceSupport(host = globalThis) {
  const synth = host?.speechSynthesis;
  const Recognition = host?.SpeechRecognition || host?.webkitSpeechRecognition;
  return {
    speak: Boolean(synth) && typeof synth.speak === "function" && typeof host.SpeechSynthesisUtterance === "function",
    listen: typeof Recognition === "function",
  };
}

export function speakText(text, who, host = globalThis) {
  try {
    const support = voiceSupport(host);
    if (!support.speak) return { ok: false, reason: "no-tts" };
    const utter = new host.SpeechSynthesisUtterance(String(text ?? ""));
    utter.rate = 0.95;
    utter.pitch = who === "eve" ? 1.15 : 0.9;
    utter.volume = 0.85;
    if (typeof host.speechSynthesis.cancel === "function") host.speechSynthesis.cancel();
    host.speechSynthesis.speak(utter);
    return { ok: true };
  } catch {
    return { ok: false, reason: "no-tts" };
  }
}

export function startListening(host, onResult, onEnd) {
  try {
    const Recognition = host?.SpeechRecognition || host?.webkitSpeechRecognition;
    if (typeof Recognition !== "function") {
      return { ok: false, reason: "no-recognition", stop() {} };
    }
    const recognition = new Recognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      try {
        const transcript = event?.results?.[0]?.[0]?.transcript;
        if (typeof transcript === "string" && transcript.trim()) onResult(transcript.trim());
      } catch {
        onEnd?.("error");
      }
    };
    recognition.onerror = () => onEnd?.("error");
    recognition.onend = () => onEnd?.("end");
    recognition.start();
    return {
      ok: true,
      stop() {
        try {
          recognition.stop();
        } catch {
          /* already stopped */
        }
      },
    };
  } catch {
    return { ok: false, reason: "no-recognition", stop() {} };
  }
}
