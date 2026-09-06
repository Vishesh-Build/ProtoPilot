import { useEffect, useState } from "react";

/* ============================================================
   Smart download data — this is what makes the button behave
   like Claude's / VS Code's: the site asks GitHub (no backend,
   no token, public API) for the newest published release, then
   hands back the right installer asset for the visitor's OS.

   Because it reads the LIVE latest release every page load, you
   never touch this site again after shipping a new app version:
   release a new .exe and the download button updates itself.
   ============================================================ */

const GITHUB_OWNER = "Vishesh-Build";
const GITHUB_REPO = "ProtoPilot";
const RELEASES_API = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/releases/latest`;

// Fallback link if GitHub is unreachable or rate-limited: send the
// user to the Releases page so they can always grab the installer.
export const RELEASES_PAGE = `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/releases`;

export function detectOS() {
  if (typeof navigator === "undefined") return "unknown";
  const ua = navigator.userAgent || "";
  const platform = navigator.platform || "";
  if (/Win/i.test(platform) || /Windows/i.test(ua)) return "windows";
  if (/Mac/i.test(platform) || /Mac OS X/i.test(ua)) return "mac";
  if (/Linux/i.test(platform) || /Linux/i.test(ua)) return "linux";
  return "unknown";
}

const OS_LABEL = {
  windows: "Windows",
  mac: "macOS",
  linux: "Linux",
  unknown: "your computer",
};

// Match a release asset to an OS by its file extension.
function assetForOS(assets, os) {
  if (!Array.isArray(assets)) return null;
  const byExt = (exts) =>
    assets.find((a) => exts.some((ext) => a.name.toLowerCase().endsWith(ext)));
  if (os === "windows") return byExt([".exe"]);
  if (os === "mac") return byExt([".dmg"]);
  if (os === "linux") return byExt([".appimage", ".deb"]);
  return null;
}

export function useLatestRelease() {
  const os = detectOS();
  const [state, setState] = useState({
    loading: true,
    error: null,
    version: null,
    osLabel: OS_LABEL[os],
    os,
    // Direct installer URL for this visitor's OS (falls back to the
    // releases page when we can't find a matching asset).
    downloadUrl: RELEASES_PAGE,
    hasDirectAsset: false,
  });

  useEffect(() => {
    let cancelled = false;
    fetch(RELEASES_API, { headers: { Accept: "application/vnd.github+json" } })
      .then((res) => {
        if (!res.ok) throw new Error(`GitHub API ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (cancelled) return;
        const asset = assetForOS(data.assets, os);
        setState({
          loading: false,
          error: null,
          version: data.tag_name || data.name || null,
          osLabel: OS_LABEL[os],
          os,
          downloadUrl: asset ? asset.browser_download_url : RELEASES_PAGE,
          hasDirectAsset: Boolean(asset),
        });
      })
      .catch((err) => {
        if (cancelled) return;
        // Never leave the user stranded — the releases page always works.
        setState((s) => ({ ...s, loading: false, error: err.message }));
      });
    return () => {
      cancelled = true;
    };
  }, [os]);

  return state;
}
