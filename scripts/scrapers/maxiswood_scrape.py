"""Scrape all products from https://www.maxiswood.com/.

The site is an iTopPlus AngularJS SPA — content is rendered client-side,
so we use Playwright (Chromium) to wait for the page to render, then
extract the product cards from each of the 10 category pages.

Output:
  data/raw/maxiswood/<slug>.html     — rendered HTML per page
  data/raw/maxiswood/<slug>.png      — full-page screenshot (debug)
  data/parsed/maxiswood/products.json — consolidated product records
  data/parsed/maxiswood/products.csv  — flat CSV
"""
from __future__ import annotations

import csv
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote, urljoin

from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "maxiswood"
OUT_DIR = ROOT / "data" / "parsed" / "maxiswood"
RAW_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Category landing pages (English). The URL path contains spaces and slashes
# because iTopPlus treats the category name as the slug.
CATEGORIES = [
    ("soffit-clad",       "SOFFIT/CLAD",       "667395a4094fe70013e56339"),
    ("maxis-facade",      "MAXIS FACADE",      "667395aa094fe70013e56347"),
    ("maxis-deck",        "MAXIS DECK",        "667395af094fe70013e56355"),
    ("maxis-coat",        "MAXIS COAT",        "667395b4094fe70013e56363"),
    ("facad-xtreme",      "FACAD XTREME",      "667395b9094fe70013e56371"),
    ("maxis-thatch",      "MAXIS THATCH",      "667395be094fe70013e5637f"),
    ("maxis-floor",       "MAXIS FLOOR",       "667395c3094fe70013e5638e"),
    ("maxis-door",        "MAXIS DOOR",        "667395c7094fe70013e5639c"),
    ("maxis-fibre-rebar", "MAXIS FIBRE REBAR", "667395cd094fe70013e563ad"),
    ("recycoex-pave",     "RECYCOEX PAVE",     "667395d2094fe70013e563bc"),
]
BASE = "https://www.maxiswood.com/"


def build_url(name: str, pid: str) -> str:
    return f"{BASE}{quote(name)}/{pid}/langEN"


def render_page(page, url: str, settle_ms: int = 2500) -> str:
    """Navigate and wait for the Angular app to render product content."""
    page.goto(url, wait_until="networkidle", timeout=60_000)
    # Accept cookie if present (best-effort).
    try:
        page.click("text=Accept", timeout=1500)
    except PwTimeout:
        pass
    # Product cards usually appear inside `.contentManager_item` or similar.
    # Wait for any significant content beyond the skeleton.
    for sel in [
        "[class*='contentManager']",
        ".ITPProduct",
        ".productList",
        ".contentmanager",
        "article",
    ]:
        try:
            page.wait_for_selector(sel, timeout=3500)
            break
        except PwTimeout:
            continue
    page.wait_for_timeout(settle_ms)
    # Scroll to bottom to trigger any lazy content
    page.evaluate(
        "async () => { "
        "  const h = document.body.scrollHeight; "
        "  for (let y = 0; y < h; y += 500) { window.scrollTo(0, y); "
        "    await new Promise(r => setTimeout(r, 80)); } "
        "  window.scrollTo(0, 0); }"
    )
    page.wait_for_timeout(800)
    return page.content()


def extract_products(page, category_url: str) -> list[dict]:
    """Pull product-like blocks out of the DOM using a few heuristics."""
    js = r"""
    () => {
      const abs = (u) => u ? new URL(u, document.baseURI).href : null;

      // Pass 1: iTopPlus 'contentmanager' modules (carousels / galleries)
      const items = [];
      const roots = document.querySelectorAll(
        "[class*='contentmanager'], [class*='contentManager'], " +
        "[class*='ITPProduct'], [class*='productlist'], " +
        "[class*='gallery'], [ng-repeat], .item"
      );
      const seen = new Set();

      function pushItem(el) {
        // Collect links + images under the element
        const links = Array.from(el.querySelectorAll("a[href]"));
        const imgs = Array.from(el.querySelectorAll("img")).map(i => ({
          src: abs(i.getAttribute('src') || i.currentSrc),
          alt: i.getAttribute('alt') || '',
        })).filter(i => i.src);

        const text = (el.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 1200);

        // Pick the most distinctive headline: an h1/h2/h3/h4 or a
        // strong/title-like class
        const head = el.querySelector('h1, h2, h3, h4, h5, .title, [class*="title"], [class*="name"]');
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
          classes: el.className,
        });
      }

      roots.forEach(el => {
        // If an element contains other candidate containers, walk its direct
        // child "cards" rather than the outer wrapper (avoids duplication).
        const children = el.querySelectorAll(':scope > *');
        if (children.length > 1 && children.length < 50) {
          children.forEach(c => {
            if (c.querySelector('img') || c.innerText.trim().length > 15) {
              pushItem(c);
            }
          });
        } else {
          pushItem(el);
        }
      });

      return items;
    }
    """
    return page.evaluate(js)


def dedupe(items: list[dict]) -> list[dict]:
    out, seen = [], set()
    for it in items:
        if not (it.get("heading") or it.get("images")):
            continue
        key = (it.get("heading") or "").lower().strip()
        img0 = (it.get("images") or [{}])[0].get("src", "")
        k = f"{key}|{img0}"
        if not key and not img0:
            continue
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out


def slugify(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s or "item"


def main() -> int:
    all_products: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0 Safari/537.36"),
            viewport={"width": 1440, "height": 2200},
        )
        page = ctx.new_page()

        for slug, name, pid in CATEGORIES:
            url = build_url(name, pid)
            print(f"-> {slug}: {url}", flush=True)
            try:
                html = render_page(page, url)
            except Exception as e:
                print(f"   render failed: {e}", flush=True)
                continue
            (RAW_DIR / f"{slug}.html").write_text(html, encoding="utf-8")
            try:
                page.screenshot(path=str(RAW_DIR / f"{slug}.png"),
                                full_page=True)
            except Exception:
                pass

            items = extract_products(page, url)
            items = dedupe(items)
            for it in items:
                it["category"] = name
                it["category_slug"] = slug
                it["category_url"] = url
            print(f"   extracted {len(items)} blocks", flush=True)
            all_products.extend(items)

        browser.close()

    (OUT_DIR / "products.json").write_text(
        json.dumps(all_products, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Flat CSV
    with (OUT_DIR / "products.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["category", "heading", "href", "image",
                    "image_alt", "text"])
        for it in all_products:
            img = (it.get("images") or [{}])[0]
            w.writerow([
                it.get("category", ""),
                it.get("heading", ""),
                it.get("href", ""),
                img.get("src", ""),
                img.get("alt", ""),
                (it.get("text") or "")[:500],
            ])

    print(f"\nTotal: {len(all_products)} items across "
          f"{len(CATEGORIES)} categories")
    print(f"  JSON: {OUT_DIR / 'products.json'}")
    print(f"  CSV : {OUT_DIR / 'products.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
