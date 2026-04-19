"""Generate /wpc-profile/ pages from data/catalog/leka-taxonomy.json.

Writes:
  website/salesheet/wpc-profile/index.html               (main landing)
  website/salesheet/wpc-profile/decking/index.html
  website/salesheet/wpc-profile/cladding/index.html
  website/salesheet/wpc-profile/panels/index.html
  website/salesheet/wpc-profile/structure/index.html
  website/salesheet/wpc-profile/diy-tiles/index.html
  website/salesheet/wpc-profile/colours/index.html

Uses the shared css/leka.css. No inline design tokens (single source of truth).
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAX = json.loads((ROOT / "data" / "catalog" / "leka-taxonomy.json").read_text(encoding="utf-8"))
OUT = ROOT / "website" / "salesheet" / "wpc-profile"

PALETTE = {c["code"]: c for c in TAX["palette_full"]}
TEXTURES = {t["code"]: t for t in TAX["textures"]}
SERIES = TAX["series"]
CATS = TAX["categories"]


def nav(active_slug: str) -> str:
    """Shared nav bar. active_slug highlights the current category."""
    links = [
        ("/wpc-profile/decking/",    "decking",    "Decking"),
        ("/wpc-profile/cladding/",   "cladding",   "Cladding"),
        ("/wpc-profile/panels/",     "panels",     "Panels"),
        ("/wpc-fence/",              "fence",      "Fence"),
        ("/wpc-profile/structure/",  "structure",  "Structure"),
        ("/wpc-profile/diy-tiles/",  "diy-tiles",  "DIY Tiles"),
        ("/wpc-profile/colours/",    "colours",    "Colours"),
    ]
    items = "".join(
        f'<a href="{href}" class="{"active" if slug == active_slug else ""}">{label}</a>'
        for href, slug, label in links
    )
    return f"""<nav class="nav">
  <div class="nav-inner">
    <a href="/wpc-profile/" class="brand">LEKA<span class="dot">.</span> STUDIO</a>
    <div class="nav-links">{items}</div>
    <a href="/quote/?product=wpc-profile" class="nav-cta">Get a Quote</a>
  </div>
</nav>"""


def crumb(trail: list[tuple[str, str]]) -> str:
    parts = []
    for i, (href, label) in enumerate(trail):
        if i > 0:
            parts.append('<span class="sep">/</span>')
        if href:
            parts.append(f'<a href="{href}">{label}</a>')
        else:
            parts.append(f'<span>{label}</span>')
    return f'<div class="crumb"><div class="container">{"".join(parts)}</div></div>'


def footer() -> str:
    return """<footer>
  <div class="f-inner">
    <div>© 2026 GO Corporation Co., Ltd. · Leka Studio — Outdoor Living Division</div>
    <div>
      <a href="/wpc-profile/">All Profiles</a> ·
      <a href="/wpc-fence/">Fence Collection</a> ·
      <a href="/quote/">Request a Quote</a>
    </div>
  </div>
</footer>"""


def cta_section(msg: str = "Specify your project.", sub: str = "Request a quotation with quantity, dimensions and target delivery. Landed-cost pricing within one working day.") -> str:
    return f"""<section class="cta">
  <div class="container">
    <h2>{msg}</h2>
    <p>{sub}</p>
    <a href="/quote/?product=wpc-profile" class="cta-btn">Request a Quotation →</a>
  </div>
</section>"""


def palette_strip(category_slug: str, codes: list[str]) -> str:
    """Palette strip showing the 8 Leka colours (real grain photos)."""
    chips = "".join(
        f'<div class="pal-chip" title="{PALETTE[c]["name"]} · {c}">'
        f'<img src="/wpc-profile/images/grain/{c.lower()}-{PALETTE[c]["name"].lower().replace(" ", "-")}-woodgrain.jpg" alt="{PALETTE[c]["name"]} wood-grain swatch">'
        f'<div class="lbl">{PALETTE[c]["name"]}</div>'
        f'</div>'
        for c in codes
    )
    return f"""<div class="palette-strip">
  <div class="container">
    <h4>Available in 8 colourways</h4>
    <div class="pal-row">{chips}</div>
    <a href="/wpc-profile/colours/" style="flex-shrink:0;font-size:13px;font-weight:700;color:var(--lk-purple);text-transform:uppercase;letter-spacing:.1em;margin-left:auto">View Full Palette →</a>
  </div>
</div>"""


def product_card(p: dict, cat_palette: list[str]) -> str:
    series_code = p["sku"].split("-")[0].lower()  # lkp, lkh, lka, lks, lkd
    series_name = SERIES.get(series_code.upper(), {"name": "Leka"})["name"]
    sub_name = CATS[[k for k, v in CATS.items() if any(pp["sku"] == p["sku"] for pp in v.get("products", []))][0]]["subcategories"][p["sub"]]["name"]
    finishes_html = "".join(
        f'<span class="p-finish">{TEXTURES[f]["name"]}</span>'
        for f in p.get("finishes", []) if f in TEXTURES
    )
    colors_html = "".join(
        f'<span class="p-color" style="background:{PALETTE[c]["hex"]} url(/wpc-profile/images/grain/{c.lower()}-{PALETTE[c]["name"].lower().replace(" ", "-")}-woodgrain.jpg) center/cover" title="{PALETTE[c]["name"]} · {c}"></span>'
        for c in cat_palette if c in PALETTE
    )
    length_m = p.get("len", 2900) / 1000
    return f"""<article class="product" data-sub="{p['sub']}">
  <div class="p-img contain">
    <span class="p-badge {series_code}">{series_name}</span>
    <span class="p-sku">{p['sku']}</span>
    <img src="{p['image']}" alt="{p['name']} — {sub_name}" loading="lazy">
  </div>
  <div class="p-body">
    <div>
      <div class="p-cat">{sub_name}</div>
      <div class="p-title">{p['name']}</div>
    </div>
    <div class="p-specs">
      <div class="p-spec"><span class="v">{p['w']:g}</span><span class="l">Width mm</span></div>
      <div class="p-spec"><span class="v">{p['t']:g}</span><span class="l">Thick mm</span></div>
      <div class="p-spec"><span class="v">{length_m:g} m</span><span class="l">Length</span></div>
    </div>
    <div class="p-finishes">{finishes_html}</div>
    <div class="p-colors">
      <span class="p-colors-lbl">Available in {len(cat_palette)} colourways</span>
      {colors_html}
    </div>
  </div>
</article>"""


def page_shell(title: str, description: str, body: str, active_slug: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Leka Studio</title>
<meta name="description" content="{description}">
<meta name="theme-color" content="#182557">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/wpc-profile/css/leka.css">
</head>
<body>
{nav(active_slug)}
{body}
{footer()}
</body>
</html>"""


# ---------- MAIN LANDING PAGE ----------
def build_main() -> None:
    # Category overview cards
    cat_order = ["decking", "cladding", "panels", "fence", "structure", "diy-tiles"]
    thumbs = {
        "decking":   "/wpc-profile/images/products/coex-p1-r5.jpg",
        "cladding":  "/wpc-profile/images/products/coex-p6-r7.jpg",
        "panels":    "/wpc-profile/images/asa/219x25-grille.jpg",
        "fence":     "/wpc-fence/images/141.jpg",
        "structure": "/wpc-profile/images/products/coex-p3-r5.jpg",
        "diy-tiles": "/wpc-profile/images/diy/wpc-coex-tile-tile.jpg",
    }
    cards = []
    for slug in cat_order:
        cat = CATS.get(slug)
        if not cat:
            continue
        n_products = len(cat.get("products", []))
        n_subs = len(cat.get("subcategories", {}))
        url = cat.get("url", f"/wpc-profile/{slug}/")
        ext = cat.get("external_link", False)
        cards.append(f"""
    <a href="{url}" class="cat-card"{' target="_self"' if ext else ''}>
      <div class="thumb">
        <img src="{thumbs[slug]}" alt="{cat['name']}" loading="lazy">
        <span class="tag">{slug.upper()}</span>
      </div>
      <div class="body">
        <h3>{cat['name']}</h3>
        <p>{cat['tagline']}</p>
        <div class="counts"><span><b>{n_products}</b>Products</span><span><b>{n_subs}</b>Sub-categories</span></div>
        <div class="arrow">Explore {cat['name']} →</div>
      </div>
    </a>""")

    body = f"""<section class="hero">
  <div class="container">
    <span class="eyebrow">Outdoor Living Division · 2026 Edition</span>
    <h1>The complete WPC profile library.</h1>
    <p class="lede">Every wood-plastic composite profile Leka sources — across decking, cladding, wall panels, fence, structure and DIY tiles. Five engineered lines (Signature, Shield, Heritage, Structure, DIY), eight colourways, four surface finishes.</p>
    <div class="meta">
      <div><strong>{sum(len(CATS[c].get("products", [])) for c in CATS)}</strong><span>Core SKUs</span></div>
      <div><strong>{len(SERIES)}</strong><span>Engineered Lines</span></div>
      <div><strong>{len(CATS)}</strong><span>Categories</span></div>
      <div><strong>{len(TAX['palette_full'])}</strong><span>Colourways</span></div>
      <div><strong>4</strong><span>Surface Finishes</span></div>
      <div><strong>250+</strong><span>Extended Catalog</span></div>
    </div>
    <div class="series-legend">
      <span class="lkp">Signature — Co-Ex</span>
      <span class="lka">Shield — ASA Triple-Cap</span>
      <span class="lkh">Heritage — Solid WPC</span>
      <span class="lks">Structure — Columns & Beams</span>
      <span class="lkd">DIY — Interlocking Tiles</span>
    </div>
  </div>
</section>

<section>
  <div class="container">
    <span class="eyebrow">Choose a Category</span>
    <h2>Six product categories.</h2>
    <p style="margin-top:12px;color:var(--lk-navy-80);max-width:720px;font-size:17px">
      Every category ships in the same 8 Leka colourways — specify once, match every surface. Click a category to see sub-categories, SKUs, dimensions and swatches.
    </p>
    <div class="cat-grid">
      {''.join(cards)}
    </div>
  </div>
</section>

{cta_section()}"""

    (OUT / "index.html").write_text(
        page_shell(
            "WPC Profiles Catalog",
            "Leka Studio's complete WPC profile library — decking, cladding, wall panels, fence, structure and DIY tiles in 8 colourways and 5 engineered lines.",
            body,
            active_slug=""
        ),
        encoding="utf-8"
    )


# ---------- CATEGORY SUB-PAGE ----------
def build_category(slug: str) -> None:
    cat = CATS[slug]
    if cat.get("external_link"):
        return  # fence uses /wpc-fence/ directly

    # Subcategory tabs
    subs = cat.get("subcategories", {})
    tabs_html = '<button class="sub-tab active" data-filter="all">All</button>'
    tabs_html += "".join(
        f'<button class="sub-tab" data-filter="{sub_slug}">{sub["name"]}</button>'
        for sub_slug, sub in subs.items()
    )

    # Product grid
    cards = [product_card(p, cat.get("palette_codes", [])) for p in cat.get("products", [])]
    grid_html = '<div class="product-grid">' + "".join(cards) + '</div>'

    # Sub-category descriptions
    sub_desc = "".join(
        f'<div style="padding:16px 0;border-top:1px solid var(--lk-navy-06)">'
        f'<h5 style="color:var(--lk-purple);margin-bottom:4px">{sub["name"]}</h5>'
        f'<p style="color:var(--lk-navy-80);font-size:14px">{sub["description"]}</p>'
        f'</div>'
        for sub in subs.values()
    )

    # DIY-tiles uses a different palette model (per-sub)
    if slug == "diy-tiles":
        palette_block = f"""<div class="palette-strip">
  <div class="container" style="flex-direction:column;align-items:flex-start">
    <h4 style="margin-right:0">Palette varies by tile type</h4>
    <p style="color:var(--lk-navy-80);font-size:14px;margin:8px 0 12px">DIY tiles use dedicated colour systems per material — see each sub-category for the specific options.</p>
  </div>
</div>"""
    else:
        palette_block = palette_strip(slug, cat.get("palette_codes", []))

    body = f"""{crumb([('/', 'Home'), ('/wpc-profile/', 'All Profiles'), ('', cat['name'])])}

<section class="hero" style="padding-top:64px;padding-bottom:64px">
  <div class="container">
    <span class="eyebrow">{slug.upper()}</span>
    <h1>{cat['name']}</h1>
    <p class="lede">{cat['tagline']}</p>
    <div class="meta" style="margin-top:32px;max-width:680px">
      <div><strong>{len(cat.get('products', []))}</strong><span>Core SKUs</span></div>
      <div><strong>{len(subs)}</strong><span>Sub-categories</span></div>
      <div><strong>{len(cat.get('palette_codes', []))}</strong><span>Colourways</span></div>
      <div><strong>{len(cat.get('default_textures', []))}</strong><span>Finishes</span></div>
    </div>
  </div>
</section>

<section>
  <div class="container">
    <span class="eyebrow">Filter by Sub-Category</span>
    <div class="sub-tabs">{tabs_html}</div>
    {grid_html}
  </div>
</section>

{palette_block}

<section>
  <div class="container">
    <span class="eyebrow">Sub-Category Guide</span>
    <h3>What each line is engineered for</h3>
    <div style="margin-top:20px;max-width:860px">{sub_desc}</div>
  </div>
</section>

{cta_section(f'Specify {cat["name"].lower()}.', 'Send us your project brief — quantities, dimensions and target delivery. We&rsquo;ll return landed-cost pricing and lead times within one working day.')}

<script>
document.querySelector('.sub-tabs').addEventListener('click', e => {{
  const btn = e.target.closest('.sub-tab');
  if (!btn) return;
  document.querySelectorAll('.sub-tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const f = btn.dataset.filter;
  document.querySelectorAll('.product').forEach(p => {{
    p.classList.toggle('hidden', f !== 'all' && p.dataset.sub !== f);
  }});
}});
</script>"""

    out_dir = OUT / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_dir.joinpath("index.html").write_text(
        page_shell(
            f"{cat['name']} — WPC Profiles",
            f"Leka {cat['name']} — {cat['tagline']}",
            body,
            active_slug=slug
        ),
        encoding="utf-8"
    )


# ---------- COLOURS PAGE ----------
def build_colours() -> None:
    # 8 large swatches (wood-grain texture)
    swatches = "".join(
        f'<div class="swatch-lg">'
        f'<div class="chip" style="background-image:url(/wpc-profile/images/grain/{c["code"].lower()}-{c["name"].lower().replace(" ", "-")}-woodgrain.jpg)"></div>'
        f'<div class="body"><h6>{c["name"]}</h6>'
        f'<div class="code">{c["code"]}</div>'
        f'<div class="hex">{c["hex"]}</div>'
        f'</div></div>'
        for c in TAX["palette_full"]
    )

    # 4 texture reference cards
    textures_html = "".join(
        f'<div class="tex">'
        f'<div class="img">{"<img src=" + t["grid_image"] + ' alt="' + t["name"] + ' texture">' if t.get("grid_image") else "<div style=&quot;width:100%;height:100%;background:linear-gradient(135deg,var(--lk-navy-06),var(--lk-navy-12));display:flex;align-items:center;justify-content:center;color:var(--lk-navy-60);font-weight:700&quot;>Heritage exclusive</div>"}</div>'
        f'<div class="body"><h4>{t["name"]}</h4><p>{t["description"]}</p></div>'
        f'</div>'
        for t in TAX["textures"]
    )
    # Fix the ternary above with a cleaner loop
    textures_html = ""
    for t in TAX["textures"]:
        if t.get("grid_image"):
            img_html = f'<img src="{t["grid_image"]}" alt="{t["name"]} texture card" loading="lazy">'
        else:
            img_html = '<div style="width:100%;height:100%;background:linear-gradient(135deg,var(--lk-navy-06),var(--lk-navy-12));display:flex;align-items:center;justify-content:center;color:var(--lk-navy-60);font-weight:700">Heritage exclusive</div>'
        textures_html += f"""
        <div class="tex">
          <div class="img">{img_html}</div>
          <div class="body"><h4>{t['name']}</h4><p>{t['description']}</p></div>
        </div>"""

    body = f"""{crumb([('/', 'Home'), ('/wpc-profile/', 'All Profiles'), ('', 'Colours')])}

<section class="hero" style="padding-top:64px;padding-bottom:64px">
  <div class="container">
    <span class="eyebrow">Colourways</span>
    <h1>Eight colours. Four textures. Every profile.</h1>
    <p class="lede">The full Leka palette — a curated library of neutrals, warm woods and deep architectural tones. Every colour is available in every texture across every WPC profile category. Custom colours on MOQ request.</p>
  </div>
</section>

<section>
  <div class="container">
    <span class="eyebrow">Colour Library</span>
    <h2>The eight Leka colourways.</h2>
    <p style="margin-top:12px;color:var(--lk-navy-80);max-width:720px;font-size:17px">Each swatch shown in 2nd-Gen wood-grain — Leka's signature finish. Click a colour to see it in knife-cut and stipple textures below.</p>
    <div class="swatch-grid">{swatches}</div>
  </div>
</section>

<section>
  <div class="container">
    <span class="eyebrow">Surface Textures</span>
    <h2>Four engineered textures.</h2>
    <p style="margin-top:12px;color:var(--lk-navy-80);max-width:720px;font-size:17px">Each texture runs across all 8 colours. Spec by function: knife-cut for feature walls, stipple for wet-area decks, wood-grain for mainline cladding, 3D emboss for heritage projects.</p>
    <div class="tex-grid">{textures_html}</div>
  </div>
</section>

{cta_section('Specify your palette.', 'Not sure which colour or texture to choose? Send the project type and we&rsquo;ll send A5 physical samples to your address.')}
"""

    out_dir = OUT / "colours"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_dir.joinpath("index.html").write_text(
        page_shell("Colours & Textures", "Leka Studio — 8 colourways × 4 textures. Every WPC profile, every category.", body, "colours"),
        encoding="utf-8"
    )


if __name__ == "__main__":
    build_main()
    for slug in CATS:
        build_category(slug)
    build_colours()
    print("Generated pages:")
    for p in sorted(OUT.rglob("index.html")):
        print(f"  {p.relative_to(OUT)}")
