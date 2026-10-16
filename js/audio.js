/** Small synthesizer. No external audio files. */

export function createAudio() {
  let ctx = null;
  let musicGain = null;
  let sfxGain = null;
  let started = false;

  function ensure() {
    if (ctx) return ctx;
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return null;
    ctx = new AudioCtx();
    musicGain = ctx.createGain();
    sfxGain = ctx.createGain();
    musicGain.gain.value = 0.32;
    sfxGain.gain.value = 0.7;
    musicGain.connect(ctx.destination);
    sfxGain.connect(ctx.destination);
    return ctx;
  }

  function startMusic() {
    const audio = ensure();
    if (!audio || started) return;
    started = true;
    const filter = audio.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 420;
    filter.connect(musicGain);
    const base = [146.83, 220, 293.66];
    for (const freq of base) {
      const osc = audio.createOscillator();
      const gain = audio.createGain();
      osc.type = freq < 200 ? "sine" : "triangle";
      osc.frequency.value = freq;
      gain.gain.value = freq < 200 ? 0.08 : 0.03;
      osc.connect(gain);
      gain.connect(filter);
      osc.start();
    }
  }

  function tone(freq, duration, type, gainValue) {
    const audio = ensure();
    if (!audio) return;
    const osc = audio.createOscillator();
    const gain = audio.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(gainValue, audio.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, audio.currentTime + duration);
    osc.connect(gain);
    gain.connect(sfxGain);
    osc.start();
    osc.stop(audio.currentTime + duration + 0.02);
  }

  return {
    resume() {
      const audio = ensure();
      if (!audio) return;
      if (audio.state === "suspended") audio.resume();
      startMusic();
    },
    setVolumes(music, sfx) {
      if (!musicGain || !sfxGain) return;
      musicGain.gain.value = music;
      sfxGain.gain.value = sfx;
    },
    cue(kind) {
      this.resume();
      if (kind === "ritual") {
        tone(523.25, 0.7, "sine", 0.08);
        tone(659.25, 0.9, "sine", 0.05);
        tone(783.99, 1.1, "triangle", 0.04);
      } else if (kind === "bless") {
        tone(880, 0.4, "sine", 0.05);
      } else if (kind === "paint") {
        tone(392, 0.12, "triangle", 0.03);
      } else if (kind === "ui") {
        tone(640, 0.08, "sine", 0.03);
      }
    },
  };
}
