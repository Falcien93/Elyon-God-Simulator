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
  voicesStatus: (whisperSize) => ipcRenderer.invoke("voices-status", whisperSize),
  voicesPrepare: (payload) => ipcRenderer.invoke("voices-prepare", payload),
  voicesChat: (payload) => ipcRenderer.invoke("voices-chat", payload),
  voicesTranscribe: (wavBase64) => ipcRenderer.invoke("voices-transcribe", wavBase64),
  voicesSpeak: (payload) => ipcRenderer.invoke("voices-speak", payload),
  onVoicesProgress: (fn) => {
    const listener = (_event, report) => fn(report);
    ipcRenderer.on("voices-progress", listener);
    return () => ipcRenderer.removeListener("voices-progress", listener);
  },
});
