/**
 * Headless-friendly captures of the Electron game for /site.
 * Run: npm run capture:site
 * The capture window disables the sandbox so it can start on locked-down Linux.
 * The installed game keeps its own sandbox.
 */
import { app, BrowserWindow } from "electron";
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const media = path.join(root, "site", "media");
const press = path.join(root, "site", "press");

app.disableHardwareAcceleration();
app.commandLine.appendSwitch("no-sandbox");
app.commandLine.appendSwitch("disable-dev-shm-usage");

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function run(command, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { stdio: "inherit" });
    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${command} exited ${code}`));
    });
  });
}

async function evalJs(win, source) {
  return win.webContents.executeJavaScript(source, true);
}

async function click(win, id) {
  return evalJs(win, `(() => {
    const el = document.getElementById(${JSON.stringify(id)});
    if (!el || el.disabled) return false;
    const hidden = el.closest("[hidden]");
    if (hidden) return false;
    el.click();
    return true;
  })()`);
}

async function shot(win, name) {
  const image = await win.webContents.capturePage();
  const file = path.join(media, name);
  fs.writeFileSync(file, image.toPNG());
  const kb = Math.round(image.toPNG().length / 1024);
  console.log(`shot ${name} ${kb}kb`);
}

async function frames(win, count, gap, holdKey) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "elyon-frames-"));
  if (holdKey) {
    win.webContents.sendInputEvent({ type: "keyDown", keyCode: holdKey });
  }
  for (let i = 0; i < count; i += 1) {
    const image = await win.webContents.capturePage();
    fs.writeFileSync(path.join(dir, `f${String(i).padStart(2, "0")}.png`), image.toPNG());
    await delay(gap);
  }
  if (holdKey) {
    win.webContents.sendInputEvent({ type: "keyUp", keyCode: holdKey });
  }
  return dir;
}

async function gif(dir, name) {
  const out = path.join(media, name);
  await run("ffmpeg", [
    "-y",
    "-framerate", "8",
    "-i", path.join(dir, "f%02d.png"),
    "-vf", "fps=8,scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen=stats_mode=diff:max_colors=96[p];[s1][p]paletteuse=dither=bayer",
    out,
  ]);
  fs.rmSync(dir, { recursive: true, force: true });
  console.log(`gif ${name} ${Math.round(fs.statSync(out).size / 1024)}kb`);
}

async function waitFor(win, source, timeout = 5000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (await evalJs(win, source)) return true;
    await delay(40);
  }
  return false;
}

async function primaryUntil(win, source, steps = 24) {
  for (let i = 0; i < steps; i += 1) {
    if (await evalJs(win, source)) return true;
    const label = await evalJs(win, `document.getElementById("btn-primary")?.textContent || ""`);
    if (await click(win, "btn-confirm-yes")) {
      console.log("confirm", label);
      await delay(280);
      continue;
    }
    if (!(await click(win, "btn-primary"))) throw new Error(`No primary button while waiting. Last label: ${label}`);
    console.log("primary", label);
    await delay(320);
  }
  throw new Error("primaryUntil timed out");
}

async function main() {
  fs.mkdirSync(media, { recursive: true });
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    show: true,
    backgroundColor: "#07060c",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      devTools: false,
    },
  });
  win.setMenuBarVisibility(false);
  await win.loadFile(path.join(root, "index.html"));
  await evalJs(win, `(() => {
    localStorage.setItem("elyon-settings-v1", JSON.stringify({
      version: 1, master: 0, fullscreen: false, textSpeed: "fast", voice: false, updatedAt: Date.now()
    }));
    localStorage.removeItem("elyon-saves-v1");
    localStorage.removeItem("elyon-save-v1");
  })()`);
  await win.loadFile(path.join(root, "index.html"));
  await delay(700);
  win.focus();

  if (!(await waitFor(win, `document.body.dataset.screen === "title" && !!document.getElementById("btn-begin")`))) {
    throw new Error("Title screen did not appear");
  }
  await shot(win, "title.png");

  if (!(await click(win, "btn-begin"))) throw new Error("Begin did not click");
  if (!(await waitFor(win, `document.body.dataset.screen === "prologue"`))) throw new Error("Prologue missing");
  await delay(200);
  await shot(win, "prologue.png");

  if (!(await click(win, "btn-prologue"))) throw new Error("Prologue did not continue");
  if (!(await waitFor(win, `document.body.dataset.screen === "play" && !!document.getElementById("btn-primary")`))) {
    throw new Error("Play did not start");
  }
  await primaryUntil(win, `document.getElementById("btn-primary")?.textContent === "Form Adam"`);
  await delay(600);
  await shot(win, "garden.png");
  const skyFrames = await frames(win, 12, 140);
  await gif(skyFrames, "garden.gif");

  await primaryUntil(win, `document.getElementById("btn-primary")?.textContent === "Descend and speak with Adam"`);
  if (!(await click(win, "btn-primary"))) throw new Error("Descend missing");
  await delay(400);
  if (!(await waitFor(win, `document.getElementById("quest-kicker")?.textContent === "Among them"`))) {
    throw new Error("Walk mode did not open");
  }
  await shot(win, "walk.png");
  const walkFrames = await frames(win, 12, 140, "W");
  await gif(walkFrames, "walk.gif");

  await primaryUntil(win, `document.getElementById("panel-dialogue") && !document.getElementById("panel-dialogue").hidden`);
  await delay(200);
  await shot(win, "dialogue.png");
  win.webContents.sendInputEvent({ type: "keyDown", keyCode: "Escape" });
  win.webContents.sendInputEvent({ type: "keyUp", keyCode: "Escape" });
  await delay(200);

  if (!(await click(win, "btn-address"))) {
    const clicked = await evalJs(win, `(() => {
      const button = [...document.querySelectorAll("#utility-slot button")].find((el) => el.textContent === "Address");
      if (!button) return false;
      button.click();
      return true;
    })()`);
    if (!clicked) throw new Error("Address button missing");
  }
  if (!(await waitFor(win, `document.getElementById("panel-address") && !document.getElementById("panel-address").hidden`))) {
    throw new Error("Address panel did not open");
  }
  await evalJs(win, `(() => {
    const input = document.getElementById("chat-input");
    input.value = "Who are you, in this garden?";
    document.getElementById("btn-send-chat").click();
  })()`);
  await delay(300);
  await shot(win, "address.png");

  const zipPath = path.join(press, "screenshots.zip");
  if (fs.existsSync(zipPath)) fs.unlinkSync(zipPath);
  const names = ["title.png", "prologue.png", "garden.png", "walk.png", "dialogue.png", "address.png", "garden.gif", "walk.gif"];
  await run("zip", ["-j", zipPath, ...names.map((name) => path.join(media, name))]);
  console.log("zip", Math.round(fs.statSync(zipPath).size / 1024), "kb");
  app.quit();
}

app.whenReady().then(() => {
  main().catch((error) => {
    console.error(error);
    app.exit(1);
  });
});
