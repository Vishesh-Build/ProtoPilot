/**
 * Robust clipboard utility that works reliably across Electron desktop apps,
 * browser contexts, insecure origins, and background/unfocused windows.
 *
 * Tier 1: Electron native clipboard via contextBridge (100% reliable in desktop app)
 * Tier 2: navigator.clipboard.writeText (standard modern web API)
 * Tier 3: document.execCommand("copy") fallback using temporary textarea
 */
export async function copyTextToClipboard(text) {
  if (!text && text !== "") return false;
  const stringVal = String(text);

  // Tier 1: Electron Native IPC bridge
  if (typeof window !== "undefined" && window.protopilotDesktop?.writeClipboard) {
    try {
      const ok = await window.protopilotDesktop.writeClipboard(stringVal);
      if (ok) return true;
    } catch (err) {
      console.warn("[clipboard] Electron bridge copy failed, trying web API:", err);
    }
  }

  // Tier 2: Modern Browser navigator.clipboard
  if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(stringVal);
      return true;
    } catch (err) {
      console.warn("[clipboard] navigator.clipboard failed, trying fallback:", err);
    }
  }

  // Tier 3: Legacy document.execCommand("copy")
  if (typeof document !== "undefined") {
    try {
      const textarea = document.createElement("textarea");
      textarea.value = stringVal;
      textarea.style.position = "fixed";
      textarea.style.left = "-9999px";
      textarea.style.top = "-9999px";
      textarea.setAttribute("readonly", "");
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      const success = document.execCommand("copy");
      document.body.removeChild(textarea);
      if (success) return true;
    } catch (err) {
      console.error("[clipboard] execCommand copy failed:", err);
    }
  }

  return false;
}
