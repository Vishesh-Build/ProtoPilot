/* ============================================================
   ProtoPilot — Electron main process

   Key decisions, and why:

   1. The window ALWAYS loads over http://localhost:5173 — in dev
      that's the Vite dev server; in a packaged build, this file
      spins up a tiny local static server for the built `dist/`
      folder on the same port. Loading over file:// instead would
      give the renderer a `null`/`file://` origin, which breaks the
      backend's CORS allowlist and makes the httpOnly session
      cookies behave inconsistently between dev and prod. Same
      origin both ways = one code path, not two.

   2. contextIsolation is on, nodeIntegration is off — the renderer
      (your React app) never gets direct Node/filesystem access.
      Only the few things explicitly exposed in preload.js are
      reachable from the page.

   3. `will-navigate` only allows navigation to origins this app
      actually needs (the local app itself, the backend, and the
      real Google/GitHub OAuth domains). Anything else opens in the
      user's normal system browser instead of inside the app window
      — this is what stops a compromised/malicious link from
      hijacking the app window into a phishing page that *looks*
      like it's still ProtoPilot.
   ============================================================ */

const { app, BrowserWindow, shell } = require("electron");
const path = require("path");
const http = require("http");
const fs = require("fs");

const APP_PORT = 5173;
const APP_URL = `http://localhost:${APP_PORT}`;

// Origins the app window is allowed to navigate to directly.
// Everything else opens in the system browser via shell.openExternal.
const ALLOWED_NAVIGATION_ORIGINS = [
  APP_URL,
  "http://localhost:8000", // backend, during local dev
  "https://accounts.google.com",
  "https://oauth2.googleapis.com",
  "https://openidconnect.googleapis.com",
  "https://github.com",
  "https://api.github.com",
];

function isAllowedOrigin(urlString) {
  try {
    const url = new URL(urlString);
    return ALLOWED_NAVIGATION_ORIGINS.some((allowed) => urlString.startsWith(allowed) || url.origin === new URL(allowed).origin);
  } catch {
    return false;
  }
}

const MIME_TYPES = {
  ".html": "text/html",
  ".js": "text/javascript",
  ".mjs": "text/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

/**
 * Minimal static file server for the built `dist/` folder — only used in
 * a packaged build. Falls back to index.html for any unknown path so the
 * app's own client-side page state (?token=, ?oauth=success) still works.
 */
function startProductionServer(distDir) {
  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      let filePath = path.join(distDir, decodeURIComponent(req.url.split("?")[0]));
      if (!filePath.startsWith(distDir)) {
        res.writeHead(403);
        res.end("Forbidden");
        return;
      }
      fs.stat(filePath, (err, stats) => {
        if (err || !stats.isFile()) {
          filePath = path.join(distDir, "index.html");
        }
        const ext = path.extname(filePath);
        res.writeHead(200, { "Content-Type": MIME_TYPES[ext] || "application/octet-stream" });
        fs.createReadStream(filePath).pipe(res);
      });
    });

    server.on("error", reject);
    server.listen(APP_PORT, "localhost", () => resolve(server));
  });
}

async function createWindow() {
  const win = new BrowserWindow({
    width: 1360,
    height: 860,
    minWidth: 1024,
    minHeight: 700,
    title: "ProtoPilot",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  win.setMenuBarVisibility(false);

  win.webContents.on("will-navigate", (event, url) => {
    if (!isAllowedOrigin(url)) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });

  // Links opened with target="_blank" or window.open() — send them to the
  // system browser instead of spawning a new Electron window.
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (isAllowedOrigin(url)) {
      return { action: "allow" };
    }
    shell.openExternal(url);
    return { action: "deny" };
  });

  if (app.isPackaged) {
    const distDir = path.join(__dirname, "..", "dist");
    await startProductionServer(distDir);
  }
  // In dev, `npm run electron:dev` waits for the Vite dev server (also on
  // port 5173) before launching Electron — see package.json.

  await win.loadURL(APP_URL);

  return win;
}

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
