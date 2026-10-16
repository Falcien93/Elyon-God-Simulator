/** Pure checks for the desktop shell. No Electron import, so tests can run them. */

export const PAGE_CSP = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self'",
  "font-src 'self'",
  "img-src 'self'",
  "connect-src 'none'",
  "object-src 'none'",
  "base-uri 'none'",
  "frame-src 'none'",
  "form-action 'none'",
].join("; ");

export function windowPreferences() {
  return {
    contextIsolation: true,
    nodeIntegration: false,
    nodeIntegrationInWorker: false,
    nodeIntegrationInSubFrames: false,
    sandbox: true,
    webSecurity: true,
    allowRunningInsecureContent: false,
    webviewTag: false,
  };
}

export function isGameSender(senderId, gameId) {
  return Number.isInteger(senderId) && Number.isInteger(gameId) && senderId === gameId;
}

export function navigationAllowed(url) {
  if (typeof url !== "string" || url.length === 0 || url.length > 4096) return false;
  return url.startsWith("file:");
}
