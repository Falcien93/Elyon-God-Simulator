import { app, BrowserWindow, Menu, ipcMain } from "electron";
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createLivingHost } from "./living-host.js";
import { acceptableWavBase64, senderIsGame } from "../js/living.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");

app.setName("Elyon");
app.setAppUserModelId("com.elyon.garden");

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) app.quit();

let windowRef = null;
let livingHost = null;

function userFile(name) {
  return path.join(app.getPath("userData"), name);
}

function saveFile() {
  return userFile("elyon-save.json");
}

function libraryFile() {
  return userFile("elyon-saves.json");
}

function settingsFile() {
  return userFile("elyon-settings.json");
}

function readText(file) {
  try {
    return fs.readFileSync(file, "utf8");
  } catch {
    return null;
  }
}

function writeText(file, text) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temporary = `${file}.tmp`;
  fs.writeFileSync(temporary, text);
  fs.renameSync(temporary, file);
}

function readPackage() {
  try {
    return JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));
  } catch {
    return {};
  }
}

function aboutPayload() {
  const pkg = readPackage();
  return {
    name: pkg.productName || "Elyon",
    version: app.getVersion() || pkg.version || "1.0.0",
    description: pkg.description || "",
    license: pkg.license || "MIT",
    appId: "com.elyon.garden",
    signed: false,
  };
}

function createSplash() {
  const splash = new BrowserWindow({
    width: 520,
    height: 640,
    frame: false,
    resizable: false,
    center: true,
    show: true,
    backgroundColor: "#07060c",
    icon: path.join(root, "assets", "icon.png"),
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  const version = app.getVersion();
  splash.loadFile(path.join(root, "splash.html"), { query: { version } });
  return splash;
}

function createWindow() {
  const splash = createSplash();
  const opened = Date.now();
  let revealed = false;
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 680,
    backgroundColor: "#07060c",
    title: "Elyon",
    show: false,
    icon: path.join(root, "assets", "icon.png"),
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  const reveal = () => {
    if (revealed || win.isDestroyed()) return;
    revealed = true;
    const wait = Math.max(0, 600 - (Date.now() - opened));
    setTimeout(() => {
      if (win.isDestroyed()) return;
      win.show();
      if (!splash.isDestroyed()) splash.close();
    }, wait);
  };
  win.once("ready-to-show", reveal);
  setTimeout(reveal, 8000);
  win.webContents.session.setPermissionRequestHandler((contents, permission, callback) => {
    callback(permission === "media" && contents.id === win.webContents.id);
  });
  win.webContents.session.setPermissionCheckHandler((contents, permission) => {
    return permission === "media" && contents?.id === win.webContents.id;
  });
  win.loadFile(path.join(root, "index.html"));
  windowRef = win;
}

function fromGame(event) {
  if (!windowRef || windowRef.isDestroyed()) return false;
  return senderIsGame(event.sender?.id, windowRef.webContents.id);
}

function livingRoot() {
  return path.join(app.getPath("userData"), "living-voices");
}

function living() {
  if (!livingHost) {
    livingHost = createLivingHost({
      fetch: globalThis.fetch.bind(globalThis),
      spawn,
      fs,
      osPath: path,
      userData: livingRoot,
      machine: () => ({ cores: os.cpus().length, memoryBytes: os.totalmem() }),
      env: process.env,
      pathEntries: String(process.env.PATH || "").split(path.delimiter).filter(Boolean),
      platform: process.platform,
      whisperSize: "base",
      onProgress: (report) => {
        if (!windowRef || windowRef.isDestroyed()) return;
        windowRef.webContents.send("voices-progress", {
          label: String(report?.label || "").slice(0, 80),
          fraction: Number(report?.fraction) || 0,
          received: Number(report?.received) || 0,
          total: Number(report?.total) || 0,
        });
      },
    });
  }
  return livingHost;
}

function decodeSpeech(encoded) {
  if (!acceptableWavBase64(encoded)) return null;
  const buffer = Buffer.from(encoded, "base64");
  if (buffer.length < 44 || buffer.length > 1_500_000) return null;
  if (buffer.subarray(0, 4).toString("ascii") !== "RIFF") return null;
  if (buffer.subarray(8, 12).toString("ascii") !== "WAVE") return null;
  return buffer;
}

function denied() {
  return { ok: false, reason: "denied" };
}

ipcMain.handle("get-about", () => aboutPayload());

ipcMain.handle("load-save", () => {
  try {
    return fs.readFileSync(saveFile(), "utf8");
  } catch {
    return null;
  }
});

ipcMain.handle("write-save", (_event, text) => {
  if (!validJsonText(text, 1_500_000)) return false;
  writeText(saveFile(), text);
  return true;
});

ipcMain.handle("load-library", () => ({
  library: readText(libraryFile()),
  legacy: readText(saveFile()),
}));

ipcMain.handle("write-library", (_event, text) => {
  if (!validJsonText(text, 1_500_000)) return false;
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    return false;
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return false;
  if (parsed.format !== 1 || !Array.isArray(parsed.slots)) return false;
  writeText(libraryFile(), text);
  return true;
});

ipcMain.handle("load-settings", () => readText(settingsFile()));

ipcMain.handle("write-settings", (_event, text) => {
  if (!validJsonText(text, 20_000)) return false;
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    return false;
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return false;
  if (parsed.version !== 1) return false;
  writeText(settingsFile(), text);
  return true;
});

ipcMain.handle("toggle-fullscreen", () => {
  if (!windowRef) return false;
  windowRef.setFullScreen(!windowRef.isFullScreen());
  return windowRef.isFullScreen();
});

ipcMain.handle("set-fullscreen", (_event, value) => {
  if (!windowRef) return false;
  windowRef.setFullScreen(Boolean(value));
  return windowRef.isFullScreen();
});

ipcMain.handle("voices-status", async (event, whisperSize) => {
  if (!fromGame(event)) return null;
  return living().status(whisperSize);
});

ipcMain.handle("voices-prepare", async (event, payload) => {
  if (!fromGame(event)) return denied();
  if (!payload || typeof payload !== "object") return { ok: false, reason: "input", fallback: true };
  return living().prepare({
    consent: payload.consent === true,
    model: payload.model,
    whisperSize: payload.whisperSize,
  });
});

ipcMain.handle("voices-chat", async (event, payload) => {
  if (!fromGame(event)) return denied();
  if (!payload || typeof payload !== "object") return { ok: false, reason: "input" };
  return living().chat({
    who: payload.who,
    text: payload.text,
    context: payload.context,
    history: payload.history,
  }, payload.model);
});

ipcMain.handle("voices-transcribe", async (event, wavBase64) => {
  if (!fromGame(event)) return denied();
  const wav = decodeSpeech(wavBase64);
  if (!wav) return { ok: false, reason: "input" };
  return living().transcribe(wav);
});

ipcMain.handle("voices-speak", async (event, payload) => {
  if (!fromGame(event)) return denied();
  if (!payload || typeof payload !== "object") return { ok: false, reason: "input" };
  return living().speak(payload.who, payload.text);
});

function validJsonText(text, max) {
  if (typeof text !== "string" || text.length < 2 || text.length > max) return false;
  try {
    const parsed = JSON.parse(text);
    return Boolean(parsed) && typeof parsed === "object" && !Array.isArray(parsed);
  } catch {
    return false;
  }
}

if (gotLock) {
  app.whenReady().then(() => {
    const about = aboutPayload();
    app.setAboutPanelOptions({
      applicationName: about.name,
      applicationVersion: about.version,
      version: about.version,
      copyright: "MIT. This build is not code-signed.",
      credits: about.description,
    });
    Menu.setApplicationMenu(Menu.buildFromTemplate([
      {
        label: "Elyon",
        submenu: [
          {
            label: "About Elyon",
            click: () => {
              if (!windowRef || windowRef.isDestroyed()) return;
              windowRef.webContents.send("open-about");
            },
          },
          { type: "separator" },
          { role: "quit" },
        ],
      },
      {
        label: "View",
        submenu: [
          { role: "reload" },
          { role: "togglefullscreen" },
          { type: "separator" },
          { role: "zoomIn" },
          { role: "zoomOut" },
          { role: "resetZoom" },
        ],
      },
    ]));
    createWindow();
    app.on("activate", () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
  });

  app.on("second-instance", () => {
    if (!windowRef) return;
    if (windowRef.isMinimized()) windowRef.restore();
    windowRef.focus();
  });

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
  });
}
