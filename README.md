# PoE2 Craft Planner — desktop app (Electron)

The Path of Exile 2 crafting recipe planner, packaged as a Windows desktop app and set up as a
proper project you can open in VS Code and keep adding features to.

## Run the finished Windows app
1. Download the build, unzip it anywhere.
2. Open the `win-unpacked` folder and run **`PoE2 Craft Planner.exe`**.
3. First launch: Windows SmartScreen may say "Windows protected your PC" because the app isn't
   code-signed (signing costs ~$200/yr and isn't needed for personal use). Click **More info → Run anyway**.

## Project layout
```
poe2-craft-planner-app/
├─ main.js            Electron main process — opens the window, loads the UI
├─ package.json       scripts + electron-builder config
├─ renderer/          the actual app (the web UI)
│  ├─ index.html      UI + crafting engine (orb/omen logic, patch 0.5.x)
│  └─ data.js         mod database (61 bases, ~1,345 mods, from Craft of Exile)
├─ build_data.py      regenerates renderer/data.js after a PoE2 patch
└─ dist/              build output (the .exe) — git-ignored
```

## Develop it (in VS Code)
1. **Open the folder:** VS Code → File → Open Folder → `poe2-craft-planner-app`.
2. **Install dependencies once:** open the built-in Terminal (Ctrl+`) and run `npm install`.
3. **Run it live as a desktop app:** `npm start` — opens the app in a window. Edit `renderer/index.html`
   or `renderer/data.js`, close and `npm start` again to see changes. (All the app logic lives in
   `renderer/` — it's plain HTML/CSS/JS, no framework.)
4. **Refresh the mod data after a patch:** `npm run refresh-data` (re-downloads Craft of Exile's dataset).

## Build the Windows app
- `npm run dist:dir` → builds the unpacked x64 app into `dist/win-unpacked/` (what we ship). **Run this on
  the Mac with:** `npx electron-builder --win --x64 --dir`
- `npm run dist` → *tries* to build a single portable `.exe`, but the installer tool (NSIS) is Intel-only and
  won't run on Apple Silicon, so on this Mac use the `--dir` build above and zip `win-unpacked`. A single-file
  `.exe` would build fine on a Windows machine or via a free GitHub Actions runner if we want that later.

## Adding features
Everything the user sees and every bit of crafting logic is in `renderer/index.html` (and the mod data in
`renderer/data.js`). Add UI or engine features there exactly like the web version — `main.js` just hosts it
in a window. Rebuild with the `--dir` command above to produce a fresh `.exe`.

## Notes
- **Size:** Electron apps bundle a browser engine, so the app is ~350 MB unpacked (~145 MB zipped). That's the
  cost of the easy cross-platform path. If size ever matters, the tiny alternative is Tauri (~10 MB), which
  needs a Windows or cloud build.
- Mod data © Craft of Exile (community tooling). Crafting logic targets **patch 0.5.x**.
