"""
gen_product_summary.py — Generate a self-contained HTML product summary
for the wooden-products catalog, sourced live from the `products-wood`
Firestore database.

Reads ALL docs from `vendors`, `products`, `categories`, `product_images`
via the shared `setup_db.get_client()` helper (bound to products-wood) and
writes a single static, dependency-free HTML page to:

    docs/summaries/product-summary.html

Per Rule 13 all generated HTML lives under docs/ in a typed subfolder.
The page is served privately via the go-access-gateway at
https://gateway.goco.bz/wooden-products/docs/summaries/product-summary.html

Usage:
    PYTHONIOENCODING=utf-8 python scripts/firestore/gen_product_summary.py

Deterministic / re-runnable — overwrites the output file each run.
"""

import html
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

# Allow `from setup_db import get_client` regardless of CWD.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from setup_db import get_client  # noqa: E402

WECHAT_SOURCE = "wechat-automation:wechat-documents"

# Output path is resolved relative to the project root (two levels up from
# scripts/firestore/), so the generator works from any CWD.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "docs", "summaries", "product-summary.html")


def esc(value):
    """HTML-escape a value, treating None/empty as an em-dash placeholder."""
    if value is None:
        return "&mdash;"
    text = str(value).strip()
    return html.escape(text) if text else "&mdash;"


def fetch_all(db):
    """Pull every doc from the four catalog collections into memory."""
    vendors = [d.to_dict() | {"_id": d.id} for d in db.collection("vendors").stream()]
    products = [d.to_dict() | {"_id": d.id} for d in db.collection("products").stream()]
    categories = [d.to_dict() | {"_id": d.id} for d in db.collection("categories").stream()]
    images = [d.to_dict() | {"_id": d.id} for d in db.collection("product_images").stream()]
    return vendors, products, categories, images


def spec_summary(specs):
    """Compress the specifications dict into a short readable cell."""
    if not isinstance(specs, dict):
        return ""
    parts = []
    for key in ("dimensions", "finish", "pattern", "construction", "grade"):
        val = specs.get(key)
        if val:
            parts.append(f"{key}: {val}")
    return " · ".join(parts)


def build_html(vendors, products, categories, images):
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Lookups -------------------------------------------------------------
    vendor_by_id = {}
    for v in vendors:
        vid = v.get("vendor_id") or v.get("_id")
        vendor_by_id[vid] = v
        # also index by doc id for safety
        vendor_by_id.setdefault(v.get("_id"), v)

    cat_name = {}
    for c in categories:
        cid = c.get("category_id") or c.get("_id")
        cat_name[cid] = c.get("name") or cid

    def cat_label(cid):
        if not cid:
            return "(uncategorised)"
        return cat_name.get(cid, cid)

    def vendor_label(vid):
        v = vendor_by_id.get(vid)
        if not v:
            return vid or "(unknown vendor)"
        return v.get("name") or v.get("brand") or vid

    # By-category counts --------------------------------------------------
    cat_counts = Counter(p.get("category") for p in products)

    # By-vendor counts ----------------------------------------------------
    vendor_counts = Counter(p.get("vendor_id") for p in products)

    # Images per product (for context, not required) ----------------------
    # Totals --------------------------------------------------------------
    totals = {
        "vendors": len(vendors),
        "products": len(products),
        "categories": len(categories),
        "images": len(images),
    }

    # WeChat highlight ----------------------------------------------------
    wechat = [p for p in products if p.get("source") == WECHAT_SOURCE]

    # ---- HTML pieces ----------------------------------------------------
    out = []
    out.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>wooden-products — Product Summary</title>
<style>
  :root {{
    --bg: #0f172a;
    --fg: #e2e8f0;
    --muted: #94a3b8;
    --accent: #8003FF;
    --amber: #FFA900;
    --ok: #10b981;
    --warn: #f59e0b;
    --card: #1e293b;
    --border: #334155;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: 'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--fg);
    margin: 0;
    padding: 32px 20px;
    line-height: 1.55;
  }}
  .wrap {{ max-width: 1180px; margin: 0 auto; }}
  h1 {{ font-size: 32px; margin: 0 0 8px; }}
  h2 {{ font-size: 22px; margin: 36px 0 12px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }}
  h3 {{ font-size: 16px; margin: 16px 0 8px; color: var(--accent); }}
  .eyebrow {{
    display: inline-block;
    font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.18em;
    color: var(--accent);
    margin-bottom: 8px;
  }}
  .meta-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px; margin: 20px 0;
  }}
  .meta-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 18px;
  }}
  .meta-card .lbl {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; }}
  .meta-card .val {{ font-size: 26px; font-weight: 700; margin-top: 4px; }}
  .status {{
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
  }}
  .status.ok   {{ background: rgba(16,185,129,0.15); color: var(--ok); }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13.5px; }}
  th, td {{ text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--border); vertical-align: top; }}
  th {{ color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
  tbody tr:hover {{ background: rgba(128,3,255,0.06); }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  code {{
    background: rgba(128,3,255,0.15);
    color: #c4b5fd;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 12.5px;
  }}
  .bar {{
    display: inline-block; height: 8px; border-radius: 4px;
    background: var(--accent); vertical-align: middle; margin-left: 8px;
  }}
  .callout {{
    background: rgba(128,3,255,0.08);
    border-left: 3px solid var(--accent);
    padding: 12px 16px;
    border-radius: 4px;
    margin: 16px 0;
  }}
  .filterbar {{
    position: sticky; top: 0; z-index: 5;
    background: var(--bg); padding: 12px 0 8px; margin: 0 0 4px;
    display: flex; gap: 12px; align-items: center; flex-wrap: wrap;
  }}
  .filterbar input {{
    flex: 1 1 320px; min-width: 220px;
    background: var(--card); border: 1px solid var(--border); border-radius: 8px;
    color: var(--fg); padding: 10px 14px; font-size: 14px;
  }}
  .filterbar input:focus {{ outline: 2px solid var(--accent); outline-offset: 0; }}
  .filterbar .count {{ color: var(--muted); font-size: 13px; white-space: nowrap; }}
  .vgroup-head td {{
    background: var(--card); font-weight: 700; color: var(--amber);
    font-size: 13px; letter-spacing: 0.02em;
  }}
  .pill {{
    display: inline-block; padding: 1px 8px; border-radius: 999px;
    background: rgba(255,169,0,0.12); color: var(--amber);
    font-size: 11px; font-weight: 600;
  }}
  footer {{
    margin-top: 48px;
    color: var(--muted);
    font-size: 12px;
    border-top: 1px solid var(--border);
    padding-top: 16px;
  }}
  a {{ color: var(--amber); }}
</style>
</head>
<body>
<div class="wrap">

  <span class="eyebrow">Product Summary</span>
  <h1>wooden-products — Catalog Summary</h1>
  <p style="color: var(--muted); margin: 0;">Live snapshot of the <code>products-wood</code> Firestore database (GCP <code>ai-agents-go</code>, <code>asia-southeast1</code>). Generated {generated} · <span class="status ok">sourced live from Firestore</span></p>

  <div class="meta-grid">
    <div class="meta-card"><div class="lbl">Vendors</div><div class="val">{totals['vendors']}</div></div>
    <div class="meta-card"><div class="lbl">Products</div><div class="val">{totals['products']}</div></div>
    <div class="meta-card"><div class="lbl">Categories</div><div class="val">{totals['categories']}</div></div>
    <div class="meta-card"><div class="lbl">Product images / docs</div><div class="val">{totals['images']}</div></div>
  </div>
""")

    # ---- By-category ----------------------------------------------------
    max_cat = max(cat_counts.values()) if cat_counts else 1
    out.append("  <h2>Products by category</h2>\n  <table>\n    <thead><tr><th>Category</th><th>Category ID</th><th class=\"num\">Products</th><th>Share</th></tr></thead>\n    <tbody>\n")
    for cid, n in sorted(cat_counts.items(), key=lambda kv: kv[1], reverse=True):
        width = int(140 * n / max_cat) if max_cat else 0
        out.append(
            f"      <tr><td>{esc(cat_label(cid))}</td><td><code>{esc(cid)}</code></td>"
            f"<td class=\"num\">{n}</td><td><span class=\"bar\" style=\"width:{width}px\"></span></td></tr>\n"
        )
    out.append("    </tbody>\n  </table>\n")

    # ---- By-vendor ------------------------------------------------------
    out.append("  <h2>Products by vendor</h2>\n")
    out.append("  <p style=\"color:var(--muted);font-size:13px;margin:4px 0 0\">All {} vendors, sorted by product count.</p>\n".format(len(vendors)))
    out.append("  <table>\n    <thead><tr><th>Vendor</th><th>Brand</th><th>Country</th><th>Type</th><th class=\"num\">Products</th></tr></thead>\n    <tbody>\n")
    # Order: vendors with products first (desc), then zero-product vendors alphabetically.
    rows = []
    for v in vendors:
        vid = v.get("vendor_id") or v.get("_id")
        rows.append((v, vendor_counts.get(vid, 0)))
    rows.sort(key=lambda r: (-r[1], (r[0].get("name") or "").lower()))
    for v, n in rows:
        out.append(
            "      <tr><td>{name}</td><td>{brand}</td><td>{country}</td><td>{vtype}</td><td class=\"num\">{n}</td></tr>\n".format(
                name=esc(v.get("name")),
                brand=esc(v.get("brand")),
                country=esc(v.get("country") or v.get("origin_country")),
                vtype=esc(v.get("type")),
                n=n,
            )
        )
    out.append("    </tbody>\n  </table>\n")

    # ---- WeChat highlight ----------------------------------------------
    out.append("  <h2>Recently ingested — WeChat wooden-flooring</h2>\n")
    out.append(
        "  <div class=\"callout\">{n} genuine-wood flooring products were ingested from the "
        "<code>wechat-automation</code> handoff (<code>source = \"{src}\"</code>) — the "
        "Bimei / Foglie d'Oro parquet, Visconti / Giorio Casa, and Elegant Living additions. "
        "(CHANGELOG 0.14.0, PR #25.)</div>\n".format(n=len(wechat), src=WECHAT_SOURCE)
    )
    out.append("  <table>\n    <thead><tr><th>Name</th><th>Brand</th><th>Vendor</th><th>Material / species</th><th>Key specs</th></tr></thead>\n    <tbody>\n")
    for p in sorted(wechat, key=lambda x: ((x.get("brand") or ""), (x.get("name") or ""))):
        out.append(
            "      <tr><td>{name}</td><td>{brand}</td><td>{vendor}</td><td>{material}</td><td>{specs}</td></tr>\n".format(
                name=esc(p.get("name")),
                brand=esc(p.get("brand")),
                vendor=esc(vendor_label(p.get("vendor_id"))),
                material=esc(p.get("material")),
                specs=esc(spec_summary(p.get("specifications"))),
            )
        )
    out.append("    </tbody>\n  </table>\n")

    # ---- Full products table (grouped by vendor, filterable) ------------
    out.append("  <h2>All products</h2>\n")
    out.append(
        "  <div class=\"filterbar\">\n"
        "    <input id=\"q\" type=\"text\" placeholder=\"Filter products — name, brand, category, material, spec, origin, source…\" "
        "oninput=\"filterRows()\" aria-label=\"Filter products\">\n"
        "    <span class=\"count\" id=\"shown\"></span>\n"
        "  </div>\n"
    )
    out.append("  <table id=\"products\">\n")
    out.append(
        "    <thead><tr><th>Product</th><th>Brand</th><th>Category</th><th>Material / species</th>"
        "<th>Key specs</th><th>Origin</th><th>Source</th></tr></thead>\n    <tbody>\n"
    )

    # Group products by vendor, vendors ordered by product count desc.
    by_vendor = defaultdict(list)
    for p in products:
        by_vendor[p.get("vendor_id")].append(p)

    ordered_vendor_ids = sorted(
        by_vendor.keys(),
        key=lambda vid: (-len(by_vendor[vid]), vendor_label(vid).lower()),
    )

    for vid in ordered_vendor_ids:
        plist = sorted(by_vendor[vid], key=lambda x: (x.get("category") or "", (x.get("name") or "").lower()))
        vlabel = vendor_label(vid)
        vmeta = vendor_by_id.get(vid, {})
        vcountry = vmeta.get("country") or ""
        head_text = "{}  ·  {} product{}".format(vlabel, len(plist), "" if len(plist) == 1 else "s")
        if vcountry:
            head_text += "  ·  " + vcountry
        # group header row — searchable text in data-text so it stays visible while filtering matches
        out.append(
            "      <tr class=\"vgroup-head\" data-group=\"{gid}\"><td colspan=\"7\">{head}</td></tr>\n".format(
                gid=esc(vid), head=esc(head_text)
            )
        )
        for p in plist:
            specs = spec_summary(p.get("specifications"))
            search_text = " ".join(
                str(x) for x in [
                    p.get("name"), p.get("name_th"), p.get("brand"), cat_label(p.get("category")),
                    p.get("category"), p.get("material"), specs, p.get("origin_country"),
                    p.get("source"), vlabel,
                ] if x
            ).lower()
            out.append(
                "      <tr class=\"prow\" data-group=\"{gid}\" data-text=\"{stext}\">"
                "<td>{name}</td><td>{brand}</td><td>{cat}</td><td>{material}</td>"
                "<td>{specs}</td><td>{origin}</td><td><code>{source}</code></td></tr>\n".format(
                    gid=esc(vid),
                    stext=html.escape(search_text, quote=True),
                    name=esc(p.get("name")),
                    brand=esc(p.get("brand")),
                    cat=esc(cat_label(p.get("category"))),
                    material=esc(p.get("material")),
                    specs=esc(specs),
                    origin=esc(p.get("origin_country")),
                    source=esc(p.get("source")),
                )
            )
    out.append("    </tbody>\n  </table>\n")

    # ---- Filter JS + footer --------------------------------------------
    total_products = len(products)
    out.append("""
  <script>
    var ALL = %d;
    function filterRows() {
      var q = document.getElementById('q').value.trim().toLowerCase();
      var rows = document.querySelectorAll('#products tr.prow');
      var groups = {};
      var shown = 0;
      rows.forEach(function (r) {
        var match = !q || r.getAttribute('data-text').indexOf(q) !== -1;
        r.style.display = match ? '' : 'none';
        if (match) { shown++; groups[r.getAttribute('data-group')] = true; }
      });
      // Hide group headers whose vendor has no visible rows.
      document.querySelectorAll('#products tr.vgroup-head').forEach(function (h) {
        h.style.display = (!q || groups[h.getAttribute('data-group')]) ? '' : 'none';
      });
      var c = document.getElementById('shown');
      c.textContent = q ? (shown + ' of ' + ALL + ' products') : (ALL + ' products');
    }
    filterRows();
  </script>

  <footer>
    wooden-products · product summary · generated %s by <code>scripts/firestore/gen_product_summary.py</code> · source: Firestore <code>products-wood</code>
  </footer>
</div>
</body>
</html>
""" % (total_products, generated))

    return "".join(out)


def main():
    db = get_client()
    vendors, products, categories, images = fetch_all(db)
    page = build_html(vendors, products, categories, images)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)

    print(f"[OK] wrote {OUTPUT_PATH}")
    print(f"     vendors={len(vendors)} products={len(products)} "
          f"categories={len(categories)} images={len(images)}")


if __name__ == "__main__":
    main()
