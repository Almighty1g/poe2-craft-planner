// Exposes a tiny price-fetch bridge to the renderer. The fetch runs in the main
// process (no CORS there), so the renderer can get poe.ninja prices safely.
const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld("poeapi", {
  fetchLeagues: () => ipcRenderer.invoke("fetch-leagues"),
  fetchPrices: (league) => ipcRenderer.invoke("fetch-prices", league),
  appVersion: () => ipcRenderer.invoke("app-version"),
  checkUpdate: () => ipcRenderer.invoke("check-update"),
  openExternal: (url) => ipcRenderer.invoke("open-external", url)
});

// Hardware-locked licensing (used by license.html).
contextBridge.exposeInMainWorld("license", {
  hwid: () => ipcRenderer.invoke("license:hwid"),
  status: () => ipcRenderer.invoke("license:status"),
  activate: (key) => ipcRenderer.invoke("license:activate", key)
});
