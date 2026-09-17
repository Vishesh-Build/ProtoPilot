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

const { app, BrowserWindow, ipcMain, shell } = require("electron");
const path = require("path");
const http = require("http");
const fs = require("fs");
// electron-updater is imported lazily inside setupAutoUpdater() so a dev run
// (npm run electron:dev, app NOT packaged) never touches it — it only matters
// for an installed NSIS build talking to GitHub Releases.
let autoUpdater = null;

const APP_PORT = 5173;
const APP_URL = `http://localhost:${APP_PORT}`;

/* ------------------------------------------------------------
   Backend API URL resolution (runtime, not build time).

   Priority:
     1. PROTOPILOT_API_URL env var (dev convenience: set it in the
        shell before `npm run electron:dev`)
     2. The user's saved choice in userData/config.json — this is what
        makes an INSTALLED (NSIS) app pointable at any backend without
        rebuilding. Written by setApiBaseUrl below; today that's called
        programmatically, and a Settings UI can call it later.
     3. http://localhost:8000 (dev default, same as the renderer's
        own fallback so both agree out of the box).

   In a packaged build Vite has already baked VITE_API_BASE_URL into
   the bundle, which is why a runtime override is the piece that was
   missing: without it an installed app could only ever talk to
   whatever URL was on the machine that ran the build.
   ------------------------------------------------------------ */
// Packaged apps talk to the live Render backend by default. A dev machine can
// still override this with the PROTOPILOT_API_URL env var (see resolveApiBaseUrl
// below) to point at a local backend. Without this, an installed .exe defaulted
// to localhost:8000 — which only exists on a dev box — so every user saw
// "Can't reach the server". The renderer reads THIS value (via preload), not the
// vite-baked VITE_API_BASE_URL, so this is the one that actually matters for the
// desktop app.
const DEFAULT_API_BASE_URL = "https://protopilot-c60r.onrender.com";

function configPath() {
  return path.join(app.getPath("userData"), "config.json");
}

function readSavedApiBaseUrl() {
  try {
    const raw = fs.readFileSync(configPath(), "utf8");
    const parsed = JSON.parse(raw);
    if (typeof parsed.apiBaseUrl === "string" && /^https?:\/\//.test(parsed.apiBaseUrl)) {
      return parsed.apiBaseUrl.replace(/\/+$/, "");
    }
  } catch {
    /* no config yet, or unreadable — fall through */
  }
  return null;
}

function resolveApiBaseUrl() {
  const fromEnv = process.env.PROTOPILOT_API_URL;
  if (fromEnv && /^https?:\/\//.test(fromEnv)) {
    return fromEnv.replace(/\/+$/, "");
  }
  const saved = readSavedApiBaseUrl();
  if (saved) return saved;
  // Dev (unpackaged) talks to a local backend; a packaged/installed app talks
  // to the live Render backend. This is what makes the shipped .exe work out of
  // the box without every user configuring anything.
  return app.isPackaged ? DEFAULT_API_BASE_URL : "http://localhost:8000";
}

function setApiBaseUrl(url) {
  if (!/^https?:\/\//.test(url)) {
    throw new Error("API base URL must start with http:// or https://");
  }
  const cleaned = url.replace(/\/+$/, "");
  fs.mkdirSync(path.dirname(configPath()), { recursive: true });
  fs.writeFileSync(configPath(), JSON.stringify({ apiBaseUrl: cleaned }, null, 2));
  return cleaned;
}

const API_BASE_URL = resolveApiBaseUrl();

ipcMain.on("protopilot:get-api-base-url", (event) => {
  event.returnValue = API_BASE_URL;
});

// Origins the app window is allowed to navigate to directly.
// Everything else opens in the system browser via shell.openExternal.
const ALLOWED_NAVIGATION_ORIGINS = [
  APP_URL,
  API_BASE_URL, // the configured backend — wherever it actually is
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

/* ------------------------------------------------------------
   Auto-update (electron-updater + GitHub Releases).

   How it reaches an installed .exe:
     1. You bump "version" in package.json and run `npm run release:win`.
        electron-builder builds the NSIS installer AND uploads it (plus a
        latest.yml manifest) to a GitHub Release.
     2. Every installed app, on launch, quietly asks GitHub "is there a
        newer version than mine?" by reading that latest.yml.
     3. If yes, it downloads the new installer in the background, then tells
        the renderer — which shows an "Update ready — Restart" button. The
        user clicks it when convenient; nothing is forced.

   The code repo can stay PRIVATE as long as the *Releases* are public,
   because electron-updater only needs to read the release assets, which
   GitHub serves without a token for public releases.

   Guarded so it's a no-op in dev (app not packaged) and never crashes the
   app if electron-updater is missing or GitHub is unreachable.
   ------------------------------------------------------------ */
let latestUpdateState = { status: "idle", version: null, error: null };

function setupAutoUpdater(win) {
  if (!app.isPackaged) return; // dev run — nothing to update

  try {
    autoUpdater = require("electron-updater").autoUpdater;
  } catch (err) {
    console.warn("[updater] electron-updater not available:", err.message);
    return;
  }

  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;

  const push = (state) => {
    latestUpdateState = { ...latestUpdateState, ...state };
    if (win && !win.isDestroyed()) {
      win.webContents.send("protopilot:update-state", latestUpdateState);
    }
  };

  autoUpdater.on("checking-for-update", () => push({ status: "checking", error: null }));
  autoUpdater.on("update-available", (info) => push({ status: "downloading", version: info?.version || null }));
  autoUpdater.on("update-not-available", () => push({ status: "idle" }));
  autoUpdater.on("download-progress", (p) =>
    push({ status: "downloading", percent: Math.round(p?.percent || 0) })
  );
  autoUpdater.on("update-downloaded", (info) =>
    push({ status: "ready", version: info?.version || null })
  );
  autoUpdater.on("error", (err) =>
    // A failed update check must never break the app — just log + report.
    push({ status: "error", error: (err && err.message) || String(err) })
  );

  // Fire the first check a few seconds after launch so it doesn't compete
  // with window/render startup, then re-check hourly for long sessions.
  setTimeout(() => autoUpdater.checkForUpdates().catch(() => {}), 4000);
  setInterval(() => autoUpdater.checkForUpdates().catch(() => {}), 60 * 60 * 1000);
}

// Renderer asks for the current state (on mount) and can trigger the install.
ipcMain.handle("protopilot:get-update-state", () => latestUpdateState);
ipcMain.handle("protopilot:install-update", () => {
  if (autoUpdater && latestUpdateState.status === "ready") {
    // Restart into the freshly downloaded installer.
    autoUpdater.quitAndInstall();
    return true;
  }
  return false;
});

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

  // Microphone (and camera) permission. LiveKit calls getUserMedia under the
  // hood when the meeting mic is enabled; in a packaged Electron build
  // Chromium denies that request by default unless we approve it here, which
  // is why live voice capture / transcription silently produced nothing.
  // We only ever grant media (mic/camera) for our own app origin — every
  // other permission, and any other origin, is denied.
  const MEDIA_PERMISSIONS = new Set(["media", "audioCapture", "videoCapture"]);
  const sess = win.webContents.session;
  sess.setPermissionRequestHandler((_wc, permission, callback, details) => {
    const origin = details && details.requestingUrl;
    const allowed =
      MEDIA_PERMISSIONS.has(permission) &&
      (!origin || isAllowedOrigin(origin));
    callback(allowed);
  });
  sess.setPermissionCheckHandler((_wc, permission, origin) => {
    return (
      MEDIA_PERMISSIONS.has(permission) && (!origin || isAllowedOrigin(origin))
    );
  });

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

  setupAutoUpdater(win);

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
