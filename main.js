// Electron main process — creates the window and loads the planner UI.
const { app, BrowserWindow, Menu, shell, ipcMain } = require("electron");
const path = require("path");
const crypto = require("crypto");
const fs = require("fs");

/* ===================== HARDWARE-LOCKED LICENSING ===================== */
// The app unlocks only with a key signed (by the private keygen) for THIS machine's HWID.
// Only the PUBLIC key ships here, so keys can't be forged. Verification happens in main.
const LICENSE_PUBKEY =
  "-----BEGIN PUBLIC KEY-----\n" +
  "MCowBQYDK2VwAyEAQvqGkKUfRhGYERpDUyvC8QOY5jbaSN9p2On1xxRLocI=\n" +
  "-----END PUBLIC KEY-----\n";

let HWID = "UNKNOWN";
try {
  const { machineIdSync } = require("node-machine-id");
  HWID = machineIdSync().replace(/[^a-f0-9]/gi, "").slice(0, 32).toUpperCase();
} catch (e) { /* fall back below */ }
if (HWID === "UNKNOWN" || HWID.length < 16) {
  // fallback fingerprint if node-machine-id is unavailable
  const os = require("os");
  const macs = Object.values(os.networkInterfaces()).flat()
    .filter(n => n && !n.internal && n.mac && n.mac !== "00:00:00:00:00:00").map(n => n.mac).sort();
  HWID = crypto.createHash("sha256")
    .update([os.hostname(), os.platform(), os.arch(), os.cpus()[0] && os.cpus()[0].model, macs[0] || ""].join("|"))
    .digest("hex").slice(0, 32).toUpperCase();
}

const licenseFile = () => path.join(app.getPath("userData"), "license.key");
function verifyKey(key) {
  try {
    return crypto.verify(null, Buffer.from(HWID), LICENSE_PUBKEY, Buffer.from(String(key).trim(), "base64"));
  } catch (e) { return false; }
}
function isLicensed() {
  try { return verifyKey(fs.readFileSync(licenseFile(), "utf8")); } catch (e) { return false; }
}
ipcMain.handle("license:hwid", () => HWID);
ipcMain.handle("license:status", () => isLicensed());
ipcMain.handle("license:activate", (e, key) => {
  if (verifyKey(key)) {
    try { fs.writeFileSync(licenseFile(), String(key).trim()); } catch (err) {}
    const win = BrowserWindow.fromWebContents(e.sender);
    if (win) win.loadFile(path.join(__dirname, "renderer", "index.html"));   // unlock → load planner
    return true;
  }
  return false;
});

/* ===================== UPDATE CHECK ===================== */
// On launch the app checks a public version manifest (a gist) and notifies if a newer
// build exists. No silent self-update (repo is private + app is licensed) — just a heads-up.
const APP_VERSION = "1.4.0";
const UPDATE_MANIFEST = "https://gist.githubusercontent.com/Almighty1g/21f993e8c717759eae0713e1817f3f5d/raw/poe2-planner-version.json";
function cmpVer(a, b) {
  const pa = String(a).split(".").map(Number), pb = String(b).split(".").map(Number);
  for (let i = 0; i < 3; i++) { const x = pa[i] || 0, y = pb[i] || 0; if (x !== y) return x > y ? 1 : -1; }
  return 0;
}
ipcMain.handle("app-version", () => APP_VERSION);
ipcMain.handle("check-update", async () => {
  try {
    const r = await fetch(UPDATE_MANIFEST + "?t=" + Date.now());
    if (!r.ok) return { update: false, current: APP_VERSION };
    const m = await r.json();
    return { update: cmpVer(m.version, APP_VERSION) > 0, current: APP_VERSION,
             version: m.version, notes: m.notes, url: m.url };
  } catch (e) { return { update: false, current: APP_VERSION }; }
});
ipcMain.handle("open-external", (_e, url) => { try { shell.openExternal(String(url)); } catch (e) {} });

// Live prices from poe2scout (documented PoE2 economy API). Fetched in the MAIN
// process — no CORS restrictions here. All prices are in Exalted Orbs (the base).
const PS = "https://poe2scout.com/api";
const PS_HEADERS = { "Accept": "application/json", "User-Agent": "PoE2CraftPlanner (desktop app)" };
async function psGet(url) {
  const r = await fetch(url, { headers: PS_HEADERS });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// List of PoE2 leagues (current ones flagged) for the league picker.
ipcMain.handle("fetch-leagues", async () => {
  try { return await psGet(`${PS}/poe2/Leagues`); }
  catch (err) { return { error: String(err) }; }
});

// Merged price map (orbs + omens + essences + fragments + runes) for one league.
ipcMain.handle("fetch-prices", async (_e, league) => {
  try {
    let divinePrice = null;
    try {
      const leagues = await psGet(`${PS}/poe2/Leagues`);
      const L = Array.isArray(leagues) && leagues.find(x => x.Value === league);
      if (L) divinePrice = L.DivinePrice;
    } catch (e) { /* non-fatal */ }

    const byName = {};
    for (const cat of ["currency", "ritual", "essences", "fragments", "runes"]) {
      try {
        const d = await psGet(`${PS}/poe2/Leagues/${encodeURIComponent(league)}`
          + `/Currencies/ByCategory?Category=${cat}&page=1&perPage=300`);
        (d.Items || []).forEach(it => { if (it.CurrentPrice != null) byName[it.Text] = it.CurrentPrice; });
      } catch (e) { /* skip a failed category */ }
    }
    byName["Exalted Orb"] = 1;   // base currency

    if (Object.keys(byName).length < 2) return { error: "no price data" };
    return { byName, divinePrice };
  } catch (err) {
    return { error: String(err) };
  }
});

function createWindow() {
  const win = new BrowserWindow({
    width: 1180,
    height: 880,
    minWidth: 720,
    minHeight: 600,
    backgroundColor: "#0e0b07",
    title: "PoE2 Craft Planner",
    autoHideMenuBar: true,            // hide the menu bar (toggle with Alt)
    webPreferences: { contextIsolation: true, preload: path.join(__dirname, "preload.js") }
  });

  // Gate: show the license screen until a valid key for this machine is present.
  win.loadFile(path.join(__dirname, "renderer", isLicensed() ? "index.html" : "license.html"));

  // open external links (poe2db, Craft of Exile) in the user's real browser
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
}

Menu.setApplicationMenu(null);

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
