const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("elyonDesktop", {
  loadSave: () => ipcRenderer.invoke("load-save"),
  writeSave: (text) => ipcRenderer.invoke("write-save", text),
  toggleFullscreen: () => ipcRenderer.invoke("toggle-fullscreen"),
});
