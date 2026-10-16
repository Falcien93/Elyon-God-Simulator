import { app, BrowserWindow, Menu, ipcMain } from "electron";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");

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

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 680,
    backgroundColor: "#07060c",
    title: "Elyon",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  win.loadFile(path.join(root, "index.html"));
  windowRef = win;
}

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
    Menu.setApplicationMenu(Menu.buildFromTemplate([
      {
        label: "Elyon",
        submenu: [
          { role: "about" },
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
