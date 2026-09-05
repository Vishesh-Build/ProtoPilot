/* ============================================================
   ProtoPilot — Electron preload script

   Runs in an isolated context with access to Node APIs, but the
   renderer (your React app) can ONLY reach what's explicitly
   exposed here via contextBridge — nothing else leaks through.

   Kept intentionally tiny for now: the renderer talks to the
   FastAPI backend directly over fetch(), same as it would in a
   browser. Add more here only when a feature genuinely needs
   OS-level access (e.g. native file save dialogs for exports).
   ============================================================ */

const { contextBridge, ipcRenderer } = require("electron");

// Resolved once in the main process (see main.cjs: env var, then the
// user's saved config, then the localhost default) and handed to the
// renderer here. The renderer never reads process.env itself — it's
// sandboxed, and in a packaged build Vite has already baked
// import.meta.env values in, so this is the only runtime-configurable
// path for the packaged app.
contextBridge.exposeInMainWorld("protopilotDesktop", {
  isDesktop: true,
  platform: process.platform,
  apiBaseUrl: ipcRenderer.sendSync("protopilot:get-api-base-url"),
  versions: {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
  },
});
