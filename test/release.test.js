import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { RELEASE } from "../js/release.js";

const root = path.join(import.meta.dirname, "..");
const pkg = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));

test("release info matches package.json", () => {
  assert.equal(RELEASE.version, pkg.version);
  assert.equal(RELEASE.name, pkg.productName);
  assert.equal(RELEASE.description, pkg.description);
  assert.equal(RELEASE.license, pkg.license);
  assert.equal(RELEASE.appId, pkg.build.appId);
});

test("installer targets stay unsigned", () => {
  assert.equal(pkg.build.forceCodeSigning, false);
  assert.deepEqual(pkg.build.win.target, ["nsis"]);
  assert.equal(pkg.build.win.icon, "assets/icon.ico");
  assert.equal(pkg.build.win.signAndEditExecutable, false);
  assert.equal(pkg.build.win.verifyUpdateCodeSignature, false);
  assert.deepEqual(pkg.build.mac.target, ["dmg"]);
  assert.equal(pkg.build.mac.icon, "assets/icon.icns");
  assert.equal(pkg.build.mac.identity, null);
  assert.equal(pkg.build.mac.notarize, false);
  assert.equal(pkg.build.mac.gatekeeperAssess, false);
  assert.equal(pkg.build.nsis.oneClick, false);
  assert.equal(pkg.build.nsis.shortcutName, "Elyon");
  assert.ok(pkg.build.files.includes("splash.html"));
  assert.equal(pkg.scripts["dist:dir"], "electron-builder --linux dir");
});

test("icon files are real png, ico, and icns", () => {
  const png = fs.readFileSync(path.join(root, "assets/icon.png"));
  assert.equal(png.subarray(0, 8).toString("hex"), "89504e470d0a1a0a");
  assert.equal(png.readUInt32BE(16), 512);
  assert.equal(png.readUInt32BE(20), 512);

  const ico = fs.readFileSync(path.join(root, "assets/icon.ico"));
  assert.equal(ico.readUInt16LE(0), 0);
  assert.equal(ico.readUInt16LE(2), 1);
  assert.ok(ico.readUInt16LE(4) >= 4);

  const icns = fs.readFileSync(path.join(root, "assets/icon.icns"));
  assert.equal(icns.subarray(0, 4).toString("ascii"), "icns");
  assert.equal(icns.readUInt32BE(4), icns.length);

  for (const size of [16, 32, 48, 64, 128, 256, 512]) {
    const bytes = fs.readFileSync(path.join(root, "assets/icons", `${size}x${size}.png`));
    assert.equal(bytes.subarray(0, 8).toString("hex"), "89504e470d0a1a0a");
  }
});

test("title, about, and splash expose the version", () => {
  const index = fs.readFileSync(path.join(root, "index.html"), "utf8");
  assert.match(index, /id="app-version"/);
  assert.match(index, /id="panel-about"/);
  assert.match(index, /id="btn-title-about"/);
  assert.match(index, /id="btn-pause-about"/);
  const splash = fs.readFileSync(path.join(root, "splash.html"), "utf8");
  assert.match(splash, /id="splash-version"/);
  const main = fs.readFileSync(path.join(root, "electron/main.js"), "utf8");
  assert.match(main, /signAndEditExecutable|signed:\s*false|signed: false/);
  assert.match(main, /get-about/);
  assert.match(main, /splash\.html/);
});
