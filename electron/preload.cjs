const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("elyonDesktop", {
  loadSave: () => ipcRenderer.invoke("load-save"),
  writeSave: (text) => ipcRenderer.invoke("write-save", text),
  loadLibrary: () => ipcRenderer.invoke("load-library"),
  writeLibrary: (text) => ipcRenderer.invoke("write-library", text),
  loadSettings: () => ipcRenderer.invoke("load-settings"),
  writeSettings: (text) => ipcRenderer.invoke("write-settings", text),
  toggleFullscreen: () => ipcRenderer.invoke("toggle-fullscreen"),
  setFullscreen: (value) => ipcRenderer.invoke("set-fullscreen", value),
  getAbout: () => ipcRenderer.invoke("get-about"),
  onOpenAbout: (fn) => {
    const listener = () => fn();
    ipcRenderer.on("open-about", listener);
    return () => ipcRenderer.removeListener("open-about", listener);
  },
});
