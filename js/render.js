/** Canvas rendering for sky and walk views. */

import { sunHeight } from "./sim.js";
import { TILE, WORLD_H, WORLD_W, isTree } from "./world.js";

export function hash(n) {
  let x = Math.imul(n ^ 0x9e3779b9, 0x85ebca6b);
  x = Math.imul(x ^ (x >>> 13), 0xc2b2ae35);
  return ((x ^ (x >>> 16)) >>> 0) / 4294967296;
}

export function screenToWorld(px, py, view) {
  return {
    x: (px - view.w / 2) / view.tile + view.camX,
    y: (py - view.h / 2) / view.tile + view.camY,
  };
}

function toScreen(x, y, view) {
  return {
    x: (x - view.camX) * view.tile + view.w / 2,
    y: (y - view.camY) * view.tile + view.h / 2,
  };
}

function skyFill(ctx, view, state) {
  const g = ctx.createLinearGradient(0, 0, 0, view.h);
  if (!state.flags.ritual_light) {
    g.addColorStop(0, "#09070f");
    g.addColorStop(1, "#1a1220");
  } else {
    const sun = sunHeight(state.time);
    if (sun > 0.55) {
      g.addColorStop(0, "#8ec4e4");
      g.addColorStop(1, "#e7f4ff");
    } else if (sun > 0.05) {
      g.addColorStop(0, "#f2a36c");
      g.addColorStop(0.45, "#f6d7b0");
      g.addColorStop(1, "#9ec0d4");
    } else {
      g.addColorStop(0, "#070b16");
      g.addColorStop(1, "#243352");
    }
  }
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, view.w, view.h);
}

function tileColor(tile, x, y, salt) {
  const n = hash(x * 97 + y * 131 + salt);
  switch (tile) {
    case TILE.CHAOS:
      return n > 0.5 ? "#120e18" : "#0c0a12";
    case TILE.NIGHT:
      return `rgb(${28 + n * 16}, ${36 + n * 14}, ${52 + n * 12})`;
    case TILE.WATER:
      return `rgb(${22 + n * 18}, ${86 + n * 24}, ${118 + n * 16})`;
    case TILE.DEEP:
      return `rgb(${10 + n * 8}, ${46 + n * 14}, ${72 + n * 10})`;
    case TILE.SAND:
      return `rgb(${186 + n * 28}, ${154 + n * 20}, ${96 + n * 16})`;
    case TILE.GRASS:
      return `rgb(${52 + n * 28}, ${96 + n * 30}, ${42 + n * 16})`;
    case TILE.STONE:
      return `rgb(${78 + n * 20}, ${74 + n * 16}, ${68 + n * 12})`;
    case TILE.FLOWER:
      return `rgb(${58 + n * 20}, ${104 + n * 24}, ${48 + n * 12})`;
    default:
      return "#111";
  }
}

function roundRect(ctx, x, y, w, h, r) {
  const radius = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + w, y, x + w, y + h, radius);
  ctx.arcTo(x + w, y + h, x, y + h, radius);
  ctx.arcTo(x, y + h, x, y, radius);
  ctx.arcTo(x, y, x + w, y, radius);
  ctx.closePath();
}

export function render(ctx, state, view) {
  const { w, h, tile } = view;
  skyFill(ctx, view, state);
  if (!state.flags.ritual_lights && state.flags.ritual_light) drawStars(ctx, view, 0.35);
  if (state.flags.ritual_lights && sunHeight(state.time) < 0.15) drawStars(ctx, view, 0.8);

  const left = Math.max(0, Math.floor(view.camX - w / tile / 2) - 1);
  const right = Math.min(WORLD_W, Math.ceil(view.camX + w / tile / 2) + 1);
  const top = Math.max(0, Math.floor(view.camY - h / tile / 2) - 1);
  const bottom = Math.min(WORLD_H, Math.ceil(view.camY + h / tile / 2) + 1);

  for (let y = top; y < bottom; y += 1) {
    for (let x = left; x < right; x += 1) {
      const tileId = state.world.tiles[y * WORLD_W + x];
      const p = toScreen(x, y, view);
      ctx.fillStyle = tileColor(tileId, x, y, 1);
      ctx.fillRect(p.x, p.y, tile + 0.5, tile + 0.5);
      if (tileId === TILE.WATER || tileId === TILE.DEEP) drawWater(ctx, p.x, p.y, tile, x, y, view.now);
      if (tileId === TILE.GRASS) drawGrass(ctx, p.x, p.y, tile, x, y);
      if (tileId === TILE.FLOWER) drawBlooms(ctx, p.x, p.y, tile, x, y);
      if (tileId === TILE.STONE) drawStone(ctx, p.x, p.y, tile, x, y);
      if (tileId === TILE.SAND) drawSand(ctx, p.x, p.y, tile, x, y);
    }
  }

  if (view.hover && view.hover.x >= 0 && view.hover.y >= 0 && view.hover.x < WORLD_W && view.hover.y < WORLD_H) {
    const p = toScreen(view.hover.x, view.hover.y, view);
    ctx.strokeStyle = "rgba(228, 194, 122, 0.9)";
    ctx.lineWidth = 2;
    ctx.strokeRect(p.x + 1, p.y + 1, tile - 2, tile - 2);
  }

  const drawables = state.world.entities.filter((entity) => {
    if (entity.kind === "serpent" && (state.flags.serpent_gone || state.ending?.id === "harmony" || state.ending?.id === "wonder")) {
      return false;
    }
    if (entity.kind === "serpent" && !state.flags.serpent_present) return false;
    return true;
  });
  drawables.sort((a, b) => a.y - b.y);
  for (const entity of drawables) {
    const p = toScreen(entity.x, entity.y, view);
    drawEntity(ctx, state, entity, p.x, p.y, tile, view.now);
  }

  if (state.mode === "walk") {
    const p = toScreen(state.player.x, state.player.y, view);
    drawElyon(ctx, p.x, p.y, tile, view.now, state.player.facing);
  } else if (state.flags.descended) {
    const p = toScreen(state.player.x, state.player.y, view);
    ctx.fillStyle = "rgba(255, 236, 196, 0.85)";
    ctx.beginPath();
    ctx.arc(p.x, p.y, Math.max(3, tile * 0.12), 0, Math.PI * 2);
    ctx.fill();
  }

  drawFirmament(ctx, state, view);
  const sun = state.flags.ritual_light ? sunHeight(state.time) : -1;
  if (sun < 0.2) {
    ctx.fillStyle = `rgba(4, 8, 18, ${state.flags.ritual_light ? Math.max(0, -sun) * 0.48 + 0.05 : 0.18})`;
    ctx.fillRect(0, 0, w, h);
  } else if (sun < 0.45) {
    ctx.fillStyle = `rgba(255, 170, 90, ${(0.45 - sun) * 0.28})`;
    ctx.fillRect(0, 0, w, h);
  }

  const vignette = ctx.createRadialGradient(w / 2, h / 2, Math.min(w, h) * 0.35, w / 2, h / 2, Math.max(w, h) * 0.72);
  vignette.addColorStop(0, "rgba(0,0,0,0)");
  vignette.addColorStop(1, "rgba(0,0,0,0.38)");
  ctx.fillStyle = vignette;
  ctx.fillRect(0, 0, w, h);
  if (view.flash > 0) {
    ctx.fillStyle = `rgba(255, 244, 220, ${Math.min(0.75, view.flash)})`;
    ctx.fillRect(0, 0, w, h);
  }
}

function drawWater(ctx, x, y, tile, gx, gy, now) {
  const wave = Math.sin(now * 0.002 + gx * 0.7 + gy) * 0.5 + 0.5;
  ctx.strokeStyle = `rgba(220, 245, 255, ${0.15 + wave * 0.2})`;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(x + 3, y + tile * (0.35 + wave * 0.2));
  ctx.quadraticCurveTo(x + tile * 0.5, y + tile * (0.25 + wave * 0.25), x + tile - 3, y + tile * 0.45);
  ctx.stroke();
}

function drawGrass(ctx, x, y, tile, gx, gy) {
  ctx.strokeStyle = "rgba(18, 40, 16, 0.35)";
  ctx.lineWidth = 1;
  for (let i = 0; i < 3; i += 1) {
    const n = hash(gx * 13 + gy * 17 + i);
    const sx = x + n * tile;
    ctx.beginPath();
    ctx.moveTo(sx, y + tile * 0.75);
    ctx.lineTo(sx + 1, y + tile * (0.45 + n * 0.15));
    ctx.stroke();
  }
}

function drawBlooms(ctx, x, y, tile, gx, gy) {
  drawGrass(ctx, x, y, tile, gx, gy);
  const colors = ["#f2d0dc", "#f0e6a8", "#e7eef8", "#e8b4c4"];
  for (let i = 0; i < 3; i += 1) {
    const n = hash(gx * 19 + gy * 23 + i * 3);
    ctx.fillStyle = colors[Math.floor(hash(gx + i * gy) * colors.length) % colors.length];
    ctx.beginPath();
    ctx.arc(x + 4 + n * (tile - 8), y + 4 + hash(gy + i) * (tile - 8), Math.max(1.5, tile * 0.06), 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawSand(ctx, x, y, tile, gx, gy) {
  ctx.fillStyle = "rgba(255,255,255,0.15)";
  for (let i = 0; i < 4; i += 1) {
    const n = hash(gx * 3 + gy * 9 + i);
    ctx.fillRect(x + n * tile, y + hash(i * 11 + gx) * tile, 1.5, 1.5);
  }
}

function drawStone(ctx, x, y, tile, gx, gy) {
  ctx.fillStyle = "rgba(20, 16, 14, 0.25)";
  const n = hash(gx * 5 + gy);
  roundRect(ctx, x + tile * 0.2, y + tile * (0.25 + n * 0.2), tile * 0.55, tile * 0.28, 3);
  ctx.fill();
}

function drawStars(ctx, view, alpha) {
  ctx.fillStyle = `rgba(255, 248, 230, ${alpha})`;
  for (let i = 0; i < 40; i += 1) {
    const n = hash(i * 17 + 3);
    const m = hash(i * 29 + 9);
    ctx.globalAlpha = alpha * (0.3 + hash(i) * 0.7);
    ctx.fillRect(n * view.w, m * view.h * 0.55, i % 5 === 0 ? 2 : 1.2, i % 5 === 0 ? 2 : 1.2);
  }
  ctx.globalAlpha = 1;
}

function drawFirmament(ctx, state, view) {
  if (!state.flags.ritual_light) return;
  const sun = sunHeight(state.time);
  const margin = 36;
  if (state.flags.ritual_lights) {
    const day = clamp01((sun + 0.15) / 1.15);
    const x = margin + day * (view.w - margin * 2);
    const y = 78 + (1 - Math.sin(day * Math.PI)) * 70;
    const glow = ctx.createRadialGradient(x, y, 2, x, y, 48);
    glow.addColorStop(0, "rgba(255, 244, 210, 0.95)");
    glow.addColorStop(1, "rgba(255, 220, 140, 0)");
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(x, y, 48, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = sun > 0 ? "#fff6d8" : "#f4efe4";
    ctx.beginPath();
    ctx.arc(x, y, sun > 0 ? 11 : 8, 0, Math.PI * 2);
    ctx.fill();
  }
  if (state.flags.ritual_lights && sun < 0.2) {
    ctx.fillStyle = "rgba(232, 236, 245, 0.85)";
    ctx.beginPath();
    ctx.arc(view.w - 70, 64, 8, 0, Math.PI * 2);
    ctx.fill();
  }
}

function clamp01(n) {
  return Math.max(0, Math.min(1, n));
}

function drawEntity(ctx, state, entity, x, y, tile, now) {
  if (isTree(entity.kind)) drawTree(ctx, state, entity, x, y, tile, now);
  else if (entity.kind === "serpent") drawSerpent(ctx, x, y, tile, now);
  else if (entity.kind === "fish") drawFish(ctx, x, y, tile, now);
  else if (entity.kind === "bird") drawBird(ctx, x, y, tile, now);
  else if (entity.kind === "deer" || entity.kind === "sheep" || entity.kind === "lion") {
    drawBeast(ctx, entity, x, y, tile);
  } else if (entity.kind === "adam" || entity.kind === "eve") {
    drawHuman(ctx, state, entity, x, y, tile);
  }
}

function drawTree(ctx, state, entity, x, y, tile, now) {
  const scale = entity.kind === "tree" ? 0.42 : 0.55;
  const sway = Math.sin(now * 0.001 + x) * tile * 0.03;
  ctx.fillStyle = "#3a2a1c";
  roundRect(ctx, x - tile * 0.04, y - tile * 0.05, tile * 0.08, tile * 0.28, 2);
  ctx.fill();
  const radius = tile * scale;
  let color = "#2f6a34";
  if (entity.kind === "tree_life") color = "#7dba62";
  if (entity.kind === "tree_knowledge") color = "#2a5a38";
  if (entity.kind === "tree_life") {
    const glow = ctx.createRadialGradient(x + sway, y - radius * 0.6, 4, x, y, radius * 1.4);
    glow.addColorStop(0, "rgba(210, 255, 180, 0.45)");
    glow.addColorStop(1, "rgba(210, 255, 180, 0)");
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(x, y - radius * 0.4, radius * 1.3, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(x + sway, y - radius * 0.55, radius, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = entity.kind === "tree_life" ? "#a9d37a" : "#3e7a48";
  ctx.beginPath();
  ctx.arc(x - radius * 0.35 + sway, y - radius * 0.8, radius * 0.62, 0, Math.PI * 2);
  ctx.fill();
  if (entity.kind === "tree_knowledge" && !state.flags.tree_guarded) {
    ctx.fillStyle = "#c83b3b";
    for (let i = 0; i < 4; i += 1) {
      const n = hash(i * 19 + 4);
      ctx.beginPath();
      ctx.arc(x + (n - 0.5) * radius, y - radius * (0.3 + hash(i + 2) * 0.7), Math.max(2, tile * 0.045), 0, Math.PI * 2);
      ctx.fill();
    }
  }
}

function drawHuman(ctx, state, entity, x, y, tile) {
  const eve = entity.kind === "eve";
  const clothed = Boolean(state.flags.clothed);
  ctx.fillStyle = "rgba(0,0,0,0.2)";
  ctx.beginPath();
  ctx.ellipse(x, y + tile * 0.08, tile * 0.16, tile * 0.05, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = clothed ? "#cbb892" : eve ? "#6d8f5e" : "#8a4b30";
  roundRect(ctx, x - tile * 0.11, y - tile * 0.28, tile * 0.22, tile * 0.32, 6);
  ctx.fill();
  ctx.fillStyle = eve ? "#e0b08f" : "#c48b62";
  ctx.beginPath();
  ctx.arc(x, y - tile * 0.36, tile * 0.09, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = eve ? "#24160f" : "#2a2118";
  ctx.beginPath();
  if (eve) ctx.ellipse(x, y - tile * 0.4, tile * 0.1, tile * 0.12, 0, Math.PI, 0);
  else ctx.arc(x, y - tile * 0.4, tile * 0.09, Math.PI, 0, true);
  ctx.fill();
  if (state.mode === "walk") {
    ctx.fillStyle = "rgba(244, 236, 223, 0.92)";
    ctx.font = `${Math.max(11, tile * 0.16)}px Cormorant, Palatino, serif`;
    ctx.textAlign = "center";
    ctx.fillText(eve ? state.names.eve : state.names.adam, x, y - tile * 0.56);
    ctx.textAlign = "left";
  }
}

function drawBeast(ctx, entity, x, y, tile) {
  const color = entity.kind === "sheep" ? "#f3ecdf" : entity.kind === "lion" ? "#c48a3a" : "#8d5a34";
  ctx.fillStyle = "rgba(0,0,0,0.18)";
  ctx.beginPath();
  ctx.ellipse(x, y + tile * 0.06, tile * 0.16, tile * 0.04, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.ellipse(x, y - tile * 0.02, tile * 0.16, tile * 0.09, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(x + tile * 0.12, y - tile * 0.08, tile * 0.055, 0, Math.PI * 2);
  ctx.fill();
  if (entity.kind === "deer") {
    ctx.strokeStyle = "#efe6d2";
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.moveTo(x + tile * 0.12, y - tile * 0.12);
    ctx.lineTo(x + tile * 0.16, y - tile * 0.22);
    ctx.moveTo(x + tile * 0.1, y - tile * 0.12);
    ctx.lineTo(x + tile * 0.06, y - tile * 0.2);
    ctx.stroke();
  }
  if (entity.kind === "lion") {
    ctx.fillStyle = "#e2b15a";
    ctx.beginPath();
    ctx.arc(x + tile * 0.12, y - tile * 0.08, tile * 0.08, 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawFish(ctx, x, y, tile, now) {
  const wobble = Math.sin(now * 0.004 + x) * tile * 0.04;
  ctx.fillStyle = "#e0b45a";
  ctx.beginPath();
  ctx.ellipse(x, y + wobble, tile * 0.12, tile * 0.05, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.moveTo(x - tile * 0.12, y + wobble);
  ctx.lineTo(x - tile * 0.18, y + wobble - tile * 0.04);
  ctx.lineTo(x - tile * 0.18, y + wobble + tile * 0.04);
  ctx.fill();
}

function drawBird(ctx, x, y, tile, now) {
  const flap = Math.sin(now * 0.008 + y) * tile * 0.08;
  ctx.strokeStyle = "#f4f7fb";
  ctx.lineWidth = Math.max(1.2, tile * 0.035);
  ctx.beginPath();
  ctx.moveTo(x - tile * 0.14, y + flap);
  ctx.quadraticCurveTo(x, y - tile * 0.08, x + tile * 0.14, y + flap);
  ctx.stroke();
}

function drawSerpent(ctx, x, y, tile, now) {
  ctx.strokeStyle = "#7d9a4e";
  ctx.lineWidth = Math.max(2, tile * 0.06);
  ctx.lineCap = "round";
  ctx.beginPath();
  const phase = now * 0.003;
  ctx.moveTo(x - tile * 0.2, y);
  ctx.bezierCurveTo(
    x - tile * 0.05,
    y - tile * (0.12 + Math.sin(phase) * 0.04),
    x + tile * 0.05,
    y + tile * 0.1,
    x + tile * 0.18,
    y - tile * 0.02,
  );
  ctx.stroke();
  ctx.fillStyle = "#d6c16a";
  ctx.beginPath();
  ctx.arc(x + tile * 0.18, y - tile * 0.02, Math.max(2, tile * 0.035), 0, Math.PI * 2);
  ctx.fill();
}

function drawElyon(ctx, x, y, tile, now, facing) {
  const pulse = 0.75 + Math.sin(now * 0.003) * 0.25;
  const glow = ctx.createRadialGradient(x, y, 2, x, y, tile * 0.7);
  glow.addColorStop(0, `rgba(255, 236, 190, ${0.45 * pulse})`);
  glow.addColorStop(1, "rgba(255, 236, 190, 0)");
  ctx.fillStyle = glow;
  ctx.beginPath();
  ctx.arc(x, y, tile * 0.7, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "rgba(255, 248, 230, 0.95)";
  ctx.beginPath();
  ctx.moveTo(x, y - tile * 0.42);
  ctx.lineTo(x + tile * 0.16, y + tile * 0.16);
  ctx.lineTo(x - tile * 0.16, y + tile * 0.16);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "#e4c27a";
  ctx.beginPath();
  ctx.arc(x, y - tile * 0.3, tile * 0.06, 0, Math.PI * 2);
  ctx.fill();
  const lean = facing === "e" ? 3 : facing === "w" ? -3 : 0;
  ctx.fillStyle = "rgba(255,255,255,0.8)";
  ctx.fillRect(x - 1 + lean, y - tile * 0.22, 2, tile * 0.12);
}
