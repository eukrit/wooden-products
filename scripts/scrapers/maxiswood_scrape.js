// Scrape all products from https://www.maxiswood.com/
// Node.js + playwright-core (reuses the Chromium already installed for
// Python Playwright). Python 3.14 + playwright sync_api is currently
// broken on Windows ("new_time >= loop->time" assertion in libuv), so
// we drive Chromium from Node instead.

const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const RAW_DIR = path.join(ROOT, 'data', 'raw', 'maxiswood');
const OUT_DIR = path.join(ROOT, 'data', 'parsed', 'maxiswood');
fs.mkdirSync(RAW_DIR, { recursive: true });
fs.mkdirSync(OUT_DIR, { recursive: true });

// Use the system Google Chrome — Playwright's bundled Chromium is
// missing a VC++ runtime on this box ("side-by-side configuration").
const CHROME_EXE = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

const BASE = 'https://www.maxiswood.com/';
const CATEGORIES = [
  ['soffit-clad',        'SOFFIT/CLAD',        '667395a4094fe70013e56339'],
  ['maxis-facade',       'MAXIS FACADE',       '667395aa094fe70013e56347'],
  ['maxis-deck',         'MAXIS DECK',         '667395af094fe70013e56355'],
  ['maxis-microcement',  'MAXIS MICROCEMENT',  null],
  ['maxis-coat',         'MAXIS COAT',         '667395b4094fe70013e56363'],
  ['facad-xtreme',       'FACAD XTREME',       '667395b9094fe70013e56371'],
  ['maxis-thatch',       'MAXIS THATCH',       '667395be094fe70013e5637f'],
  ['maxis-floor',        'MAXIS FLOOR',        '667395c3094fe70013e5638e'],
  ['maxis-door',         'MAXIS DOOR',         '667395c7094fe70013e5639c'],
  ['maxis-fibre-rebar',  'MAXIS FIBRE REBAR',  '667395cd094fe70013e563ad'],
  ['recycoex-pave',      'RECYCOEX PAVE',      '667395d2094fe70013e563bc'],
];

function buildUrl(name, pid) {
  if (!pid) {
    // MAXIS MICROCEMENT uses a different URL scheme (no ID slug).
    return `${BASE}MAXIS_Und_MICROCEMENT`;
  }
  // Encode each path segment but keep '/' inside SOFFIT/CLAD literal.
  const enc = name.split('/').map(s => encodeURIComponent(s)).join('/');
  return `${BASE}${enc}/${pid}/langEN`;
}

async function renderAndExtract(page, url, settleMs = 2500) {
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  // Accept cookie (best-effort).
  try {
    await page.click('text=Accept', { timeout: 1500 });
  } catch (_) {}
  // Wait for something product-y to appear.
  for (const sel of [
    '[class*="contentmanager"]',
    '[class*="contentManager"]',
    '.ITPProduct',
    '.productList',
    'article',
  ]) {
    try {
      await page.waitForSelector(sel, { timeout: 3500 });
      break;
    } catch (_) {}
  }
  await page.waitForTimeout(settleMs);
  // Scroll to trigger any lazy-loaded images.
  await page.evaluate(async () => {
    const h = document.body.scrollHeight;
    for (let y = 0; y < h; y += 500) {
      window.scrollTo(0, y);
      await new Promise(r => setTimeout(r, 80));
    }
    window.scrollTo(0, 0);
  });
  await page.waitForTimeout(800);

  const html = await page.content();
  const items = await page.evaluate(() => {
    const abs = (u) => u ? new URL(u, document.baseURI).href : null;
    const items = [];
    const seen = new Set();

    function pushItem(el) {
      const links = Array.from(el.querySelectorAll('a[href]'));
      const imgs = Array.from(el.querySelectorAll('img')).map(i => ({
        src: abs(i.getAttribute('src') || i.currentSrc || ''),
        alt: i.getAttribute('alt') || '',
      })).filter(i => i.src && !i.src.endsWith('#'));

      const text = (el.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 1500);
      const head = el.querySelector(
        'h1, h2, h3, h4, h5, .title, [class*="title"], [class*="name"], strong'
      );
      const heading = head ? head.innerText.trim().replace(/\s+/g, ' ') : '';
      const href = links.length ? abs(links[0].getAttribute('href')) : null;

      if (!heading && !imgs.length) return;
      const key = (heading || '') + '|' + (imgs[0]?.src || '') + '|' + (href || '');
      if (seen.has(key)) return;
      seen.add(key);
      items.push({
        heading,
        text,
        href,
        images: imgs.slice(0, 6),
        tag: el.tagName,
        classes: el.className || '',
      });
    }

    const roots = document.querySelectorAll(
      '[class*="contentmanager"], [class*="contentManager"], ' +
      '[class*="ITPProduct"], [class*="productlist"], ' +
      '[class*="gallery"], [ng-repeat], .item, article'
    );
    roots.forEach(el => {
      const children = el.querySelectorAll(':scope > *');
      if (children.length > 1 && children.length < 80) {
        children.forEach(c => {
          if (c.querySelector('img') || (c.innerText || '').trim().length > 15) {
            pushItem(c);
          }
        });
      } else {
        pushItem(el);
      }
    });

    return items;
  });
  return { html, items };
}

function dedupe(items) {
  const out = [];
  const seen = new Set();
  for (const it of items) {
    if (!(it.heading || (it.images && it.images.length))) continue;
    const key = (it.heading || '').toLowerCase().trim();
    const img = (it.images && it.images[0]) ? it.images[0].src : '';
    const k = `${key}|${img}`;
    if (!key && !img) continue;
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(it);
  }
  return out;
}

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

// CLI: optionally pass a comma-separated list of slugs to scrape only those.
const ONLY = (process.argv[2] || '').split(',').filter(Boolean);

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: CHROME_EXE,
  });
  const ctx = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
               '(KHTML, like Gecko) Chrome/131.0 Safari/537.36',
    viewport: { width: 1440, height: 2200 },
  });
  const page = await ctx.newPage();

  const all = [];
  const targets = ONLY.length
    ? CATEGORIES.filter(c => ONLY.includes(c[0]))
    : CATEGORIES;
  for (const [slug, name, pid] of targets) {
    const url = buildUrl(name, pid);
    console.log(`-> ${slug}: ${url}`);
    try {
      const { html, items } = await renderAndExtract(page, url);
      fs.writeFileSync(path.join(RAW_DIR, `${slug}.html`), html, 'utf8');
      try {
        await page.screenshot({
          path: path.join(RAW_DIR, `${slug}.png`),
          fullPage: true,
        });
      } catch (_) {}

      const clean = dedupe(items).map(it => ({
        ...it,
        category: name,
        category_slug: slug,
        category_url: url,
      }));
      console.log(`   extracted ${clean.length} blocks`);
      all.push(...clean);

      // Persist this category's extracted blocks immediately so we don't
      // lose work if the process dies mid-run (seen on Windows).
      fs.writeFileSync(
        path.join(OUT_DIR, `${slug}.json`),
        JSON.stringify(clean, null, 2),
        'utf8'
      );
    } catch (e) {
      console.log(`   render failed: ${e.message}`);
    }
  }

  await browser.close();

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
  console.log(`\nTotal: ${all.length} items across ${CATEGORIES.length} categories`);
  console.log(`  JSON: ${path.join(OUT_DIR, 'products.json')}`);
  console.log(`  CSV : ${path.join(OUT_DIR, 'products.csv')}`);
})().catch(err => {
  console.error(err);
  process.exit(1);
});
