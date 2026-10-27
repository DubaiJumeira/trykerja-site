// The download pages' QR codes (decision 5275), drawn as assets/qr-download.svg is: EC level M, a
// 4-module quiet zone, one white square and one ink path of horizontal runs, with crisp edges.
//   assets/qr-download.svg     https://trykerja.com/download     (English, made on 20 Oct)
//   assets/qr-download-id.svg  https://trykerja.com/id/download  (Indonesian, made with this script)
//
// The encoder is toqr 0.1.1 (MIT, "Tiny QR code encoder", a dependency of Expo's CLI), imported in
// place from the app repo's node_modules and only read: nothing is installed for the site. If the app
// repo isn't at ~/dev/kerja, set TOQR to the path of toqr's dist/toqr.mjs.
//
//   node tools/qr.mjs https://trykerja.com/id/download assets/qr-download-id.svg
//
// Then run python3 -I tools/stamp.py, and decode the new picture in a browser before publishing.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [url, out] = process.argv.slice(2);
if (!url || !out) {
  console.error('usage: node tools/qr.mjs <url> <out.svg>');
  process.exit(2);
}
const TOQR = process.env.TOQR || path.join(os.homedir(), 'dev', 'kerja', 'node_modules', 'toqr', 'dist', 'toqr.mjs');
const { toQR } = await import(pathToFileURL(TOQR).href);

const EC_M = 0; // toqr's ECLevel: M = 0, L = 1, H = 2, Q = 3 (the format bits)
const modules = toQR(url, EC_M); // row by row, 1 = dark
const size = Math.round(Math.sqrt(modules.length));
if (size * size !== modules.length) throw new Error('toqr returned a matrix that is not square');
const margin = 4;
const full = size + 2 * margin;

// Each row's dark runs as "M x y" (a row's first run) or "m dx 0" (the gap since the last run), then
// "h length"; the stroke is 1 module wide, centred on the row (y + 0.5).
let d = '';
let move = 0;
let run = 0;
let newRow = false;
for (let i = 0; i < modules.length; i++) {
  const col = i % size;
  const row = Math.floor(i / size);
  if (!col && !newRow) newRow = true;
  if (modules[i]) {
    run++;
    if (!(col > 0 && modules[i - 1])) {
      d += newRow ? `M${col + margin} ${row + margin + 0.5}` : `m${move} 0`;
      move = 0;
      newRow = false;
    }
    if (!(col + 1 < size && modules[i + 1])) {
      d += `h${run}`;
      run = 0;
    }
  } else {
    move++;
  }
}

// White and the site's ink (--ink in assets/site.css), as in qr-download.svg.
const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${full} ${full}" shape-rendering="crispEdges">`
  + `<path fill="#FFFFFF" d="M0 0h${full}v${full}H0z"/><path stroke="#1D1A14" d="${d}"/></svg>\n`;
fs.writeFileSync(out, svg);
console.log(`${out}: ${url} (version ${(size - 17) / 4}, ${size} x ${size} modules, EC M, ${svg.length} bytes)`);
