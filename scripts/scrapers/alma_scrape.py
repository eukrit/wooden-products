"""Full scrape of Alma by Giorio (GIORIO S.r.l.) — https://www.almafloor.it/en-gb

The site is server-rendered HTML (Duda CMS). Each collection page contains all
its models inline as `<div id="modello-...">` blocks; each essence page lists the
colour/treatment range for one wood species plus product images whose filenames
encode the real SKU matrix (species · collection · model · colour · grade).

So plain `requests` + BeautifulSoup is sufficient — no headless browser needed.

Outputs (all under data/raw/alma/):
  pages/<slug>.html      — raw HTML of every collection / essence / info page
  pdfs/<file>.pdf        — every downloadable document from /download
  images/<file>          — product / swatch images (mid-res 640w variants)
  manifest.json          — index of everything fetched (urls, sizes, sha-less)

Run:
  python scripts/scrapers/alma_scrape.py
  python scripts/scrapers/alma_scrape.py --no-images   # skip image download
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "alma"
PAGES = RAW / "pages"
PDFS = RAW / "pdfs"
IMAGES = RAW / "images"
for d in (PAGES, PDFS, IMAGES):
    d.mkdir(parents=True, exist_ok=True)

BASE = "https://www.almafloor.it"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "en-GB,en;q=0.9"}

# (slug, path, pattern, category) — the 9 product collections
COLLECTIONS = [
    ("doghe",                "/en-gb/collezione-doghe",              "plank",        "engineered_flooring"),
    ("spina-ungherese-45",   "/en-gb/collezione-spina-ungherese-45", "chevron-45",   "engineered_flooring"),
    ("spina-italiana-90",    "/en-gb/collezione-spina-italiana-90",  "herringbone-90", "engineered_flooring"),
    ("spina-francese-30",    "/en-gb/collezione-spina-francese-30",  "chevron-30",   "engineered_flooring"),
    ("geometrici",           "/en-gb/collezione-geometrici",         "geometric",    "engineered_flooring"),
    ("design",               "/en-gb/collezione-design",             "design",       "engineered_flooring"),
    ("intarsi",              "/en-gb/collezione-intarsi",            "inlay",        "engineered_flooring"),
    ("esterno",              "/en-gb/collezione-esterno",            "decking",      "decking"),
    ("accessori",            "/en-gb/collezione-accessori",          "accessory",    "moulding"),
]

# (slug, path, species) — the wood essences (colour ranges).
# NB: the header nav's `essence-glacial-oak` link 404s; the live slug is `/glacial-oak`.
ESSENCES = [
    ("european-oak",       "/en-gb/essence-european-oak",    "European Oak"),
    ("glacial-oak",        "/en-gb/glacial-oak",             "Glacial Oak"),
    ("european-walnut",    "/en-gb/essence-european-walnut", "European Walnut"),
    ("american-walnut",    "/en-gb/essence-american-walnut", "American Walnut"),
    ("asian-teak",         "/en-gb/Asian-teak",              "Asian Teak"),
    ("austrian-larch-bio", "/en-gb/austrian-larch-bio",      "Austrian Larch Bio"),
]

# Context / info pages worth keeping
INFO_PAGES = [
    ("home",      "/en-gb"),
    ("azienda",   "/en-gb/azienda"),
    ("collezioni", "/en-gb/collezioni"),
    ("tutti-i-parquet", "/en-gb/tutti-i-parquet"),
    ("download",  "/en-gb/download"),
]

session = requests.Session()
session.headers.update(HEADERS)


def get(url: str, tries: int = 3) -> requests.Response | None:
    for i in range(tries):
        try:
            r = session.get(url, timeout=45)
            if r.status_code == 200:
                return r
            print(f"   HTTP {r.status_code} for {url}")
        except Exception as e:
            print(f"   error ({i+1}/{tries}) {url}: {e}")
        time.sleep(1.5 * (i + 1))
    return None


def fetch_pages() -> dict:
    """Download HTML for every collection / essence / info page."""
    saved = {}
    for slug, path, *_ in COLLECTIONS:
        saved[slug] = _save_html("collection", slug, path)
    for slug, path, _species in ESSENCES:
        saved[slug] = _save_html("essence", slug, path)
    for slug, path in INFO_PAGES:
        saved[slug] = _save_html("info", slug, path)
    return saved


def _save_html(kind: str, slug: str, path: str) -> dict | None:
    url = urljoin(BASE, path)
    print(f"-> [{kind}] {slug}: {url}", flush=True)
    r = get(url)
    if not r:
        return None
    out = PAGES / f"{slug}.html"
    out.write_text(r.text, encoding="utf-8")
    print(f"   saved {len(r.text):,} bytes -> {out.name}", flush=True)
    time.sleep(0.8)
    return {"kind": kind, "slug": slug, "url": url, "bytes": len(r.text), "file": out.name}


def extract_pdf_links() -> list[dict]:
    """Parse the /download page for every PDF link."""
    html = (PAGES / "download.html")
    if not html.exists():
        return []
    soup = BeautifulSoup(html.read_text(encoding="utf-8"), "html.parser")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".pdf" not in href.lower():
            continue
        full = urljoin(BASE, href)
        if full in seen:
            continue
        seen.add(full)
        label = a.get_text(" ", strip=True) or ""
        out.append({"url": full, "label": label})
    print(f"\nFound {len(out)} PDF links on /download")
    return out


def _safe_name(url: str) -> str:
    name = unquote(url.split("?")[0].split("/")[-1])
    name = re.sub(r"[^A-Za-z0-9._+\-]+", "_", name)
    return name[:160] or "file.pdf"


def download_pdfs(links: list[dict]) -> list[dict]:
    out = []
    for i, lk in enumerate(links, 1):
        url = lk["url"]
        name = _safe_name(url)
        dest = PDFS / name
        if dest.exists() and dest.stat().st_size > 0:
            print(f"   [{i}/{len(links)}] cached {name}")
            out.append({**lk, "file": name, "bytes": dest.stat().st_size})
            continue
        r = get(url)
        if not r:
            continue
        dest.write_bytes(r.content)
        print(f"   [{i}/{len(links)}] {name}  ({len(r.content):,} B)")
        out.append({**lk, "file": name, "bytes": len(r.content)})
        time.sleep(0.5)
    return out


CDN = "cdn-website.com"
# noise we never want as a "product image"
IMG_SKIP = ("logo", "favicon", "icon", "sprite", "bandiera", "flag", "placeholder",
            "where-to-find", "follow", "social")


def collect_image_urls() -> dict[str, str]:
    """Gather product/swatch image URLs from collection + essence pages.
    Returns {safe_filename: url} de-duplicated, normalised to a 640w variant."""
    urls: dict[str, str] = {}
    for slug, *_ in COLLECTIONS + [(s, p, sp) for s, p, sp in ESSENCES]:
        f = PAGES / f"{slug}.html"
        if not f.exists():
            continue
        soup = BeautifulSoup(f.read_text(encoding="utf-8"), "html.parser")
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if CDN not in src:
                continue
            low = src.lower()
            if any(k in low for k in IMG_SKIP):
                continue
            if not re.search(r"\.(jpg|jpeg|png)", low):
                continue
            norm = re.sub(r"-\d+w(\.(?:jpg|jpeg|png))", r"-640w\1", src, flags=re.I)
            name = _safe_name(norm)
            urls.setdefault(name, norm)
    print(f"\nCollected {len(urls)} unique product image URLs")
    return urls


def download_images(urls: dict[str, str]) -> list[dict]:
    out = []
    items = list(urls.items())
    for i, (name, url) in enumerate(items, 1):
        dest = IMAGES / name
        if dest.exists() and dest.stat().st_size > 0:
            out.append({"file": name, "url": url, "bytes": dest.stat().st_size})
            continue
        r = get(url, tries=2)
        if not r:
            continue
        dest.write_bytes(r.content)
        out.append({"file": name, "url": url, "bytes": len(r.content)})
        if i % 25 == 0 or i == len(items):
            print(f"   images {i}/{len(items)}")
        time.sleep(0.2)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-images", action="store_true", help="skip image download")
    ap.add_argument("--no-pdfs", action="store_true", help="skip PDF download")
    args = ap.parse_args()

    print("=== Alma by Giorio — full scrape ===\n")
    pages = fetch_pages()

    pdfs = []
    if not args.no_pdfs:
        pdfs = download_pdfs(extract_pdf_links())

    images = []
    if not args.no_images:
        images = download_images(collect_image_urls())

    manifest = {
        "source": BASE,
        "pages": [p for p in pages.values() if p],
        "pdfs": pdfs,
        "images": images,
        "counts": {
            "pages": len([p for p in pages.values() if p]),
            "pdfs": len(pdfs),
            "images": len(images),
        },
    }
    (RAW / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== DONE ===")
    print(f"  pages : {manifest['counts']['pages']}")
    print(f"  pdfs  : {manifest['counts']['pdfs']}")
    print(f"  images: {manifest['counts']['images']}")
    print(f"  manifest -> {RAW / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
