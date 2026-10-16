/** Tile map and entity layout for Eden. */

export const WORLD_W = 42;
export const WORLD_H = 30;

export const TILE = {
  CHAOS: 0,
  NIGHT: 1,
  WATER: 2,
  DEEP: 3,
  SAND: 4,
  GRASS: 5,
  STONE: 6,
  FLOWER: 7,
};

export const TILE_NAME = {
  0: "chaos",
  1: "night",
  2: "water",
  3: "deep",
  4: "sand",
  5: "grass",
  6: "stone",
  7: "flower",
};

export const WALKABLE = new Set([TILE.NIGHT, TILE.SAND, TILE.GRASS, TILE.FLOWER]);

export const SPOT = {
  adam: { x: 20.5, y: 14.5 },
  eve: { x: 21.7, y: 14.5 },
  life: { x: 14.5, y: 14.5 },
  knowledge: { x: 27.5, y: 13.5 },
  descend: { x: 20.5, y: 17.4 },
};

const RESERVED = new Set(["14,14", "20,14", "21,14", "19,14", "20,13", "20,15", "27,13", "26,13", "28,13"]);

export function idx(x, y) {
  return y * WORLD_W + x;
}

export function inBounds(x, y) {
  return x >= 0 && y >= 0 && x < WORLD_W && y < WORLD_H;
}

export function createWorld() {
  return {
    w: WORLD_W,
    h: WORLD_H,
    tiles: Array.from({ length: WORLD_W * WORLD_H }, () => TILE.CHAOS),
    entities: [],
  };
}

export function tileAt(world, x, y) {
  if (!inBounds(x, y)) return TILE.STONE;
  return world.tiles[idx(x, y)];
}

export function setTile(world, x, y, tile) {
  if (!inBounds(x, y)) return false;
  world.tiles[idx(x, y)] = tile;
  return true;
}

export function entityAt(world, x, y, pred) {
  const tx = Math.floor(x);
  const ty = Math.floor(y);
  return world.entities.find((e) => Math.floor(e.x) === tx && Math.floor(e.y) === ty && (!pred || pred(e))) || null;
}

export function findKind(world, kind) {
  return world.entities.find((e) => e.kind === kind) || null;
}

export function isTree(kind) {
  return kind === "tree" || kind === "tree_life" || kind === "tree_knowledge";
}

export function isCreature(kind) {
  return kind === "fish" || kind === "bird" || kind === "deer" || kind === "sheep" || kind === "lion";
}

export function blocksFoot(world, x, y) {
  const tile = tileAt(world, Math.floor(x), Math.floor(y));
  if (!WALKABLE.has(tile)) return true;
  const tree = entityAt(world, x, y, (e) => isTree(e.kind));
  return Boolean(tree);
}

function spawn(world, partial) {
  world.entities.push({
    pause: 0,
    tx: partial.x,
    ty: partial.y,
    facing: "s",
    name: "",
    ...partial,
  });
}

export function fillNight(world) {
  for (let i = 0; i < world.tiles.length; i += 1) {
    if (world.tiles[i] === TILE.CHAOS) world.tiles[i] = TILE.NIGHT;
  }
}

export function carveWaters(world) {
  for (let y = 26; y < WORLD_H; y += 1) {
    for (let x = 0; x < WORLD_W; x += 1) {
      setTile(world, x, y, y > 27 ? TILE.DEEP : TILE.WATER);
    }
  }
  let x = 32;
  for (let y = 1; y < 27; y += 1) {
    if (y % 5 === 0) x += y % 10 === 0 ? -1 : 1;
    x = Math.max(29, Math.min(WORLD_W - 2, x));
    setTile(world, x, y, TILE.WATER);
    setTile(world, x + 1, y, TILE.DEEP);
  }
  const lx = 8;
  const ly = 18;
  for (let y = ly - 2; y <= ly + 2; y += 1) {
    for (let x2 = lx - 3; x2 <= lx + 3; x2 += 1) {
      const dx = (x2 - lx) / 3;
      const dy = (y - ly) / 2.2;
      if (dx * dx + dy * dy <= 1) setTile(world, x2, y, TILE.WATER);
    }
  }
}

export function raiseLand(world) {
  for (let y = 0; y < WORLD_H; y += 1) {
    for (let x = 0; x < WORLD_W; x += 1) {
      const t = tileAt(world, x, y);
      if (y <= 1 && t === TILE.NIGHT) {
        setTile(world, x, y, TILE.STONE);
        continue;
      }
      if (t === TILE.NIGHT) setTile(world, x, y, TILE.GRASS);
    }
  }
  for (let y = 0; y < WORLD_H; y += 1) {
    for (let x = 0; x < WORLD_W; x += 1) {
      if (tileAt(world, x, y) !== TILE.GRASS) continue;
      const shore =
        tileAt(world, x + 1, y) === TILE.WATER ||
        tileAt(world, x - 1, y) === TILE.WATER ||
        tileAt(world, x, y + 1) === TILE.WATER ||
        tileAt(world, x, y - 1) === TILE.WATER ||
        tileAt(world, x, y + 1) === TILE.DEEP;
      if (shore) setTile(world, x, y, TILE.SAND);
    }
  }
  // A clearing of grass around the people and the two trees, even if shore logic touched them.
  for (const key of ["20,14", "21,14", "19,14", "20,13", "20,15", "14,14", "27,13", "26,13"]) {
    const [sx, sy] = key.split(",").map(Number);
    if (tileAt(world, sx, sy) === TILE.SAND || tileAt(world, sx, sy) === TILE.NIGHT) {
      setTile(world, sx, sy, TILE.GRASS);
    }
  }
}

function scatterFlowers(world, rand) {
  let placed = 0;
  let guard = 0;
  while (placed < 28 && guard < 400) {
    guard += 1;
    const x = 4 + Math.floor(rand() * (WORLD_W - 8));
    const y = 4 + Math.floor(rand() * 20);
    if (RESERVED.has(`${x},${y}`)) continue;
    if (tileAt(world, x, y) !== TILE.GRASS) continue;
    setTile(world, x, y, TILE.FLOWER);
    placed += 1;
  }
}

export function plantGrove(world, rand) {
  scatterFlowers(world, rand);
  spawn(world, { id: "tree_life", kind: "tree_life", x: SPOT.life.x, y: SPOT.life.y });
  spawn(world, { id: "tree_knowledge", kind: "tree_knowledge", x: SPOT.knowledge.x, y: SPOT.knowledge.y });
  let placed = 0;
  let guard = 0;
  while (placed < 16 && guard < 500) {
    guard += 1;
    const x = 3 + Math.floor(rand() * (WORLD_W - 6));
    const y = 3 + Math.floor(rand() * 21);
    if (RESERVED.has(`${x},${y}`)) continue;
    if (tileAt(world, x, y) !== TILE.GRASS && tileAt(world, x, y) !== TILE.FLOWER) continue;
    if (entityAt(world, x + 0.5, y + 0.5, (e) => isTree(e.kind))) continue;
    spawn(world, { id: `tree_${x}_${y}`, kind: "tree", x: x + 0.5, y: y + 0.5 });
    placed += 1;
  }
}

function randomWater(world, rand) {
  for (let n = 0; n < 80; n += 1) {
    const x = Math.floor(rand() * WORLD_W);
    const y = Math.floor(rand() * WORLD_H);
    const t = tileAt(world, x, y);
    if (t === TILE.WATER || t === TILE.DEEP) return { x: x + 0.5, y: y + 0.5 };
  }
  return { x: 10.5, y: 28.5 };
}

function randomLand(world, rand) {
  for (let n = 0; n < 80; n += 1) {
    const x = 2 + Math.floor(rand() * (WORLD_W - 4));
    const y = 3 + Math.floor(rand() * 20);
    if (RESERVED.has(`${x},${y}`)) continue;
    const t = tileAt(world, x, y);
    if (t === TILE.GRASS || t === TILE.FLOWER || t === TILE.SAND) {
      if (entityAt(world, x + 0.5, y + 0.5)) continue;
      return { x: x + 0.5, y: y + 0.5 };
    }
  }
  return { x: 18.5, y: 16.5 };
}

export function seedCreatures(world, rand, nextId) {
  const plan = [
    ["fish", 4],
    ["bird", 3],
    ["deer", 2],
    ["sheep", 2],
    ["lion", 1],
  ];
  for (const [kind, count] of plan) {
    for (let i = 0; i < count; i += 1) {
      const spot = kind === "fish" ? randomWater(world, rand) : randomLand(world, rand);
      const id = nextId();
      spawn(world, { id, kind, x: spot.x, y: spot.y, tx: spot.x, ty: spot.y });
    }
  }
}

export function placeHuman(world, kind) {
  if (findKind(world, kind)) return null;
  const spot = kind === "eve" ? SPOT.eve : SPOT.adam;
  const id = kind;
  spawn(world, { id, kind, x: spot.x, y: spot.y, homeX: spot.x, homeY: spot.y });
  return id;
}

export function placeSerpent(world) {
  if (findKind(world, "serpent")) return;
  const tree = findKind(world, "tree_knowledge");
  const x = tree ? tree.x + 0.15 : SPOT.knowledge.x;
  const y = tree ? tree.y + 0.35 : SPOT.knowledge.y;
  spawn(world, { id: "serpent", kind: "serpent", x, y, tx: x, ty: y });
}

export function countTiles(world, tile) {
  let n = 0;
  for (const t of world.tiles) if (t === tile) n += 1;
  return n;
}

export function countKind(world, kind) {
  return world.entities.filter((e) => e.kind === kind).length;
}
