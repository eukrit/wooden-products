"""Parse the saved rendered HTML for each Maxis Wood category and extract
a structured catalog.

Each category produces a record with:
  - category name / slug / URL
  - description (narrative body text)
  - features (bulleted list or short lines between description and REMARKS)
  - products (list of SKU rows from the spec table, if any)
  - remarks (ordering / pricing terms)
  - colors_note (e.g. "Available in 9 colors")
  - warranty_note (e.g. "3 years warranty", "20-Year Warranty")
  - brochure_url
  - images (gallery — chrome/nav images filtered out)

Outputs:
  data/parsed/maxiswood/maxiswood_catalog.json   — per category, nested
  data/parsed/maxiswood/maxiswood_catalog.csv    — one row per SKU
  data/parsed/maxiswood/maxiswood_images.csv     — one row per image
  data/parsed/maxiswood/README.md                — human-readable summary
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "maxiswood"
OUT_DIR = ROOT / "data" / "parsed" / "maxiswood"
BASE = "https://www.maxiswood.com/"

# Category order as on the site menu. MAXIS MICROCEMENT is a placeholder
# page with no content as of scrape time; we record it anyway for
# completeness.
CATEGORIES = [
    ("soffit-clad",        "SOFFIT/CLAD",
     "https://www.maxiswood.com/SOFFIT/CLAD/667395a4094fe70013e56339/langEN"),
    ("maxis-facade",       "MAXIS FACADE",
     "https://www.maxiswood.com/MAXIS%20FACADE/667395aa094fe70013e56347/langEN"),
    ("maxis-deck",         "MAXIS DECK",
     "https://www.maxiswood.com/MAXIS%20DECK/667395af094fe70013e56355/langEN"),
    ("maxis-microcement",  "MAXIS MICROCEMENT",
     "https://www.maxiswood.com/MAXIS_Und_MICROCEMENT"),
    ("maxis-coat",         "MAXIS COAT",
     "https://www.maxiswood.com/MAXIS%20COAT/667395b4094fe70013e56363/langEN"),
    ("facad-xtreme",       "FACAD XTREME",
     "https://www.maxiswood.com/FACAD%20XTREME/667395b9094fe70013e56371/langEN"),
    ("maxis-thatch",       "MAXIS THATCH",
     "https://www.maxiswood.com/MAXIS%20THATCH/667395be094fe70013e5637f/langEN"),
    ("maxis-floor",        "MAXIS FLOOR",
     "https://www.maxiswood.com/MAXIS%20FLOOR/667395c3094fe70013e5638e/langEN"),
    ("maxis-door",         "MAXIS DOOR",
     "https://www.maxiswood.com/MAXIS%20DOOR/667395c7094fe70013e5639c/langEN"),
    ("maxis-fibre-rebar",  "MAXIS FIBRE REBAR",
     "https://www.maxiswood.com/MAXIS%20FIBRE%20REBAR/667395cd094fe70013e563ad/langEN"),
    ("recycoex-pave",      "RECYCOEX PAVE",
     "https://www.maxiswood.com/RECYCOEX%20PAVE/667395d2094fe70013e563bc/langEN"),
]

CHROME_IMG_HINTS = (
    "flag/", "/Images/flag", "/ic-", "whatsapp", "widgets_",
    "autodigi.net", "cart.png", "menu/bg-", "sprite.png", "/Shopcart/",
    "Linez-", "arrow", "icon", "maxis@2x", "pdf02",
)


def is_chrome_img(src: str) -> bool:
    s = src.lower()
    return any(h.lower() in s for h in CHROME_IMG_HINTS)


def clean(s: str | None) -> str:
    if not s:
        return ""
    s = s.replace("\xa0", " ").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", s).strip()


def absu(u: str | None) -> str:
    if not u:
        return ""
    return urljoin(BASE, u)


def visible_body_text(soup: BeautifulSoup) -> str:
    """Page text with scripts/styles/nav stripped."""
    for bad in soup(["script", "style", "noscript"]):
        bad.decompose()
    text = soup.get_text(" ", strip=True)
    return clean(text)


def cut_after_nav(text: str) -> str:
    """The nav is duplicated (desktop + mobile); content starts after the
    *second* 'CONTACT US'. Strip everything up to there."""
    first = text.find("CONTACT US")
    if first == -1:
        return text
    second = text.find("CONTACT US", first + 1)
    if second == -1:
        return text[first + len("CONTACT US"):].strip()
    return text[second + len("CONTACT US"):].strip()


CONTENT_END_MARKERS = (
    "BANGKOK", "© 2024", "© 2025", "© 2026", "Powered by Autodigi",
    "We use cookies", "Privacy Policy",
)


def cut_before_footer(text: str) -> str:
    ends = []
    for m in CONTENT_END_MARKERS:
        i = text.find(m)
        if i != -1:
            ends.append(i)
    if not ends:
        return text
    return text[: min(ends)].strip()


def extract_description(text: str, category: str) -> str:
    """Narrative between category heading and the REMARKS / Specifications /
    Sample-of-shades section."""
    # Remove the leading category heading if present
    up = text.upper()
    cat_up = category.upper()
    idx = up.find(cat_up)
    if idx != -1:
        text = text[idx + len(category):].lstrip(" -—:")
    # Cut at stop markers
    stops = [
        r"\bSpecifications\b",
        r"\bSPECIFICATIONS\b",
        r"\bPRODUCT CODE\b",
        r"\bSample of wood shades\b",
        r"\bSample of thatch shades\b",
        r"\bAvailable in \d+ colors\b",
        r"\bClick the button below\b",
        r"\bDownload Borchure\b",
        r"\bDownload Brochure\b",
        r"\bREMARKS\b",
        r"\b Advantages \b",
        r"\b Handling and Placement \b",
    ]
    ends = []
    for pat in stops:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            ends.append(m.start())
    if ends:
        text = text[: min(ends)]
    return clean(text)[:4000]


def extract_section(text: str, start_pat: str, end_pats: list[str]) -> str:
    m = re.search(start_pat, text, re.IGNORECASE)
    if not m:
        return ""
    tail = text[m.end():]
    ends = []
    for p in end_pats:
        mm = re.search(p, tail, re.IGNORECASE)
        if mm:
            ends.append(mm.start())
    if ends:
        tail = tail[: min(ends)]
    return clean(tail)


def extract_colors_note(text: str) -> str:
    m = re.search(r"Available in (\d+ colors?)", text, re.IGNORECASE)
    return m.group(0) if m else ""


def extract_warranty(text: str) -> str:
    m = re.search(r"(\d{1,2})[- ]?Year[s]?\s+warranty", text, re.IGNORECASE)
    if m:
        return clean(m.group(0))
    return ""


def extract_brochure_link(soup: BeautifulSoup) -> str:
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().endswith(".pdf"):
            return absu(href)
    # sometimes brochure is behind a button + JS; return "" in that case
    return ""


HEADER_KEYS = ("PRODUCT CODE", "PRODUCT", "CODE", "MODEL", "DIMENSION",
               "SIZE", "PROFILE", "COLOR", "PRICE")


def _looks_like_header(cells: list[str]) -> bool:
    up = " ".join(c.upper() for c in cells)
    return sum(k in up for k in HEADER_KEYS) >= 2


def _normalize_header(cells: list[str]) -> list[str]:
    out = []
    for c in cells:
        u = clean(c).upper()
        if u.startswith("PRODUCT") or u in {"CODE", "MODEL"}:
            out.append("product_code")
        elif "DIMENSION" in u or u.startswith("SIZE"):
            out.append("dimension")
        elif u == "PROFILE":
            out.append("profile")
        elif u.startswith("PRICE"):
            out.append("price")
        elif u == "COLOR":
            out.append("color")
        else:
            out.append(u.lower().replace(" ", "_") or f"col{len(out)+1}")
    return out


def extract_spec_tables(soup: BeautifulSoup) -> list[dict]:
    products: list[dict] = []
    for tbl in soup.find_all("table"):
        rows = [r for r in tbl.find_all("tr")]
        if not rows:
            continue
        # Find header row (first row with 2+ recognizable keys)
        header_idx = None
        header_cells: list[str] = []
        for i, tr in enumerate(rows[:3]):
            cells = [clean(c.get_text(" ")) for c in tr.find_all(["th", "td"])]
            if _looks_like_header(cells):
                header_idx, header_cells = i, cells
                break
        if header_idx is None:
            continue
        keys = _normalize_header(header_cells)
        for tr in rows[header_idx + 1:]:
            cells = [clean(c.get_text(" ")) for c in tr.find_all(["th", "td"])]
            if not any(cells) or len(cells) < 2:
                continue
            # Skip header-ish rows that reappear
            if _looks_like_header(cells):
                continue
            rec = {}
            for i, val in enumerate(cells):
                key = keys[i] if i < len(keys) else f"col{i+1}"
                rec[key] = val
            # Require a product code OR a dimension
            if (rec.get("product_code") or "").strip() or (rec.get("dimension") or "").strip():
                products.append(rec)
    return products


def extract_gallery(soup: BeautifulSoup) -> list[dict]:
    """Meaningful product / shade-sample images."""
    imgs: list[dict] = []
    seen_keys: set[str] = set()
    for img in soup.find_all("img"):
        src = (img.get("src") or "").strip()
        if not src:
            continue
        if is_chrome_img(src):
            continue
        # Deduplicate the same filename served at multiple sizes.
        base_key = re.sub(r"/\d+/\d+/", "/_/_/", src)
        if base_key in seen_keys:
            continue
        seen_keys.add(base_key)
        alt = clean(img.get("alt") or "")
        imgs.append({"src": absu(src), "alt": alt})
    return imgs


def parse_category(slug: str, category: str, url: str) -> dict:
    path = RAW_DIR / f"{slug}.html"
    if not path.exists():
        return {"slug": slug, "category": category, "url": url,
                "error": "missing rendered HTML"}
    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    text_all = visible_body_text(soup)
    body = cut_before_footer(cut_after_nav(text_all))

    description = extract_description(body, category)
    remarks = extract_section(
        body, r"\bREMARKS\b",
        [r"\bSample of (wood|thatch) shades\b",
         r"\bAvailable in \d+ colors\b",
         r"\bClick the button below\b",
         r"\bDownload Borchure\b",
         r"\bDownload Brochure\b"],
    )
    advantages = extract_section(
        body, r"\bAdvantages\b",
        [r"\bREMARKS\b", r"\bSample of (wood|thatch) shades\b",
         r"\bAvailable in \d+ colors\b",
         r"\bClick the button below\b"],
    )
    properties = extract_section(
        body, r"\bProperties of (maxis|Maxis|MAXIS)[^.]{0,40}\b",
        [r"\bPrevious Next\b", r"\bAdvantages\b", r"\bREMARKS\b"],
    )
    handling = extract_section(
        body, r"\bHandling and Placement\b",
        [r"\bBANGKOK\b"],
    )
    products = extract_spec_tables(soup)
    brochure = extract_brochure_link(soup)
    colors_note = extract_colors_note(body)
    warranty = extract_warranty(body)
    images = extract_gallery(soup)

    # Notes for categories that don't render product content
    notes = []
    if len(body) < 120:
        notes.append("Page rendered with no visible content — category appears "
                     "to be a placeholder only.")
    if slug == "soffit-clad" and "SUSTAINABLE WOOD EXPERT" in body.upper():
        notes.append("The SOFFIT/CLAD URL currently routes to the site "
                     "home page content; no dedicated category page was rendered.")

    return {
        "slug": slug,
        "category": category,
        "url": url,
        "description": description,
        "advantages": advantages,
        "properties": properties,
        "handling_and_placement": handling,
        "remarks": remarks,
        "colors_note": colors_note,
        "warranty_note": warranty,
        "brochure_url": brochure,
        "products": products,
        "images": images,
        "notes": notes,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    catalog = [parse_category(s, c, u) for s, c, u in CATEGORIES]

    (OUT_DIR / "maxiswood_catalog.json").write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Flat SKU-level CSV
    sku_fields = [
        "category", "category_slug", "product_code", "dimension",
        "profile", "color", "price", "brochure_url",
        "colors_note", "warranty_note", "description", "remarks",
        "first_image", "image_count", "url",
    ]
    with (OUT_DIR / "maxiswood_catalog.csv").open("w", newline="",
                                                  encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=sku_fields, extrasaction="ignore")
        w.writeheader()
        for cat in catalog:
            base = {
                "category": cat.get("category", ""),
                "category_slug": cat.get("slug", ""),
                "url": cat.get("url", ""),
                "brochure_url": cat.get("brochure_url", ""),
                "colors_note": cat.get("colors_note", ""),
                "warranty_note": cat.get("warranty_note", ""),
                "description": cat.get("description", ""),
                "remarks": cat.get("remarks", ""),
                "first_image": (cat.get("images") or [{}])[0].get("src", ""),
                "image_count": len(cat.get("images", [])),
            }
            products = cat.get("products") or [{}]
            for p in products:
                row = dict(base)
                row.update({
                    "product_code": p.get("product_code", ""),
                    "dimension": p.get("dimension", ""),
                    "profile": p.get("profile", ""),
                    "color": p.get("color", ""),
                    "price": p.get("price", ""),
                })
                w.writerow(row)

    # Image-level CSV
    with (OUT_DIR / "maxiswood_images.csv").open("w", newline="",
                                                 encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["category", "category_slug", "image_url", "alt"])
        for cat in catalog:
            for img in cat.get("images", []):
                w.writerow([cat["category"], cat["slug"],
                            img["src"], img["alt"]])

    # Summary
    total_skus = sum(len(c.get("products", [])) for c in catalog)
    total_imgs = sum(len(c.get("images", [])) for c in catalog)
    lines = [
        "# Maxis Wood Catalog Summary",
        f"Scraped: {len(catalog)} categories, {total_skus} SKU rows, "
        f"{total_imgs} product images",
        "",
    ]
    for c in catalog:
        lines.append(f"## {c['category']}")
        lines.append(f"- URL: {c['url']}")
        lines.append(f"- Description: "
                     f"{(c.get('description') or '')[:180]}{'…' if len(c.get('description') or '') > 180 else ''}")
        lines.append(f"- SKU rows: {len(c.get('products', []))}")
        for p in c.get("products", []):
            lines.append(
                f"  - {p.get('product_code','')}  "
                f"{p.get('dimension','')}  "
                f"{p.get('profile','')}  "
                f"{p.get('color','')}  "
                f"{p.get('price','')}"
            )
        if c.get("colors_note"):
            lines.append(f"- Colors: {c['colors_note']}")
        if c.get("warranty_note"):
            lines.append(f"- Warranty: {c['warranty_note']}")
        if c.get("brochure_url"):
            lines.append(f"- Brochure: {c['brochure_url']}")
        lines.append(f"- Images: {len(c.get('images', []))}")
        for n in c.get("notes", []):
            lines.append(f"- NOTE: {n}")
        lines.append("")
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"Categories: {len(catalog)}")
    print(f"Total SKU rows: {total_sku}".replace("total_sku", str(total_skus))) if False else None
    print(f"Total SKU rows: {total_skus}")
    print(f"Total product images: {total_imgs}")
    print(f"  -> {OUT_DIR / 'maxiswood_catalog.json'}")
    print(f"  -> {OUT_DIR / 'maxiswood_catalog.csv'}")
    print(f"  -> {OUT_DIR / 'maxiswood_images.csv'}")
    print(f"  -> {OUT_DIR / 'README.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
