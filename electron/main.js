import { app, BrowserWindow, Menu, ipcMain } from "electron";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { isGameSender, navigationAllowed, windowPreferences } from "./guards.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");

function windowIcon() {
  const file = process.platform === "win32" ? "icon.ico" : "icon.png";
  return path.join(root, "assets", file);
}

app.setName("Elyon");
app.setAppUserModelId("com.elyon.garden");

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) app.quit();

let windowRef = null;

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
    icon: windowIcon(),
    webPreferences: {
      ...windowPreferences(),
      devTools: false,
    },
  });
  contain(splash.webContents);
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
    icon: windowIcon(),
    autoHideMenuBar: true,
    webPreferences: {
      ...windowPreferences(),
      preload: path.join(__dirname, "preload.cjs"),
      devTools: false,
    },
  });
  contain(win.webContents);
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
  win.loadFile(path.join(root, "index.html"));
  windowRef = win;
}

function contain(contents) {
  contents.setWindowOpenHandler(() => ({ action: "deny" }));
  const block = (event, url) => {
    if (!navigationAllowed(url)) event.preventDefault();
  };
  contents.on("will-navigate", block);
  contents.on("will-redirect", block);
  contents.on("will-attach-webview", (event) => event.preventDefault());
}

function fromGame(event) {
  if (!windowRef || windowRef.isDestroyed()) return false;
  return isGameSender(event.sender.id, windowRef.webContents.id);
}

ipcMain.handle("get-about", (event) => (fromGame(event) ? aboutPayload() : null));

ipcMain.handle("load-save", (event) => {
  if (!fromGame(event)) return null;
  try {
    return fs.readFileSync(saveFile(), "utf8");
  } catch {
    return null;
  }
});

ipcMain.handle("write-save", (event, text) => {
  if (!fromGame(event)) return false;
  if (!validJsonText(text, 1_500_000)) return false;
  writeText(saveFile(), text);
  return true;
});

ipcMain.handle("load-library", (event) => {
  if (!fromGame(event)) return { library: null, legacy: null };
  return {
    library: readText(libraryFile()),
    legacy: readText(saveFile()),
  };
});

ipcMain.handle("write-library", (event, text) => {
  if (!fromGame(event)) return false;
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

ipcMain.handle("load-settings", (event) => (fromGame(event) ? readText(settingsFile()) : null));

ipcMain.handle("write-settings", (event, text) => {
  if (!fromGame(event)) return false;
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

ipcMain.handle("toggle-fullscreen", (event) => {
  if (!fromGame(event) || !windowRef) return false;
  windowRef.setFullScreen(!windowRef.isFullScreen());
  return windowRef.isFullScreen();
});

ipcMain.handle("set-fullscreen", (event, value) => {
  if (!fromGame(event) || !windowRef) return false;
  windowRef.setFullScreen(Boolean(value));
  return windowRef.isFullScreen();
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
