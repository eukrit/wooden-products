// Merge per-category extracted JSONs + re-extract from saved raw HTML
// into the final products.json / products.csv. Runs with no browser.

const fs = require('fs');
const path = require('path');
const { JSDOM } = (() => {
  try { return require('jsdom'); } catch (_) { return {}; }
})();

const ROOT = path.resolve(__dirname, '..', '..');
const RAW_DIR = path.join(ROOT, 'data', 'raw', 'maxiswood');
const OUT_DIR = path.join(ROOT, 'data', 'parsed', 'maxiswood');

const CATEGORIES = [
  ['soffit-clad',       'SOFFIT/CLAD'],
  ['maxis-facade',      'MAXIS FACADE'],
  ['maxis-deck',        'MAXIS DECK'],
  ['maxis-coat',        'MAXIS COAT'],
  ['facad-xtreme',      'FACAD XTREME'],
  ['maxis-thatch',      'MAXIS THATCH'],
  ['maxis-floor',       'MAXIS FLOOR'],
  ['maxis-door',        'MAXIS DOOR'],
  ['maxis-fibre-rebar', 'MAXIS FIBRE REBAR'],
  ['recycoex-pave',     'RECYCOEX PAVE'],
];

function toCsv(rows) {
  const header = ['category', 'heading', 'href', 'image', 'image_alt', 'text'];
  const esc = (s) => {
    s = (s == null) ? '' : String(s);
    if (s.includes('"') || s.includes(',') || s.includes('\n')) {
      return '"' + s.replace(/"/g, '""') + '"';
    }
    return s;
  };
  const lines = [header.join(',')];
  for (const r of rows) {
    const img = (r.images && r.images[0]) || {};
    lines.push([
      r.category, r.heading, r.href || '',
      img.src || '', img.alt || '',
      (r.text || '').slice(0, 500),
    ].map(esc).join(','));
  }
  return lines.join('\n');
}

const all = [];
for (const [slug, name] of CATEGORIES) {
  const jsonPath = path.join(OUT_DIR, `${slug}.json`);
  if (fs.existsSync(jsonPath)) {
    const arr = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
    all.push(...arr);
    console.log(`  + ${slug}: ${arr.length} blocks (json)`);
  } else {
    console.log(`  ! ${slug}: no json — run scraper first`);
  }
}

fs.writeFileSync(
  path.join(OUT_DIR, 'products.json'),
  JSON.stringify(all, null, 2),
  'utf8'
);
fs.writeFileSync(
  path.join(OUT_DIR, 'products.csv'),
  toCsv(all),
  'utf8'
);
console.log(`\nWrote ${all.length} items to products.json / products.csv`);
