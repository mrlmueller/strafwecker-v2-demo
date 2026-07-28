/**
 * Regenerate PWA + Apple icons + favicon from public/icon.svg.
 * Run: `npm run build:icons`
 */
import sharp from "sharp";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
const svgPath = resolve(root, "public/icon.svg");

const targets = [
  { size: 192, out: "public/icon-192.png" },
  { size: 512, out: "public/icon-512.png" },
  { size: 180, out: "public/apple-touch-icon.png" },
  // 32x32 PNG renamed as .ico — modern browsers accept PNG-in-ICO.
  { size: 32, out: "app/favicon.ico" },
];

const svg = await readFile(svgPath);
console.log(`source: ${svgPath} (${svg.byteLength} bytes)`);

for (const t of targets) {
  const outPath = resolve(root, t.out);
  await mkdir(dirname(outPath), { recursive: true });
  const buf = await sharp(svg, { density: 384 })
    .resize(t.size, t.size, { fit: "contain" })
    .png({ compressionLevel: 9 })
    .toBuffer();
  await writeFile(outPath, buf);
  console.log(`  → ${t.out}  ${t.size}x${t.size}  (${buf.byteLength} bytes)`);
}

console.log("done.");
