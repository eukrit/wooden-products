"""
gen_solid_wood_dashboard.py — Generate a self-contained HTML dashboard +
cross-vendor price comparison for GENUINE SOLID WOOD FLOORING ONLY, sourced
live from the `products-wood` Firestore database.

Reads `vendors`, `products`, `categories`, `quotations`, `product_images`
via the shared `setup_db.get_client()` helper (bound to products-wood) and
writes a single static, dependency-free dark-theme HTML page to:

    docs/dashboards/solid-wood-flooring.html

Per Rule 13 all generated HTML lives under docs/ in a typed subfolder.
The page is served privately via the go-access-gateway at
https://gateway.goco.bz/wooden-products/docs/dashboards/solid-wood-flooring.html

------------------------------------------------------------------------------
SCOPE — genuine solid wood flooring ONLY (decided by the owner)
------------------------------------------------------------------------------
INCLUDE:
  (a) one-piece SOLID TIMBER flooring, and
  (b) REAL-WOOD ENGINEERED / parquet — multi-layer with a genuine solid-wood
      wear layer (e.g. Bimei / Foglie d'Oro engineered parquet, Visconti /
      Giorio Casa, Elegant Living oak planks, Chinese teak veneer floors,
      Leo Nature / Qihome engineered hardwood).

EXCLUDE entirely (even if mis-filed under a flooring category):
  WPC / "artificial wood" / composite, SPC / stone-plastic, LVT / vinyl, and
  laminate / HDF / MDF fiberboard "decor" floors.

The inclusion rule does NOT trust the category name alone. A product is in
scope only if BOTH:
  * its category is a flooring category (timber_flooring | engineered_flooring),
    OR it is filed elsewhere but clearly a genuine-wood floor, AND
  * none of its material / subcategory / name fields match a COMPOSITE marker
    (wpc, spc, lvt, vinyl, laminate, hdf, mdf, fiberboard, "wood plastic",
    "wood polymer", "stone plastic", "stone polymer", "polymer/plastic
    composite").
Ambiguous records (e.g. bamboo — botanically a grass, not timber) are NOT
silently dropped: they are excluded from the comparison and listed in the
"excluded / needs-review" footnote so the owner can adjudicate.

solid vs engineered: category timber_flooring (one-piece solid) is classified
"solid"; engineered_flooring (real-wood wear layer over a ply core) is
classified "engineered". Both are in scope and kept visually distinct.

------------------------------------------------------------------------------
PRICING
------------------------------------------------------------------------------
Per product, a raw unit price is sourced in priority order:
  1. structured `quotations.items[]` matched by product_id (richest source),
  2. else parsed from free-text `product.notes` (e.g. "328 yuan/m2",
     "$36/sqm", "295 CNY").
Raw price + currency + unit are always kept and shown. A normalised
≈THB/m² is computed with a STATIC, approximate FX table (see FX below) and,
where the source unit is per-piece / per-linear-metre, by converting with the
product's dimensions. When conversion is not possible, ≈THB/m² shows "n/a".
Prices are NEVER invented — only what is sourced is shown, with the source
named (quotation:QC… / notes / slack-pricelist-2026-03-15).

Usage:
    PYTHONIOENCODING=utf-8 python scripts/firestore/gen_solid_wood_dashboard.py

Deterministic / re-runnable — overwrites the output file each run.
"""

import html
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

# Allow `from setup_db import get_client` regardless of CWD.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from setup_db import get_client  # noqa: E402

# ---------------------------------------------------------------------------
# Static, APPROXIMATE FX table — THB per 1 unit of the source currency.
# Hand-set, NOT a live feed. Update the date when you refresh these.
# ---------------------------------------------------------------------------
FX_DATE = "2026-06-10"
FX_THB = {
    "THB": 1.0,
    "USD": 36.5,
    "CNY": 5.0,   # also matches RMB / yuan
    "RMB": 5.0,
    "EUR": 40.0,
}

PRICELIST_SOURCE = "slack-pricelist-2026-03-15"
PRICELIST_LABEL = "2026.03.15 price list (Slack)"

# ---------------------------------------------------------------------------
# External vendor parsed from the Slack price list
#   file F0APVRP36UC — "2026年主推产品价格表 2026.3.15.pdf"
#   (2026 Main Products Price List, dated 2026-03-15), fetched via the Slack
#   Web API. The PDF is NOT committed (binary); these are the derived facts.
#
# Every series below is genuine REAL-WOOD ENGINEERED flooring: a natural
# knot-free oak/walnut veneer wear layer (0.6–3.0 mm) over an imported
# full-birch marine-ply core ("全桦多层 / 进口全桦基材"). Prices are the
# dealer price (经销商价) in CNY, per m² (the China-market convention for
# these 经销商价 floor listings). Pages 10–11 of the PDF (金刚面 "diamond-
# face" and 强化 "reinforced", both "surface = HD decorative paper") are
# LAMINATE and are intentionally excluded — see EXCLUDED_NOTES.
# ---------------------------------------------------------------------------
PRICELIST_VENDOR = {
    "vendor_id": PRICELIST_SOURCE,
    "name": "Russian/American Oak engineered-flooring supplier",
    "brand": None,
    "country": "CN",
    "note": "External quote-only source — from " + PRICELIST_LABEL
            + " (lekastudio Slack, file F0APVRP36UC). Not yet a Firestore vendor.",
}

# Each row: (series name, species, grade, dims LxWxT mm, veneer mm, finish/format, CNY/m²)
PRICELIST_ROWS = [
    ("A-grade Russian Oak large plank",     "Russian Oak",        "A / knot-free", "1910x185x15", "3.0", "brushed, locking, UV (Italian semi-translucent)", 255),
    ("A-grade American Oak large plank",    "American Oak",       "A / AB",        "1900x191x15", "3.0", "brushed, flat, UV (PPG)",                          240),
    ("B-grade Oak large herringbone",       "Oak",                "B / AB",        "910x127x14",  "0.6", "brushed, flat, herringbone, UV",                   165),
    ("B-grade European White Oak plank",    "European White Oak", "B / knot-free", "1215x193x14", "1.2", "brushed, locking, UV (stained)",                   108),
    ("B-grade Oak 1200 plank",              "Oak",                "B / AB",        "1220x193x14.5","1.2", "brushed, locking, UV (stained)",                  180),
    ("B-grade Oak 600 herringbone",         "Oak",                "B / knot-free", "600x124x14.5","1.2", "brushed, locking, herringbone, UV",                168),
    ("B-grade Oak 500 chevron",             "Oak",                "B",             "500x127x14.5","1.2", "brushed, locking, chevron, UV",                    198),
    ("B-grade Oak 1900 large plank",        "Oak",                "B",             "1910x193x14.5","1.2", "brushed, locking, UV",                            180),
    ("B-grade Black Walnut 600 herringbone","Black Walnut",       "B / AB",        "600x124x14.5","1.2", "brushed, locking, herringbone, UV (stained)",      185),
    ("B-grade Black Walnut 500 chevron",    "Black Walnut",       "B / AB",        "500x127x14.5","1.2", "brushed, flat, chevron, UV (stained)",             208),
    ("B-grade Black Walnut 1200 plank",     "Black Walnut",       "B / AB",        "1220x193x14.5","1.2", "brushed, locking, UV (stained)",                  208),
    ("B-grade Black Walnut 1900 large plank","Black Walnut",      "B / AB",        "1910x193x14.5","1.2", "brushed, locking, UV (stained)",                  228),
]

WECHAT_SOURCE = "wechat-automation:wechat-documents"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "docs", "dashboards", "solid-wood-flooring.html")

# Flooring categories that are candidates for the genuine-wood scope.
FLOORING_CATEGORIES = {"timber_flooring", "engineered_flooring"}

# Composite markers — if any appears in material / subcategory / name, the
# record is NOT genuine wood and is excluded from the comparison.
COMPOSITE_MARKERS = [
    "wpc", "spc", "lvt", "vinyl", "laminate", "hdf", "mdf", "fiberboard",
    "fibreboard", "wood plastic", "wood polymer", "wood-plastic", "wood-polymer",
    "stone plastic", "stone polymer", "stone-plastic", "stone-polymer",
    "plastic composite", "polymer composite", "pvc",
]
# Ambiguous markers — excluded from the comparison but surfaced for review
# (bamboo is botanically a grass, not timber).
NEEDS_REVIEW_MARKERS = ["bamboo"]


def esc(value):
    """HTML-escape a value, treating None/empty as an em-dash placeholder."""
    if value is None:
        return "&mdash;"
    text = str(value).strip()
    return html.escape(text) if text else "&mdash;"


def fetch_all(db):
    vendors = [d.to_dict() | {"_id": d.id} for d in db.collection("vendors").stream()]
    products = [d.to_dict() | {"_id": d.id} for d in db.collection("products").stream()]
    categories = [d.to_dict() | {"_id": d.id} for d in db.collection("categories").stream()]
    quotations = [d.to_dict() | {"_id": d.id} for d in db.collection("quotations").stream()]
    images = [d.to_dict() | {"_id": d.id} for d in db.collection("product_images").stream()]
    return vendors, products, categories, quotations, images


# ---------------------------------------------------------------------------
# Scope classification
# ---------------------------------------------------------------------------
def _blob(p):
    return " ".join(
        str(p.get(k) or "")
        for k in ("name", "name_th", "material", "subcategory", "category", "notes")
    ).lower()


def classify(p):
    """Return one of: 'solid', 'engineered', 'needs_review', 'exclude'.

    'solid' / 'engineered' are in scope; the other two are out of scope.
    """
    cat = p.get("category")
    blob = _blob(p)
    mat_sub = " ".join(str(p.get(k) or "") for k in ("material", "subcategory", "name")).lower()

    # Hard composite exclusion first — wins even inside a flooring category.
    if any(m in mat_sub for m in COMPOSITE_MARKERS):
        return "exclude"

    # Bamboo and similar → surfaced for review, not silently dropped.
    if any(m in mat_sub for m in NEEDS_REVIEW_MARKERS):
        return "needs_review"

    if cat == "timber_flooring":
        return "solid"
    if cat == "engineered_flooring":
        return "engineered"

    # Filed elsewhere but unmistakably a genuine-wood floor (defensive; no such
    # record exists today, but keeps the rule honest if data shifts).
    if ("floor" in blob or "parquet" in blob) and (
        "solid" in mat_sub or "engineered" in mat_sub or "parquet" in mat_sub
    ):
        return "engineered"

    return "exclude"


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------
_NOTE_PRICE_PATTERNS = [
    # $36/sqm, $2.55/m, USD 36
    (r"(?:USD|US\$|\$)\s*([\d,]+(?:\.\d+)?)\s*(?:/|per)?\s*(sqm|m2|m²|m3|m|piece|pc|set|lm)?", "USD"),
    # 328 yuan/m2, 295 CNY, 280 RMB
    (r"([\d,]+(?:\.\d+)?)\s*(?:yuan|cny|rmb|元)\s*(?:/|per)?\s*(sqm|m2|m²|m3|m|piece|pc|set)?", "CNY"),
    # 360 THB / 360 baht
    (r"([\d,]+(?:\.\d+)?)\s*(?:thb|baht|฿)\s*(?:/|per)?\s*(sqm|m2|m²|m|piece|pc)?", "THB"),
    # 295 yuan/sqm written as "EXW price 295 yuan/sqm" already covered; EUR
    (r"(?:EUR|€)\s*([\d,]+(?:\.\d+)?)\s*(?:/|per)?\s*(sqm|m2|m²|m|piece|pc)?", "EUR"),
]

_UNIT_NORM = {
    "sqm": "sqm", "m2": "sqm", "m²": "sqm",
    "m": "lm", "lm": "lm", "lineal_meter": "lm", "linear_meter": "lm", "meter": "lm",
    "piece": "piece", "pc": "piece", "pcs": "piece",
    "set": "set", "m3": "m3", "lump_sum": "lump_sum", "lot": "lot",
}


def norm_unit(u):
    if not u:
        return None
    return _UNIT_NORM.get(str(u).strip().lower(), str(u).strip().lower())


def price_from_quotations(product_id, quotes_by_pid):
    """Return (price, currency, unit, source_label) from a quotation item, or None."""
    item = quotes_by_pid.get(product_id)
    if not item:
        return None
    q, it = item
    price = it.get("unit_price")
    if price is None:
        return None
    cur = (it.get("currency") or q.get("currency") or "").upper() or None
    unit = norm_unit(it.get("unit"))
    qno = q.get("quote_number") or q.get("_id")
    return float(price), cur, unit, f"quotation:{qno}"


def price_from_notes(notes):
    """Best-effort parse of a unit price out of free-text notes."""
    if not notes or not isinstance(notes, str):
        return None
    low = notes.lower()
    for pat, cur in _NOTE_PRICE_PATTERNS:
        m = re.search(pat, low)
        if m:
            try:
                val = float(m.group(1).replace(",", ""))
            except (ValueError, IndexError):
                continue
            unit = norm_unit(m.group(2)) if m.lastindex and m.lastindex >= 2 else None
            return val, cur, unit, "notes"
    return None


def parse_dims_mm(specs):
    """Return (length, width, thickness) in mm from a specifications dict, when present."""
    if not isinstance(specs, dict):
        return None
    L = specs.get("length")
    W = specs.get("width")
    T = specs.get("thickness")
    dims = specs.get("dimensions")
    if (L is None or W is None) and isinstance(dims, str):
        nums = re.findall(r"[\d.]+", dims)
        if len(nums) >= 2:
            try:
                L = L if L is not None else float(nums[0])
                W = W if W is not None else float(nums[1])
                if T is None and len(nums) >= 3:
                    T = float(nums[2])
            except ValueError:
                pass
    try:
        L = float(L) if L is not None else None
        W = float(W) if W is not None else None
    except (ValueError, TypeError):
        L = W = None
    return (L, W, T)


def to_thb_per_m2(price, currency, unit, specs):
    """Convert a raw price to ≈THB/m². Returns (thb_per_m2 or None, note)."""
    if price is None or currency is None:
        return None, "no price/currency"
    fx = FX_THB.get(currency.upper())
    if fx is None:
        return None, f"no FX for {currency}"
    thb = price * fx
    u = norm_unit(unit) or "sqm"  # default assumption stated on the page
    if u == "sqm":
        return round(thb, 1), ""
    if u == "lm":
        dims = parse_dims_mm(specs)
        if dims and dims[1]:  # width mm → m² per linear metre = width/1000
            area_per_lm = dims[1] / 1000.0
            if area_per_lm > 0:
                return round(thb / area_per_lm, 1), "from /lm via width"
        return None, "n/a (per-lm, no width)"
    if u == "piece":
        dims = parse_dims_mm(specs)
        if dims and dims[0] and dims[1]:
            area = (dims[0] / 1000.0) * (dims[1] / 1000.0)
            if area > 0:
                return round(thb / area, 1), "from /piece via dims"
        return None, "n/a (per-piece, no dims)"
    return None, f"n/a ({u})"


# ---------------------------------------------------------------------------
# Build the in-scope row set
# ---------------------------------------------------------------------------
def build_rows(vendors, products, quotations):
    vendor_by_id = {}
    for v in vendors:
        vid = v.get("vendor_id") or v.get("_id")
        vendor_by_id[vid] = v
        vendor_by_id.setdefault(v.get("_id"), v)

    def vendor_label(vid):
        v = vendor_by_id.get(vid)
        if not v:
            return vid or "(unknown vendor)"
        return v.get("name") or v.get("brand") or vid

    def vendor_country(vid):
        v = vendor_by_id.get(vid) or {}
        return v.get("country") or v.get("origin_country")

    # Index quotation items by product_id (first occurrence wins).
    quotes_by_pid = {}
    for q in quotations:
        for it in (q.get("items") or []):
            pid = it.get("product_id")
            if pid and pid not in quotes_by_pid:
                quotes_by_pid[pid] = (q, it)

    rows = []
    excluded = []        # composite floors filed under a flooring category
    needs_review = []    # ambiguous (bamboo, etc.)

    for p in products:
        kind = classify(p)
        if kind == "exclude":
            # Only report exclusions that are flooring-category records (the
            # interesting "mis-filed composite" cases); skip the hundreds of
            # genuinely-out-of-scope decking/cladding/structural records.
            if p.get("category") in FLOORING_CATEGORIES:
                excluded.append(p)
            continue
        if kind == "needs_review":
            needs_review.append(p)
            continue

        specs = p.get("specifications") or {}
        priced = price_from_quotations(p["_id"], quotes_by_pid) or price_from_notes(p.get("notes"))
        if priced:
            raw_price, currency, unit, src = priced
        else:
            raw_price, currency, unit, src = None, None, p.get("unit"), None
        thb_m2, conv_note = to_thb_per_m2(raw_price, currency, unit, specs)

        rows.append({
            "vendor": vendor_label(p.get("vendor_id")),
            "vendor_id": p.get("vendor_id"),
            "brand": p.get("brand"),
            "name": p.get("name"),
            "kind": kind,  # solid | engineered
            "species": p.get("material"),
            "dims": specs.get("dimensions") or _dims_str(specs),
            "finish": specs.get("finish") or specs.get("grade") or specs.get("pattern"),
            "origin": p.get("origin_country") or vendor_country(p.get("vendor_id")),
            "raw_price": raw_price,
            "currency": currency,
            "unit": unit,
            "thb_m2": thb_m2,
            "conv_note": conv_note,
            "source": src or p.get("source"),
            "from_pricelist": False,
        })

    # External Slack price-list rows (engineered, CNY/m²).
    for (sname, species, grade, dims, veneer, fmt, cny) in PRICELIST_ROWS:
        thb_m2, _ = to_thb_per_m2(cny, "CNY", "sqm", None)
        rows.append({
            "vendor": PRICELIST_VENDOR["name"],
            "vendor_id": PRICELIST_VENDOR["vendor_id"],
            "brand": PRICELIST_VENDOR["brand"],
            "name": sname,
            "kind": "engineered",
            "species": f"{species} (real-wood veneer {veneer}mm / birch core)",
            "dims": dims,
            "finish": f"{grade} · {fmt}",
            "origin": PRICELIST_VENDOR["country"],
            "raw_price": float(cny),
            "currency": "CNY",
            "unit": "sqm",
            "thb_m2": thb_m2,
            "conv_note": "",
            "source": PRICELIST_SOURCE,
            "from_pricelist": True,
        })

    return rows, excluded, needs_review, vendor_by_id


def _dims_str(specs):
    L, W, T = (specs.get("length"), specs.get("width"), specs.get("thickness"))
    if L and W:
        return f"{L}x{W}" + (f"x{T}" if T else "") + "mm"
    return ""


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
CSS = """
  :root {
    --bg: #0f172a; --fg: #e2e8f0; --muted: #94a3b8;
    --accent: #8003FF; --amber: #FFA900; --ok: #10b981; --warn: #f59e0b;
    --card: #1e293b; --border: #334155;
    --solid: #FFA900; --eng: #8003FF;
  }
  * { box-sizing: border-box; }
  body {
    font-family: 'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg); color: var(--fg); margin: 0; padding: 32px 20px; line-height: 1.55;
  }
  .wrap { max-width: 1240px; margin: 0 auto; }
  h1 { font-size: 32px; margin: 0 0 8px; }
  h2 { font-size: 22px; margin: 40px 0 12px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
  h3 { font-size: 15px; margin: 18px 0 8px; color: var(--accent); text-transform: uppercase; letter-spacing: 0.06em; }
  .eyebrow { display: inline-block; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.18em; color: var(--accent); margin-bottom: 8px; }
  .meta-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 20px 0; }
  .meta-card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 14px 18px; }
  .meta-card .lbl { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; }
  .meta-card .val { font-size: 26px; font-weight: 700; margin-top: 4px; }
  .status { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; }
  .status.ok { background: rgba(16,185,129,0.15); color: var(--ok); }
  table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }
  th, td { text-align: left; padding: 7px 9px; border-bottom: 1px solid var(--border); vertical-align: top; }
  th { color: var(--muted); font-weight: 600; font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.06em; }
  tbody tr:hover { background: rgba(128,3,255,0.06); }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
  code { background: rgba(128,3,255,0.15); color: #c4b5fd; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
  .tag { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; }
  .tag.solid { background: rgba(255,169,0,0.16); color: var(--amber); }
  .tag.eng { background: rgba(128,3,255,0.18); color: #c4b5fd; }
  .thb { font-weight: 700; color: var(--amber); }
  .na { color: var(--muted); }
  .bars td { padding: 4px 9px; }
  .barwrap { display: flex; align-items: center; gap: 10px; }
  .bar { display: inline-block; height: 10px; border-radius: 5px; background: var(--accent); }
  .bar.amber { background: var(--amber); }
  .callout { background: rgba(128,3,255,0.08); border-left: 3px solid var(--accent); padding: 14px 18px; border-radius: 4px; margin: 16px 0; font-size: 13.5px; }
  .callout.warn { background: rgba(245,158,11,0.08); border-left-color: var(--warn); }
  .callout ul { margin: 8px 0 0; padding-left: 18px; }
  .callout li { margin: 3px 0; }
  .filterbar { position: sticky; top: 0; z-index: 5; background: var(--bg); padding: 12px 0 8px; margin: 0 0 4px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  .filterbar input { flex: 1 1 320px; min-width: 220px; background: var(--card); border: 1px solid var(--border); border-radius: 8px; color: var(--fg); padding: 10px 14px; font-size: 14px; }
  .filterbar input:focus { outline: 2px solid var(--accent); outline-offset: 0; }
  .filterbar .count { color: var(--muted); font-size: 13px; white-space: nowrap; }
  .cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 22px; }
  footer { margin-top: 48px; color: var(--muted); font-size: 12px; border-top: 1px solid var(--border); padding-top: 16px; }
  a { color: var(--amber); }
  .sortable { cursor: pointer; user-select: none; }
  .sortable:hover { color: var(--fg); }
"""


def bar_row(label, n, maxn, amber=False):
    width = int(220 * n / maxn) if maxn else 0
    cls = "bar amber" if amber else "bar"
    return (
        f"      <tr class=\"bars\"><td>{esc(label)}</td>"
        f"<td class=\"num\">{n}</td>"
        f"<td><div class=\"barwrap\"><span class=\"{cls}\" style=\"width:{width}px\"></span></div></td></tr>\n"
    )


def build_html(rows, excluded, needs_review, vendor_by_id):
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    solid = [r for r in rows if r["kind"] == "solid"]
    engineered = [r for r in rows if r["kind"] == "engineered"]
    priced = [r for r in rows if r["thb_m2"] is not None]
    in_scope_vendor_ids = sorted({r["vendor_id"] for r in rows})

    # Dashboard aggregates -------------------------------------------------
    def species_key(r):
        s = (r["species"] or "").strip()
        # collapse to a coarse species bucket for the dashboard
        low = s.lower()
        for k in ("oak", "rovere", "walnut", "noce", "teak", "hickory", "cherry",
                  "maple", "acero", "mahogany"):
            if k in low:
                return {"rovere": "Oak", "noce": "Walnut", "acero": "Maple"}.get(k, k.title())
        return s.split(",")[0].strip() or "(unspecified)"

    species_counts = Counter(species_key(r) for r in rows)
    kind_counts = Counter(r["kind"] for r in rows)
    origin_counts = Counter((r["origin"] or "(unknown)") for r in rows)

    bands = Counter()
    for r in priced:
        v = r["thb_m2"]
        if v < 1000:
            bands["< 1,000 THB/m²"] += 1
        elif v < 2000:
            bands["1,000–2,000 THB/m²"] += 1
        else:
            bands["2,000+ THB/m²"] += 1

    out = []
    out.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>wooden-products — Solid Wood Flooring · Price Comparison</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

  <span class="eyebrow">Dashboard · Price Comparison</span>
  <h1>Solid Wood Flooring — Cross-Vendor Comparison</h1>
  <p style="color: var(--muted); margin: 0;">Genuine solid timber &amp; real-wood engineered / parquet flooring only.
  Live snapshot of the <code>products-wood</code> Firestore database (GCP <code>ai-agents-go</code>, <code>asia-southeast1</code>),
  plus one external Slack price list. Generated {generated} · <span class="status ok">sourced live from Firestore</span></p>

  <div class="meta-grid">
    <div class="meta-card"><div class="lbl">In-scope vendors</div><div class="val">{len(in_scope_vendor_ids)}</div></div>
    <div class="meta-card"><div class="lbl">In-scope products</div><div class="val">{len(rows)}</div></div>
    <div class="meta-card"><div class="lbl">With pricing</div><div class="val">{len(priced)}</div></div>
    <div class="meta-card"><div class="lbl">Solid</div><div class="val" style="color:var(--amber)">{len(solid)}</div></div>
    <div class="meta-card"><div class="lbl">Engineered</div><div class="val" style="color:#c4b5fd">{len(engineered)}</div></div>
  </div>
""")

    # ---- Scope & method --------------------------------------------------
    out.append("  <h2>Scope &amp; method</h2>\n")
    excl_items = "".join(
        f"<li><code>{esc(p['_id'])}</code> — {esc(p.get('name'))} "
        f"(<em>{esc(p.get('material') or p.get('subcategory'))}</em>, category "
        f"<code>{esc(p.get('category'))}</code>)</li>"
        for p in excluded
    )
    review_items = "".join(
        f"<li><code>{esc(p['_id'])}</code> — {esc(p.get('name'))} "
        f"(<em>{esc(p.get('material') or p.get('subcategory'))}</em>)</li>"
        for p in needs_review
    )
    fx_str = ", ".join(f"{k}≈{v}" for k, v in FX_THB.items() if k not in ("RMB",))
    out.append(f"""  <div class="callout">
    <strong>Included</strong> — genuine wood flooring only:
    (a) one-piece <strong>solid timber</strong> (<span class="tag solid">solid</span>, Firestore category <code>timber_flooring</code>), and
    (b) <strong>real-wood engineered / parquet</strong> (<span class="tag eng">engineered</span>, <code>engineered_flooring</code>) —
    multi-layer with a genuine solid-wood wear layer.
    Scope is decided per-record, not by category name alone: a flooring record is dropped if its
    <em>material / subcategory / name</em> matches a composite marker
    (WPC, SPC, LVT, vinyl, laminate, HDF/MDF/fiberboard, wood-/stone-plastic or -polymer composite).
    <br><br>
    <strong>Excluded entirely</strong> — WPC / artificial-wood / composite, SPC / stone-plastic, LVT / vinyl, and
    laminate / HDF / MDF "decor" floors. The Slack price list's pages 10–11 (金刚面 "diamond-face" &amp; 强化 "reinforced",
    both <em>"surface = HD decorative paper"</em>) are laminate and were left out.
    <br><br>
    <strong>Pricing</strong> — raw unit price taken from structured <code>quotations.items[]</code> (by <code>product_id</code>) first,
    else parsed from free-text <code>notes</code>; normalised to <span class="thb">≈THB/m²</span> using a
    <strong>static, approximate FX table</strong> (THB per unit, as of {FX_DATE}): {fx_str}.
    Per-piece / per-linear-metre prices are converted to m² via product dimensions where possible; otherwise ≈THB/m² shows
    <span class="na">n/a</span>. FX is hand-set, <strong>not</strong> a live feed. Prices are only ever shown when sourced.
    <br><br>
    <strong>Record counts</strong> — {len(rows)} in scope ({len(solid)} solid, {len(engineered)} engineered);
    {len(priced)} with a price; {len(excluded)} mis-filed composite floors excluded; {len(needs_review)} needs-review.
  </div>
""")
    out.append(f"""  <div class="callout warn">
    <strong>Excluded — composite floors mis-filed under a flooring category ({len(excluded)})</strong>
    <ul>{excl_items or '<li>none</li>'}</ul>
    <strong style="display:block;margin-top:10px">Needs review — ambiguous / not timber ({len(needs_review)})</strong>
    <ul>{review_items or '<li>none</li>'}</ul>
    <strong style="display:block;margin-top:10px">Known but not yet in <code>products</code></strong>
    <ul><li>Pinecross solid pine flooring (e.g. 140×19 mm corrugated, 360 THB/lm) appears in quotation
    <code>PC&nbsp;18112021</code> but has no product record — genuine solid wood, not yet ingested.</li></ul>
  </div>
""")

    # ---- Dashboard -------------------------------------------------------
    out.append("  <h2>Dashboard</h2>\n  <div class=\"cols\">\n")

    # Solid vs engineered
    out.append("    <div><h3>Solid vs engineered</h3>\n    <table>\n      <tbody>\n")
    mk = max(kind_counts.values()) if kind_counts else 1
    for k in ("solid", "engineered"):
        out.append(bar_row(k.title(), kind_counts.get(k, 0), mk, amber=(k == "solid")))
    out.append("      </tbody>\n    </table></div>\n")

    # Species
    out.append("    <div><h3>By species</h3>\n    <table>\n      <tbody>\n")
    ms = max(species_counts.values()) if species_counts else 1
    for sp, n in species_counts.most_common():
        out.append(bar_row(sp, n, ms))
    out.append("      </tbody>\n    </table></div>\n")

    # Origin
    out.append("    <div><h3>By origin country</h3>\n    <table>\n      <tbody>\n")
    mo = max(origin_counts.values()) if origin_counts else 1
    for oc, n in origin_counts.most_common():
        out.append(bar_row(oc, n, mo))
    out.append("      </tbody>\n    </table></div>\n")

    # Price bands
    out.append("    <div><h3>Price bands (≈THB/m²)</h3>\n    <table>\n      <tbody>\n")
    mb = max(bands.values()) if bands else 1
    for label in ("< 1,000 THB/m²", "1,000–2,000 THB/m²", "2,000+ THB/m²"):
        out.append(bar_row(label, bands.get(label, 0), mb, amber=True))
    out.append("      </tbody>\n    </table>\n")
    out.append(f"    <p style=\"color:var(--muted);font-size:12px;margin:6px 0 0\">{len(priced)} of {len(rows)} products priced.</p></div>\n")
    out.append("  </div>\n")

    # ---- By-vendor summary ----------------------------------------------
    out.append("  <h2>By-vendor summary</h2>\n")
    out.append("  <table>\n    <thead><tr><th>Vendor</th><th>Country</th><th>Type</th>"
               "<th class=\"num\">Solid</th><th class=\"num\">Eng.</th><th class=\"num\">SKUs</th>"
               "<th class=\"num\">Priced</th><th class=\"num\">Min ≈THB/m²</th><th class=\"num\">Avg</th>"
               "<th class=\"num\">Max</th></tr></thead>\n    <tbody>\n")
    by_vendor = defaultdict(list)
    for r in rows:
        by_vendor[r["vendor_id"]].append(r)

    def vmeta(vid):
        if vid == PRICELIST_VENDOR["vendor_id"]:
            return PRICELIST_VENDOR["name"], PRICELIST_VENDOR["country"], "price list"
        v = vendor_by_id.get(vid) or {}
        return (v.get("name") or vid, v.get("country") or v.get("origin_country"), v.get("type"))

    vsummary = []
    for vid, vr in by_vendor.items():
        vp = [r["thb_m2"] for r in vr if r["thb_m2"] is not None]
        name, country, vtype = vmeta(vid)
        vsummary.append((name, country, vtype, vr, vp))
    vsummary.sort(key=lambda x: (-len(x[3]), x[0].lower()))

    for name, country, vtype, vr, vp in vsummary:
        nsolid = sum(1 for r in vr if r["kind"] == "solid")
        neng = sum(1 for r in vr if r["kind"] == "engineered")
        if vp:
            mn, mx = min(vp), max(vp)
            avg = sum(vp) / len(vp)
            mn_s, avg_s, mx_s = f"{mn:,.0f}", f"{avg:,.0f}", f"{mx:,.0f}"
        else:
            mn_s = avg_s = mx_s = "<span class=\"na\">n/a</span>"
        out.append(
            "      <tr><td>{name}</td><td>{country}</td><td>{vtype}</td>"
            "<td class=\"num\">{ns}</td><td class=\"num\">{ne}</td><td class=\"num\">{tot}</td>"
            "<td class=\"num\">{np}</td><td class=\"num\">{mn}</td><td class=\"num\">{avg}</td>"
            "<td class=\"num\">{mx}</td></tr>\n".format(
                name=esc(name), country=esc(country), vtype=esc(vtype),
                ns=nsolid, ne=neng, tot=len(vr), np=len(vp), mn=mn_s, avg=avg_s, mx=mx_s,
            )
        )
    out.append("    </tbody>\n  </table>\n")

    # ---- Price comparison table -----------------------------------------
    out.append("  <h2>Price comparison — one row per product</h2>\n")
    out.append(
        "  <p style=\"color:var(--muted);font-size:13px;margin:4px 0 0\">"
        "Pre-sorted by ≈THB/m² ascending (priced first, then unpriced). "
        "Click a column header to re-sort; type to filter.</p>\n"
    )
    out.append(
        "  <div class=\"filterbar\">\n"
        "    <input id=\"q\" type=\"text\" placeholder=\"Filter — vendor, product, species, origin, source…\" "
        "oninput=\"filterRows()\" aria-label=\"Filter products\">\n"
        "    <span class=\"count\" id=\"shown\"></span>\n"
        "  </div>\n"
    )
    out.append("  <table id=\"cmp\">\n    <thead><tr>"
               "<th class=\"sortable\" onclick=\"sortBy(0,false)\">Vendor / brand</th>"
               "<th class=\"sortable\" onclick=\"sortBy(1,false)\">Product</th>"
               "<th class=\"sortable\" onclick=\"sortBy(2,false)\">Type</th>"
               "<th class=\"sortable\" onclick=\"sortBy(3,false)\">Species / material</th>"
               "<th>Dims L×W×T</th>"
               "<th>Finish / grade</th>"
               "<th class=\"sortable\" onclick=\"sortBy(6,false)\">Origin</th>"
               "<th class=\"num sortable\" onclick=\"sortBy(7,true)\">Raw price</th>"
               "<th class=\"num sortable\" onclick=\"sortBy(8,true)\">≈THB/m²</th>"
               "<th>Source</th></tr></thead>\n    <tbody>\n")

    # Pre-sort by THB/m² asc, unpriced last.
    def sort_key(r):
        return (0, r["thb_m2"]) if r["thb_m2"] is not None else (1, 0)
    for r in sorted(rows, key=sort_key):
        tag = f"<span class=\"tag {'solid' if r['kind']=='solid' else 'eng'}\">{r['kind']}</span>"
        vb = esc(r["vendor"]) + (f"<br><span style=\"color:var(--muted);font-size:11px\">{esc(r['brand'])}</span>" if r.get("brand") else "")
        if r["raw_price"] is not None:
            unit = r["unit"] or "?"
            raw = f"{r['raw_price']:,.2f} {esc(r['currency'])}/{esc(unit)}"
            rawval = r["raw_price"]
        else:
            raw = "<span class=\"na\">—</span>"
            rawval = ""
        if r["thb_m2"] is not None:
            thb = f"<span class=\"thb\">{r['thb_m2']:,.0f}</span>"
            thbval = r["thb_m2"]
            if r["conv_note"]:
                thb += f"<br><span style=\"color:var(--muted);font-size:10px\">{esc(r['conv_note'])}</span>"
        else:
            thb = "<span class=\"na\">n/a</span>"
            thbval = ""
        src = r["source"] or ""
        src_html = f"<code>{esc(src)}</code>"
        search_text = " ".join(str(x) for x in [
            r["vendor"], r["brand"], r["name"], r["kind"], r["species"],
            r["origin"], r["source"], r["dims"], r["finish"],
        ] if x).lower()
        out.append(
            "      <tr class=\"prow\" data-text=\"{st}\">"
            "<td data-v=\"{vsort}\">{vb}</td>"
            "<td data-v=\"{nsort}\">{name}</td>"
            "<td data-v=\"{kind}\">{tag}</td>"
            "<td data-v=\"{spsort}\">{species}</td>"
            "<td>{dims}</td>"
            "<td>{finish}</td>"
            "<td data-v=\"{origin}\">{origin}</td>"
            "<td class=\"num\" data-v=\"{rawval}\">{raw}</td>"
            "<td class=\"num\" data-v=\"{thbval}\">{thb}</td>"
            "<td>{src}</td></tr>\n".format(
                st=html.escape(search_text, quote=True),
                vsort=html.escape((r["vendor"] or "").lower(), quote=True),
                nsort=html.escape((r["name"] or "").lower(), quote=True),
                spsort=html.escape((r["species"] or "").lower(), quote=True),
                origin=esc(r["origin"]),
                kind=esc(r["kind"]),
                vb=vb, name=esc(r["name"]), tag=tag, species=esc(r["species"]),
                dims=esc(r["dims"]), finish=esc(r["finish"]),
                rawval=rawval, raw=raw, thbval=thbval, thb=thb, src=src_html,
            )
        )
    out.append("    </tbody>\n  </table>\n")

    # ---- JS + footer -----------------------------------------------------
    out.append("""
  <script>
    var ALL = %d;
    function filterRows() {
      var q = document.getElementById('q').value.trim().toLowerCase();
      var rows = document.querySelectorAll('#cmp tr.prow');
      var shown = 0;
      rows.forEach(function (r) {
        var match = !q || r.getAttribute('data-text').indexOf(q) !== -1;
        r.style.display = match ? '' : 'none';
        if (match) shown++;
      });
      var c = document.getElementById('shown');
      c.textContent = q ? (shown + ' of ' + ALL + ' products') : (ALL + ' products');
    }
    var sortState = {};
    function sortBy(col, numeric) {
      var tbody = document.querySelector('#cmp tbody');
      var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr.prow'));
      var dir = sortState[col] === 'asc' ? 'desc' : 'asc';
      sortState = {}; sortState[col] = dir;
      rows.sort(function (a, b) {
        var av = a.children[col].getAttribute('data-v') || '';
        var bv = b.children[col].getAttribute('data-v') || '';
        if (numeric) {
          var an = av === '' ? Infinity : parseFloat(av);
          var bn = bv === '' ? Infinity : parseFloat(bv);
          return dir === 'asc' ? an - bn : bn - an;
        }
        return dir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      });
      rows.forEach(function (r) { tbody.appendChild(r); });
    }
    filterRows();
  </script>

  <footer>
    wooden-products · solid wood flooring price comparison · generated %s by
    <code>scripts/firestore/gen_solid_wood_dashboard.py</code> · sources: Firestore <code>products-wood</code>
    (vendors / products / categories / quotations / product_images) + Slack price list %s.
    FX static &amp; approximate (as of %s) — for indicative comparison only, not a quotation.
  </footer>
</div>
</body>
</html>
""" % (len(rows), generated, PRICELIST_LABEL, FX_DATE))

    return "".join(out)


def main():
    db = get_client()
    vendors, products, categories, quotations, images = fetch_all(db)
    rows, excluded, needs_review, vendor_by_id = build_rows(vendors, products, quotations)
    page = build_html(rows, excluded, needs_review, vendor_by_id)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)

    solid = sum(1 for r in rows if r["kind"] == "solid")
    eng = sum(1 for r in rows if r["kind"] == "engineered")
    priced = sum(1 for r in rows if r["thb_m2"] is not None)
    print(f"[OK] wrote {OUTPUT_PATH}")
    print(f"     in-scope products={len(rows)} (solid={solid} engineered={eng}) "
          f"priced={priced} excluded={len(excluded)} needs_review={len(needs_review)}")
    print(f"     in-scope vendors={len({r['vendor_id'] for r in rows})} "
          f"(incl. external Slack price list: {len(PRICELIST_ROWS)} rows)")


if __name__ == "__main__":
    main()
