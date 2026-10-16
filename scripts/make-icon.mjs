import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";

const size = 512;
const raw = Buffer.alloc((size * 4 + 1) * size);

function plot(x, y, r, g, b, a = 255) {
  if (x < 0 || y < 0 || x >= size || y >= size) return;
  const i = y * (size * 4 + 1) + 1 + x * 4;
  const srcA = a / 255;
  const dstA = raw[i + 3] / 255;
  const outA = srcA + dstA * (1 - srcA);
  if (outA <= 0) return;
  raw[i] = Math.round((r * srcA + raw[i] * dstA * (1 - srcA)) / outA);
  raw[i + 1] = Math.round((g * srcA + raw[i + 1] * dstA * (1 - srcA)) / outA);
  raw[i + 2] = Math.round((b * srcA + raw[i + 2] * dstA * (1 - srcA)) / outA);
  raw[i + 3] = Math.round(outA * 255);
}

function disc(cx, cy, radius, color) {
  const [r, g, b] = color;
  const min = Math.max(0, Math.floor(cy - radius));
  const max = Math.min(size - 1, Math.ceil(cy + radius));
  for (let y = min; y <= max; y += 1) {
    for (let x = Math.max(0, Math.floor(cx - radius)); x <= Math.min(size - 1, Math.ceil(cx + radius)); x += 1) {
      if ((x - cx) ** 2 + (y - cy) ** 2 <= radius * radius) plot(x, y, r, g, b);
    }
  }
}

for (let y = 0; y < size; y += 1) {
  raw[y * (size * 4 + 1)] = 0;
  for (let x = 0; x < size; x += 1) plot(x, y, 18, 14, 12);
}

disc(256, 256, 214, [228, 194, 122]);
disc(256, 256, 196, [18, 14, 12]);
disc(256, 210, 86, [47, 107, 58]);
disc(214, 236, 52, [36, 92, 48]);
disc(300, 230, 46, [58, 122, 64]);
for (let y = 250; y < 390; y += 1) {
  for (let x = 240; x < 272; x += 1) plot(x, y, 141, 112, 64);
}
disc(256, 176, 14, [228, 194, 122]);

function chunk(type, data) {
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length);
  const body = Buffer.concat([Buffer.from(type), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body) >>> 0);
  return Buffer.concat([length, body, crc]);
}

function crc32(buffer) {
  let c = ~0;
  for (const byte of buffer) {
    c ^= byte;
    for (let bit = 0; bit < 8; bit += 1) c = (c >>> 1) ^ (0xedb88320 & -(c & 1));
  }
  return ~c;
}

const ihdr = Buffer.alloc(13);
ihdr.writeUInt32BE(size, 0);
ihdr.writeUInt32BE(size, 4);
ihdr[8] = 8;
ihdr[9] = 6;
const png = Buffer.concat([
  Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
  chunk("IHDR", ihdr),
  chunk("IDAT", zlib.deflateSync(raw, { level: 9 })),
  chunk("IEND", Buffer.alloc(0)),
]);

const root = path.join(import.meta.dirname, "..", "assets");
fs.mkdirSync(path.join(root, "icons"), { recursive: true });
fs.writeFileSync(path.join(root, "icon.png"), png);
for (const px of [16, 32, 48, 64, 128, 256, 512]) {
  fs.writeFileSync(path.join(root, "icons", `${px}x${px}.png`), px === 512 ? png : scale(png, px));
}

function scale(source, target) {
  const src = decode(source);
  const out = Buffer.alloc((target * 4 + 1) * target);
  for (let y = 0; y < target; y += 1) {
    out[y * (target * 4 + 1)] = 0;
    for (let x = 0; x < target; x += 1) {
      const sx = Math.min(511, Math.floor((x + 0.5) * (512 / target)));
      const sy = Math.min(511, Math.floor((y + 0.5) * (512 / target)));
      const si = sy * (512 * 4 + 1) + 1 + sx * 4;
      const di = y * (target * 4 + 1) + 1 + x * 4;
      out[di] = src[si];
      out[di + 1] = src[si + 1];
      out[di + 2] = src[si + 2];
      out[di + 3] = src[si + 3];
    }
  }
  const header = Buffer.alloc(13);
  header.writeUInt32BE(target, 0);
  header.writeUInt32BE(target, 4);
  header[8] = 8;
  header[9] = 6;
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk("IHDR", header),
    chunk("IDAT", zlib.deflateSync(out, { level: 9 })),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

function decode(buffer) {
  let offset = 8;
  const parts = [];
  while (offset < buffer.length) {
    const length = buffer.readUInt32BE(offset);
    const type = buffer.toString("ascii", offset + 4, offset + 8);
    const data = buffer.subarray(offset + 8, offset + 8 + length);
    if (type === "IDAT") parts.push(data);
    if (type === "IEND") break;
    offset += 12 + length;
  }
  return zlib.inflateSync(Buffer.concat(parts));
}
