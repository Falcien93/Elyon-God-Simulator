import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";

const root = path.join(import.meta.dirname, "..");

function read(file) {
  return fs.readFileSync(path.join(root, file), "utf8");
}

test("Netlify publishes site with no build command", () => {
  const toml = read("netlify.toml");
  assert.match(toml, /publish\s*=\s*"site"/);
  assert.match(toml, /command\s*=\s*""/);
  assert.doesNotMatch(toml, /pages/i);
});

test("the canonical site is www.elyongame.com", () => {
  const html = read("site/index.html");
  const canonical = "https://www.elyongame.com/";
  assert.match(html, new RegExp(`rel="canonical" href="${canonical}"`));
  assert.match(html, new RegExp(`property="og:url" content="${canonical}"`));
  assert.match(html, /property="og:image" content="https:\/\/www\.elyongame\.com\/media\/garden\.png"/);
  assert.match(html, /https:\/\/foundryjr\.com/);
  assert.match(html, /A Foundry game/);
  assert.match(html, /YOUR_FORM_ID/);
  assert.match(read("site/robots.txt"), /Sitemap: https:\/\/www\.elyongame\.com\/sitemap\.xml/);
  assert.match(read("site/sitemap.xml"), /<loc>https:\/\/www\.elyongame\.com\/<\/loc>/);
  for (const name of ["short.txt", "long.txt", "facts.txt"]) {
    assert.match(read(`site/press/${name}`), /https:\/\/www\.elyongame\.com|elyongame\.com|Elyon/);
  }
  assert.match(read("site/press/facts.txt"), /https:\/\/www\.elyongame\.com/);
  assert.match(read("site/press/facts.txt"), /https:\/\/foundryjr\.com/);
});

test("press files and captured pictures are present", () => {
  for (const file of [
    "site/press/logo.png",
    "site/press/screenshots.zip",
    "site/media/title.png",
    "site/media/prologue.png",
    "site/media/garden.png",
    "site/media/walk.png",
    "site/media/dialogue.png",
    "site/media/address.png",
    "site/media/garden.gif",
    "site/media/walk.gif",
    "site/fonts/OFL.txt",
  ]) {
    const stat = fs.statSync(path.join(root, file));
    assert.ok(stat.size > 400, file);
  }
  assert.equal(fs.readFileSync(path.join(root, "site/media/garden.png")).subarray(0, 8).toString("hex"), "89504e470d0a1a0a");
  assert.equal(fs.readFileSync(path.join(root, "site/media/garden.gif")).subarray(0, 3).toString("ascii"), "GIF");
});
