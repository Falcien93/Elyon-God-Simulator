import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { isGameSender, navigationAllowed, PAGE_CSP, windowPreferences } from "../electron/guards.js";

const root = path.join(import.meta.dirname, "..");
const TEXT = new Set([".js", ".cjs", ".mjs", ".html", ".css", ".json", ".yml", ".yaml", ".md", ".cs", ".txt"]);
const SKIP = new Set(["node_modules", "dist", ".git", "Library", "Temp", "Logs", "obj", "bin"]);
const SECRET = [
  /sk-[A-Za-z0-9]{20,}/,
  /AKIA[0-9A-Z]{16}/,
  /ghp_[A-Za-z0-9]{20,}/,
  /xai-[A-Za-z0-9]{20,}/,
  /Bearer [A-Za-z0-9._-]{20,}/,
  /BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY/,
];

function walk(dir, out) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (SKIP.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, out);
    else if (TEXT.has(path.extname(entry.name))) out.push(full);
  }
  return out;
}

function csp(file) {
  const html = fs.readFileSync(path.join(root, file), "utf8");
  const match = html.match(/http-equiv="Content-Security-Policy" content="([^"]+)"/);
  assert.ok(match, file);
  return match[1];
}

test("the desktop window stays isolated", () => {
  const prefs = windowPreferences();
  assert.equal(prefs.contextIsolation, true);
  assert.equal(prefs.nodeIntegration, false);
  assert.equal(prefs.nodeIntegrationInWorker, false);
  assert.equal(prefs.nodeIntegrationInSubFrames, false);
  assert.equal(prefs.sandbox, true);
  assert.equal(prefs.webSecurity, true);
  assert.equal(prefs.allowRunningInsecureContent, false);
  assert.equal(prefs.webviewTag, false);
  assert.equal(isGameSender(4, 4), true);
  assert.equal(isGameSender(4, 5), false);
  assert.equal(isGameSender(1.5, 1), false);
  assert.equal(isGameSender(null, 1), false);
  assert.equal(navigationAllowed("file:///garden/index.html"), true);
  assert.equal(navigationAllowed("https://example.invalid/"), false);
  assert.equal(navigationAllowed("javascript:alert(1)"), false);
  assert.equal(navigationAllowed(""), false);
  assert.equal(navigationAllowed(`file:${"a".repeat(5000)}`), false);
});

test("the shell denies foreign navigation, webviews, and foreign IPC", () => {
  const main = fs.readFileSync(path.join(root, "electron/main.js"), "utf8");
  const preload = fs.readFileSync(path.join(root, "electron/preload.cjs"), "utf8");
  assert.match(main, /windowPreferences\(\)/);
  assert.match(main, /setWindowOpenHandler/);
  assert.match(main, /will-navigate/);
  assert.match(main, /will-redirect/);
  assert.match(main, /will-attach-webview/);
  assert.match(main, /isGameSender/);
  assert.doesNotMatch(main, /nodeIntegration:\s*true/);
  const handlers = main.split(/ipcMain\.handle\(/).slice(1);
  assert.ok(handlers.length >= 9);
  for (const handler of handlers) assert.match(handler.slice(0, 280), /fromGame\(event\)/);
  assert.match(preload, /contextBridge\.exposeInMainWorld\("elyonDesktop"/);
  assert.doesNotMatch(preload, /exposeInMainWorld\("require"/);
  assert.doesNotMatch(preload, /exposeInMainWorld\("ipcRenderer"/);
  assert.equal(csp("index.html"), PAGE_CSP);
  assert.equal(csp("splash.html"), PAGE_CSP);
  for (const file of ["index.html", "splash.html"]) {
    const html = fs.readFileSync(path.join(root, file), "utf8");
    assert.doesNotMatch(html, /<script[^>]+src="https?:/);
  }
});

test("tracked text has no secrets and the template leftovers are gone", () => {
  const hits = [];
  for (const file of walk(root, [])) {
    const text = fs.readFileSync(file, "utf8");
    for (const pattern of SECRET) {
      if (pattern.test(text)) hits.push(`${path.relative(root, file)} ${pattern}`);
    }
  }
  assert.deepEqual(hits, []);
  assert.equal(fs.existsSync(path.join(root, "scripts/make-icon.mjs")), false);
  assert.equal(fs.existsSync(path.join(root, "ElyonFirstLight/Assets/TutorialInfo")), false);
  assert.equal(fs.existsSync(path.join(root, "ElyonFirstLight/Assets/Readme.asset")), false);
});
