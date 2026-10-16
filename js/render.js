/** Real-time Eden. Sky is a free camera. Walk is on the ground. */

import * as THREE from "../node_modules/three/build/three.module.js";
import { sunHeight } from "./sim.js";
import { TILE, WORLD_H, WORLD_W, isTree, tileAt } from "./world.js";

const orbit = { theta: 0.42, phi: 0.86, radius: 24 };
const look = { yaw: Math.PI, pitch: -0.08, pull: 2.6 };

let renderer = null;
let scene = null;
let camera = null;
let sun = null;
let sunTarget = null;
let hemi = null;
let moon = null;
let terrain = null;
let water = null;
let sky = null;
let beings = null;
let props = null;
let grass = null;
let flowers = null;
let playerBody = null;
let beam = null;
let hoverRing = null;
let motes = null;
let tileStamp = "";
let canvasRef = null;
const entityGroups = new Map();
const workGroups = new Map();

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();

function hash(n) {
  let x = Math.imul(n ^ 0x9e3779b9, 0x85ebca6b);
  x = Math.imul(x ^ (x >>> 13), 0xc2b2ae35);
  return ((x ^ (x >>> 16)) >>> 0) / 4294967296;
}

function tileHeight(tile) {
  switch (tile) {
    case TILE.DEEP: return -0.55;
    case TILE.WATER: return -0.22;
    case TILE.SAND: return 0.16;
    case TILE.STONE: return 0.72;
    case TILE.FLOWER: return 0.34;
    case TILE.GRASS: return 0.32;
    case TILE.NIGHT: return 0.08;
    default: return 0.02;
  }
}

function tileRgb(tile, n) {
  switch (tile) {
    case TILE.DEEP: return [0.05 + n * 0.02, 0.16, 0.22];
    case TILE.WATER: return [0.08, 0.32 + n * 0.05, 0.34];
    case TILE.SAND: return [0.62 + n * 0.08, 0.5, 0.28];
    case TILE.STONE: return [0.32 + n * 0.05, 0.3, 0.26];
    case TILE.FLOWER: return [0.22 + n * 0.06, 0.42, 0.16];
    case TILE.GRASS: return [0.16 + n * 0.08, 0.38 + n * 0.06, 0.12];
    case TILE.NIGHT: return [0.08 + n * 0.03, 0.1, 0.16];
    default: return [0.04, 0.035, 0.05];
  }
}

function boot(canvas) {
  if (renderer) return;
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  renderer.setClearColor(0x07060c, 1);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.08;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0xc5d4df, 16, 78);
  camera = new THREE.PerspectiveCamera(48, 1, 0.08, 240);

  hemi = new THREE.HemisphereLight(0xc5ddf2, 0x3a4a28, 0.55);
  scene.add(hemi);
  moon = new THREE.DirectionalLight(0x8aa4d4, 0.15);
  moon.position.set(-18, 22, 10);
  scene.add(moon);
  sun = new THREE.DirectionalLight(0xfff1d2, 1.6);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.camera.near = 2;
  sun.shadow.camera.far = 140;
  sun.shadow.camera.left = -36;
  sun.shadow.camera.right = 36;
  sun.shadow.camera.top = 28;
  sun.shadow.camera.bottom = -28;
  sun.shadow.bias = -0.00035;
  sun.shadow.normalBias = 0.045;
  scene.add(sun);
  sunTarget = new THREE.Object3D();
  sunTarget.position.set(WORLD_W / 2, 0.4, WORLD_H / 2);
  scene.add(sunTarget);
  sun.target = sunTarget;

  sky = new THREE.Mesh(
    new THREE.SphereGeometry(180, 28, 18),
    new THREE.ShaderMaterial({
      side: THREE.BackSide,
      depthWrite: false,
      uniforms: {
        uDay: { value: 1 },
        uSun: { value: new THREE.Vector3(0.2, 0.8, 0.2) },
      },
      vertexShader: `
        varying vec3 vDir;
        void main() {
          vDir = position;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        varying vec3 vDir;
        uniform float uDay;
        uniform vec3 uSun;
        void main() {
          vec3 dir = normalize(vDir);
          float h = dir.y;
          vec3 nightZ = vec3(0.015, 0.02, 0.05);
          vec3 nightH = vec3(0.08, 0.09, 0.16);
          vec3 dayZ = vec3(0.22, 0.48, 0.78);
          vec3 dayH = vec3(0.78, 0.84, 0.86);
          vec3 zenith = mix(nightZ, dayZ, uDay);
          vec3 horizon = mix(nightH, dayH, uDay);
          vec3 col = mix(horizon, zenith, smoothstep(-0.08, 0.55, h));
          float glow = pow(max(dot(dir, normalize(uSun)), 0.0), 90.0);
          float disc = pow(max(dot(dir, normalize(uSun)), 0.0), 900.0);
          col += vec3(1.0, 0.72, 0.4) * glow * uDay;
          col += vec3(1.0, 0.95, 0.8) * disc;
          float stars = step(0.992, fract(sin(dot(floor(dir * 220.0), vec3(12.9, 78.2, 37.1))) * 43758.5));
          col += stars * (1.0 - uDay) * smoothstep(0.0, 0.4, h);
          gl_FragColor = vec4(col, 1.0);
        }
      `,
    }),
  );
  sky.position.set(WORLD_W / 2, 0, WORLD_H / 2);
  sky.frustumCulled = false;
  scene.add(sky);

  beings = new THREE.Group();
  props = new THREE.Group();
  scene.add(beings, props);

  const robe = new THREE.MeshStandardMaterial({ color: 0xf4e2b8, roughness: 0.72, metalness: 0.02 });
  playerBody = makeHuman(robe, 0x2a2118, 1);
  playerBody.traverse((child) => {
    child.castShadow = true;
  });
  scene.add(playerBody);
  beam = new THREE.Mesh(
    new THREE.CylinderGeometry(0.18, 0.55, 8, 12, 1, true),
    new THREE.MeshBasicMaterial({ color: 0xf0d7a2, transparent: true, opacity: 0.28, depthWrite: false }),
  );
  beam.position.y = 4;
  scene.add(beam);

  hoverRing = new THREE.Mesh(
    new THREE.RingGeometry(0.38, 0.48, 24),
    new THREE.MeshBasicMaterial({ color: 0xe4c27a, side: THREE.DoubleSide, transparent: true, opacity: 0.85 }),
  );
  hoverRing.rotation.x = -Math.PI / 2;
  hoverRing.visible = false;
  scene.add(hoverRing);

  const moteGeo = new THREE.BufferGeometry();
  const motePos = new Float32Array(80 * 3);
  for (let i = 0; i < 80; i += 1) {
    motePos[i * 3] = (hash(i + 3) - 0.5) * 6;
    motePos[i * 3 + 1] = hash(i + 9) * 3;
    motePos[i * 3 + 2] = (hash(i + 17) - 0.5) * 6;
  }
  moteGeo.setAttribute("position", new THREE.BufferAttribute(motePos, 3));
  motes = new THREE.Points(moteGeo, new THREE.PointsMaterial({ color: 0xf6e2a8, size: 0.08, transparent: true, opacity: 0 }));
  scene.add(motes);
  canvasRef = canvas;
}

export function resize(cssW, cssH) {
  if (!renderer || !camera) return;
  const dpr = Math.min(window.devicePixelRatio || 1, 1.75);
  renderer.setPixelRatio(dpr);
  renderer.setSize(Math.max(1, cssW), Math.max(1, cssH), false);
  camera.aspect = cssW / Math.max(1, cssH);
  camera.updateProjectionMatrix();
}

export function orbitBy(dx, dy) {
  orbit.theta -= dx * 0.005;
  orbit.phi = Math.max(0.38, Math.min(1.28, orbit.phi - dy * 0.0035));
}

export function lookBy(dx, dy) {
  look.yaw -= dx * 0.0045;
  look.pitch = Math.max(-0.7, Math.min(0.45, look.pitch - dy * 0.003));
}

export function zoomBy(delta, mode) {
  if (mode === "walk") look.pull = Math.max(0.35, Math.min(7, look.pull + (delta > 0 ? 0.35 : -0.35)));
  else orbit.radius = Math.max(8, Math.min(62, orbit.radius + (delta > 0 ? 1.6 : -1.6)));
}

export function walkAxes() {
  return {
    fx: Math.sin(look.yaw),
    fy: Math.cos(look.yaw),
    rx: Math.cos(look.yaw),
    ry: -Math.sin(look.yaw),
  };
}

function sampleHeight(state, x, z) {
  const tile = tileAt(state.world, Math.floor(x), Math.floor(z));
  const n = hash(Math.floor(x) * 17 + Math.floor(z) * 29) * 0.06;
  return tileHeight(tile) + (tile === TILE.WATER || tile === TILE.DEEP ? 0 : n);
}

function rebuildTerrain(state) {
  const tiles = state.world.tiles;
  const positions = [];
  const colors = [];
  const indices = [];
  const waterPos = [];
  const waterIdx = [];
  const cols = WORLD_W + 1;
  const heightAt = (x, z) => {
    let h = 0;
    let c = 0;
    for (let dz = -1; dz <= 0; dz += 1) {
      for (let dx = -1; dx <= 0; dx += 1) {
        const tx = Math.min(WORLD_W - 1, Math.max(0, x + dx));
        const tz = Math.min(WORLD_H - 1, Math.max(0, z + dz));
        h += tileHeight(tiles[tz * WORLD_W + tx]);
        c += 1;
      }
    }
    return h / c + hash(x * 13 + z * 19) * 0.05;
  };
  const colorAt = (x, z) => {
    const tx = Math.min(WORLD_W - 1, Math.max(0, x));
    const tz = Math.min(WORLD_H - 1, Math.max(0, z));
    return tileRgb(tiles[tz * WORLD_W + tx], hash(x * 3 + z * 11));
  };
  for (let z = 0; z <= WORLD_H; z += 1) {
    for (let x = 0; x <= WORLD_W; x += 1) {
      positions.push(x, heightAt(x, z), z);
      colors.push(...colorAt(x, z));
    }
  }
  for (let z = 0; z < WORLD_H; z += 1) {
    for (let x = 0; x < WORLD_W; x += 1) {
      const a = z * cols + x;
      indices.push(a, a + cols, a + 1, a + 1, a + cols, a + cols + 1);
      const tile = tiles[z * WORLD_W + x];
      if (tile === TILE.WATER || tile === TILE.DEEP) {
        const base = waterPos.length / 3;
        const y = tile === TILE.DEEP ? -0.18 : -0.02;
        waterPos.push(x, y, z, x + 1, y, z, x + 1, y, z + 1, x, y, z + 1);
        waterIdx.push(base, base + 1, base + 2, base, base + 2, base + 3);
      }
    }
  }
  if (terrain) {
    terrain.geometry.dispose();
    scene.remove(terrain);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geo.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  geo.setIndex(indices);
  geo.computeVertexNormals();
  terrain = new THREE.Mesh(
    geo,
    new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.92, metalness: 0.02 }),
  );
  terrain.receiveShadow = true;
  terrain.castShadow = true;
  scene.add(terrain);

  if (water) {
    water.geometry.dispose();
    scene.remove(water);
    water = null;
  }
  if (waterPos.length) {
    const wgeo = new THREE.BufferGeometry();
    wgeo.setAttribute("position", new THREE.Float32BufferAttribute(waterPos, 3));
    wgeo.setIndex(waterIdx);
    wgeo.computeVertexNormals();
    water = new THREE.Mesh(
      wgeo,
      new THREE.MeshStandardMaterial({
        color: 0x1c7c86,
        roughness: 0.18,
        metalness: 0.08,
        transparent: true,
        opacity: 0.78,
      }),
    );
    water.receiveShadow = true;
    scene.add(water);
  }
  scatterCover(state);
}

function scatterCover(state) {
  if (grass) {
    grass.geometry.dispose();
    grass.material.dispose();
    scene.remove(grass);
  }
  if (flowers) {
    flowers.geometry.dispose();
    flowers.material.dispose();
    scene.remove(flowers);
  }
  const grassSpots = [];
  const flowerSpots = [];
  for (let z = 0; z < WORLD_H; z += 1) {
    for (let x = 0; x < WORLD_W; x += 1) {
      const tile = state.world.tiles[z * WORLD_W + x];
      if (tile === TILE.GRASS && hash(x * 19 + z * 7) > 0.42) {
        grassSpots.push([x + 0.2 + hash(x + z) * 0.6, tileHeight(tile), z + 0.2 + hash(z * 3 + x) * 0.6, 0.7 + hash(x * z + 4) * 0.8]);
      }
      if (tile === TILE.FLOWER) {
        flowerSpots.push([x + 0.5, tileHeight(tile) + 0.08, z + 0.5]);
      }
    }
  }
  const cone = new THREE.ConeGeometry(0.08, 0.42, 4);
  grass = new THREE.InstancedMesh(cone, new THREE.MeshStandardMaterial({ color: 0x3d7a32, roughness: 0.9 }), Math.max(1, grassSpots.length));
  grass.castShadow = true;
  grass.receiveShadow = true;
  const dummy = new THREE.Object3D();
  grassSpots.forEach((spot, index) => {
    dummy.position.set(spot[0], spot[1] + spot[3] * 0.18, spot[2]);
    dummy.scale.set(1, spot[3], 1);
    dummy.rotation.y = hash(index + 8) * Math.PI;
    dummy.updateMatrix();
    grass.setMatrixAt(index, dummy.matrix);
  });
  grass.count = grassSpots.length;
  grass.instanceMatrix.needsUpdate = true;
  grass.visible = grassSpots.length > 0;
  scene.add(grass);
  const bud = new THREE.SphereGeometry(0.1, 8, 6);
  flowers = new THREE.InstancedMesh(bud, new THREE.MeshStandardMaterial({ color: 0xe7d27a, roughness: 0.6 }), Math.max(1, flowerSpots.length));
  flowerSpots.forEach((spot, index) => {
    dummy.position.set(spot[0], spot[1], spot[2]);
    dummy.scale.set(1, 1, 1);
    dummy.rotation.set(0, 0, 0);
    dummy.updateMatrix();
    flowers.setMatrixAt(index, dummy.matrix);
  });
  flowers.count = flowerSpots.length;
  flowers.instanceMatrix.needsUpdate = true;
  flowers.visible = flowerSpots.length > 0;
  scene.add(flowers);
}

function makeHuman(cloth, hairColor, scale) {
  const group = new THREE.Group();
  const robe = new THREE.Mesh(new THREE.CylinderGeometry(0.22 * scale, 0.34 * scale, 0.95 * scale, 10), cloth);
  robe.position.y = 0.62 * scale;
  robe.castShadow = true;
  const head = new THREE.Mesh(
    new THREE.SphereGeometry(0.16 * scale, 12, 10),
    new THREE.MeshStandardMaterial({ color: 0xd7b394, roughness: 0.7 }),
  );
  head.position.y = 1.28 * scale;
  head.castShadow = true;
  const hair = new THREE.Mesh(
    new THREE.SphereGeometry(0.17 * scale, 10, 8),
    new THREE.MeshStandardMaterial({ color: hairColor, roughness: 0.8 }),
  );
  hair.position.y = 1.36 * scale;
  hair.scale.set(1, 0.7, 1);
  const armGeo = new THREE.CapsuleGeometry(0.05 * scale, 0.38 * scale, 2, 6);
  const armMat = cloth;
  const left = new THREE.Mesh(armGeo, armMat);
  const right = new THREE.Mesh(armGeo, armMat);
  left.position.set(-0.28 * scale, 0.85 * scale, 0);
  right.position.set(0.28 * scale, 0.85 * scale, 0);
  left.rotation.z = 0.25;
  right.rotation.z = -0.25;
  left.castShadow = true;
  right.castShadow = true;
  group.add(robe, head, hair, left, right);
  return group;
}

function makeTree(kind, salt) {
  const group = new THREE.Group();
  const trunk = new THREE.Mesh(
    new THREE.CylinderGeometry(0.1, 0.16, 1.15, 7),
    new THREE.MeshStandardMaterial({ color: 0x5a3b24, roughness: 0.9 }),
  );
  trunk.position.y = 0.55;
  trunk.castShadow = true;
  const leaf = kind === "tree_knowledge" ? 0x8d4a3a : kind === "tree_life" ? 0x2f8a45 : 0x2f6b32;
  const canopy = new THREE.Mesh(
    new THREE.SphereGeometry(0.7 + hash(salt) * 0.35, 10, 8),
    new THREE.MeshStandardMaterial({ color: leaf, roughness: 0.82 }),
  );
  canopy.position.y = 1.55 + hash(salt + 2) * 0.4;
  canopy.scale.y = 0.85;
  canopy.castShadow = true;
  group.add(trunk, canopy);
  if (kind === "tree_knowledge") {
    const fruit = new THREE.Mesh(
      new THREE.SphereGeometry(0.08, 8, 6),
      new THREE.MeshStandardMaterial({ color: 0xd4a24a, emissive: 0x3a2508, roughness: 0.4 }),
    );
    fruit.position.set(0.25, 1.4, 0.2);
    group.add(fruit);
  }
  return group;
}

function makeBeast(kind) {
  const group = new THREE.Group();
  const color = kind === "sheep" ? 0xe7e1d6 : kind === "lion" ? 0xc48a3a : kind === "bird" ? 0xd8d2c4 : kind === "fish" ? 0x4aa3b5 : 0x7a5433;
  const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.78 });
  const body = new THREE.Mesh(new THREE.SphereGeometry(kind === "lion" ? 0.38 : 0.28, 10, 8), mat);
  body.scale.set(1.35, 0.75, 0.8);
  body.position.y = kind === "fish" ? 0.12 : kind === "bird" ? 0.2 : 0.38;
  body.castShadow = true;
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.14, 8, 6), mat);
  head.position.set(0, body.position.y + 0.12, 0.32);
  group.add(body, head);
  if (kind !== "fish" && kind !== "bird") {
    for (const side of [-0.12, 0.12]) {
      for (const z of [-0.12, 0.16]) {
        const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.04, 0.28, 5), mat);
        leg.position.set(side, 0.14, z);
        leg.castShadow = true;
        group.add(leg);
      }
    }
  }
  return group;
}

function makeSerpent() {
  const group = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({ color: 0x6f8f4a, roughness: 0.55, metalness: 0.08 });
  for (let i = 0; i < 6; i += 1) {
    const seg = new THREE.Mesh(new THREE.SphereGeometry(0.1 - i * 0.008, 8, 6), mat);
    seg.position.set(Math.sin(i) * 0.05, 0.1, -i * 0.16);
    seg.castShadow = true;
    group.add(seg);
  }
  return group;
}

function makeWork(label) {
  const group = new THREE.Group();
  const text = label.toLowerCase();
  let mesh;
  if (text.includes("mat") || text.includes("reed")) {
    mesh = new THREE.Mesh(
      new THREE.BoxGeometry(0.7, 0.05, 0.45),
      new THREE.MeshStandardMaterial({ color: 0xb08958, roughness: 0.9 }),
    );
    mesh.position.y = 0.04;
  } else if (text.includes("stone") || text.includes("ring")) {
    mesh = new THREE.Mesh(
      new THREE.TorusGeometry(0.28, 0.07, 6, 10),
      new THREE.MeshStandardMaterial({ color: 0x8d887c, roughness: 0.85 }),
    );
    mesh.rotation.x = Math.PI / 2;
    mesh.position.y = 0.08;
  } else if (text.includes("plant") || text.includes("tend") || text.includes("flower") || text.includes("herb")) {
    mesh = new THREE.Mesh(
      new THREE.ConeGeometry(0.12, 0.45, 6),
      new THREE.MeshStandardMaterial({ color: 0x3f8f45, roughness: 0.8 }),
    );
    mesh.position.y = 0.24;
  } else {
    mesh = new THREE.Mesh(
      new THREE.BoxGeometry(0.36, 0.28, 0.36),
      new THREE.MeshStandardMaterial({ color: 0x8a5a32, roughness: 0.78 }),
    );
    mesh.position.y = 0.16;
  }
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  group.add(mesh);
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 64;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, 256, 64);
  ctx.fillStyle = "rgba(12,9,8,0.72)";
  ctx.fillRect(8, 8, 240, 48);
  ctx.fillStyle = "#f4ecdf";
  ctx.font = "24px Palatino, Georgia, serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(label.slice(0, 28), 128, 32);
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), transparent: true }));
  sprite.position.y = 0.85;
  sprite.scale.set(1.6, 0.4, 1);
  group.add(sprite);
  return group;
}

function facingYaw(facing) {
  if (facing === "n") return Math.PI;
  if (facing === "e") return Math.PI / 2;
  if (facing === "w") return -Math.PI / 2;
  return 0;
}

function syncEntities(state, now) {
  const live = new Set();
  for (const entity of state.world.entities) {
    if (entity.kind === "serpent" && (state.flags.serpent_gone || !state.flags.serpent_present)) continue;
    live.add(entity.id);
    let group = entityGroups.get(entity.id);
    if (!group) {
      if (entity.kind === "adam") group = makeHuman(new THREE.MeshStandardMaterial({ color: 0xc4a574, roughness: 0.75 }), 0x2a2118, 1.05);
      else if (entity.kind === "eve") group = makeHuman(new THREE.MeshStandardMaterial({ color: 0xd8c2ae, roughness: 0.72 }), 0x3a2418, 1);
      else if (isTree(entity.kind)) group = makeTree(entity.kind, entity.x * 10 + entity.y);
      else if (entity.kind === "serpent") group = makeSerpent();
      else group = makeBeast(entity.kind);
      group.userData.eid = entity.id;
      group.traverse((child) => {
        child.userData.eid = entity.id;
        if (child.isMesh) child.castShadow = true;
      });
      const reach = entity.kind === "adam" || entity.kind === "eve" ? 0.7 : isTree(entity.kind) ? 0 : 0.45;
      if (reach) {
        const sensor = new THREE.Mesh(
          new THREE.CylinderGeometry(reach, reach, 2.4, 8),
          new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }),
        );
        sensor.position.y = 1.1;
        sensor.userData.eid = entity.id;
        group.add(sensor);
      }
      beings.add(group);
      entityGroups.set(entity.id, group);
    }
    const y = sampleHeight(state, entity.x, entity.y);
    const bob = entity.kind === "bird" ? 1.8 + Math.sin(now / 500 + entity.x) * 0.25 : entity.kind === "fish" ? 0.05 : 0;
    group.position.set(entity.x, y + bob, entity.y);
    group.rotation.y = facingYaw(entity.facing);
  }
  for (const [id, group] of entityGroups) {
    if (live.has(id)) continue;
    beings.remove(group);
    entityGroups.delete(id);
  }
}

function syncWorks(state) {
  const live = new Set();
  for (const work of state.works || []) {
    live.add(work.id);
    let group = workGroups.get(work.id);
    if (!group) {
      group = makeWork(work.label);
      props.add(group);
      workGroups.set(work.id, group);
    }
    group.position.set(work.x, sampleHeight(state, work.x, work.y), work.y);
  }
  for (const [id, group] of workGroups) {
    if (live.has(id)) continue;
    props.remove(group);
    workGroups.delete(id);
  }
}

function frameCamera(state) {
  const walk = state.mode === "walk";
  scene.fog.near = walk ? 8 : 28;
  scene.fog.far = walk ? 42 : 96;
  if (!walk) {
    const cx = WORLD_W / 2;
    const cz = WORLD_H / 2;
    const x = cx + orbit.radius * Math.sin(orbit.phi) * Math.sin(orbit.theta);
    const y = 2 + orbit.radius * Math.cos(orbit.phi);
    const z = cz + orbit.radius * Math.sin(orbit.phi) * Math.cos(orbit.theta);
    camera.position.set(x, Math.max(1.4, y), z);
    camera.lookAt(cx, 0.6, cz);
    return;
  }
  const fx = Math.sin(look.yaw);
  const fz = Math.cos(look.yaw);
  const eye = 1.62 + look.pitch * 0.4;
  const px = state.player.x;
  const pz = state.player.y;
  const py = sampleHeight(state, px, pz);
  camera.position.set(px - fx * look.pull, py + eye, pz - fz * look.pull);
  camera.lookAt(px + fx * 6, py + eye + look.pitch * 2.2, pz + fz * 6);
}

function frameLight(state, flash) {
  const lit = Boolean(state.flags.ritual_light);
  const elev = lit ? sunHeight(state.time) : -0.35;
  const day = lit ? THREE.MathUtils.clamp((elev + 0.08) / 0.85, 0.08, 1) : 0.02;
  const az = state.time * Math.PI * 2;
  sun.position.set(
    WORLD_W / 2 + Math.cos(az) * 46,
    6 + Math.max(0.15, elev) * 40,
    WORLD_H / 2 + Math.sin(az) * 24,
  );
  sun.intensity = 0.15 + day * 2.15 + flash * 1.4;
  sun.color.set(day > 0.35 ? 0xfff1d0 : 0xffb27a);
  hemi.intensity = 0.18 + day * 0.55;
  moon.intensity = (1 - day) * 0.35;
  sky.material.uniforms.uDay.value = day;
  sky.material.uniforms.uSun.value.copy(sun.position).sub(sky.position).normalize();
  const fogColor = new THREE.Color().setRGB(0.08 + day * 0.62, 0.1 + day * 0.68, 0.16 + day * 0.7);
  scene.fog.color.copy(fogColor);
  renderer.toneMappingExposure = 0.92 + day * 0.22 + flash * 0.65;
}

export function pick(clientX, clientY) {
  if (!renderer || !camera || !canvasRef) return null;
  const rect = canvasRef.getBoundingClientRect();
  if (!rect.width || !rect.height) return null;
  pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const beingHits = raycaster.intersectObjects(beings.children, true);
  if (beingHits.length) {
    let node = beingHits[0].object;
    while (node && !node.userData.eid) node = node.parent;
    const id = node?.userData.eid;
    const group = id ? entityGroups.get(id) : null;
    if (group) return { x: Math.floor(group.position.x), y: Math.floor(group.position.z), id };
  }
  const ground = [];
  if (terrain) ground.push(terrain);
  if (water) ground.push(water);
  const hit = raycaster.intersectObjects(ground, false)[0];
  if (!hit) return null;
  return { x: Math.floor(hit.point.x), y: Math.floor(hit.point.z) };
}

let fitted = "";

export function render(canvas, state, view) {
  boot(canvas);
  const w = view.w || window.innerWidth;
  const h = view.h || window.innerHeight;
  const fit = `${Math.round(w)}x${Math.round(h)}`;
  if (fit !== fitted) {
    fitted = fit;
    resize(w, h);
  }
  const stamp = `${state.world.tiles.join(",")}`;
  if (stamp !== tileStamp) {
    tileStamp = stamp;
    rebuildTerrain(state);
  }
  syncEntities(state, view.now || 0);
  syncWorks(state);
  const py = sampleHeight(state, state.player.x, state.player.y);
  playerBody.position.set(state.player.x, py, state.player.y);
  playerBody.rotation.y = look.yaw;
  playerBody.visible = state.mode === "walk";
  beam.position.set(state.player.x, 4, state.player.y);
  beam.visible = state.mode !== "walk";
  if (view.hover && view.hover.x >= 0 && view.hover.y >= 0 && view.hover.x < WORLD_W && view.hover.y < WORLD_H) {
    hoverRing.visible = true;
    hoverRing.position.set(view.hover.x + 0.5, sampleHeight(state, view.hover.x + 0.5, view.hover.y + 0.5) + 0.08, view.hover.y + 0.5);
  } else hoverRing.visible = false;
  motes.position.set(state.player.x, py, state.player.y);
  motes.material.opacity = Math.max(0, view.flash || 0) * 0.9;
  frameCamera(state);
  frameLight(state, view.flash || 0);
  renderer.render(scene, camera);
}
