"""Crop vendor catalog PDF pages into clean, brand-free Leka assets.

Extracts:
  - Full colour-grid cards (4 textures x 8 colours) from jackson_ce_p10/11/12
  - Wall-panel colour card (9 panels) from jackson_ce_p13
  - Individual Co-Ex product photos from jackson_ce p1-p9 (leftmost cell of each row)
  - ASA Shield Series product photos from aolo_asa p2-p7 (top + bottom product)
  - DIY tile hero photos from diy p2-p6
  - First-generation Heritage strip from firstgen p3-p10 (leftmost column)

Output: website/salesheet/wpc-profile/images/{grain,products,asa,diy,heritage}/
"""
from __future__ import annotations
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / ".claude" / "pdf-pages"
OUT = ROOT / "website" / "salesheet" / "wpc-profile" / "images"
for sub in ("grain", "products", "asa", "diy", "heritage"):
    (OUT / sub).mkdir(parents=True, exist_ok=True)


# ----- 1. COLOUR GRID CARDS ---------------------------------------------
# jackson_ce_p10/p11/p12: 993 x 1404, 4 col x 2 row grid of wood-grain swatches
# Crop the whole grid minus the Chinese header at top.
# Header is in the top ~110px. Grid runs y~120 to y~1380.
COLOUR_CARDS = {
    "p10": ("knifecut",  "Knife-Cut Texture"),
    "p11": ("stipple",   "Stipple Texture"),
    "p12": ("woodgrain", "2nd-Gen Wood-Grain (Main)"),
    "p13": ("wallpanel", "Wall-Panel Profile Colour Card"),
}
for pnum, (slug, _label) in COLOUR_CARDS.items():
    src = PDF / f"jackson_ce_{pnum}.png"
    if not src.exists():
        continue
    img = Image.open(src)
    w, h = img.size
    # Crop below the Chinese header
    grid = img.crop((15, 125, w - 15, h - 20))
    grid.save(OUT / "grain" / f"grid-{slug}.jpg", quality=88, optimize=True)


# Individual swatch cells — 4 columns x 2 rows from p12 (main wood-grain)
# Grid occupies roughly x=40..955, y=130..1380  (after trimming header)
# Each row ~625px tall (incl. Chinese label below swatch)
# Swatch area within each cell: ~500px tall, excluding the label
# Grid order: 枫木 柚木 红木 紫檀 / 沙白 古木 浅灰 炭黑  →  LK-08 LK-05 LK-06 LK-07 / LK-04 LK-02 LK-03 LK-01
GRID_SRC = {
    "woodgrain": PDF / "jackson_ce_p12.png",
    "knifecut":  PDF / "jackson_ce_p10.png",
    "stipple":   PDF / "jackson_ce_p11.png",
}
GRID_CODES = [
    ("lk-08", "maple"),
    ("lk-05", "teak"),
    ("lk-06", "mahogany"),
    ("lk-07", "rosewood"),
    ("lk-04", "sand-white"),
    ("lk-02", "ancient-wood"),
    ("lk-03", "light-grey"),
    ("lk-01", "charcoal"),
]
# Cell geometry (approximate — calibrated for jackson_ce_p12 993x1404)
# Tight crop excluding Chinese labels at bottom of each cell
CELL_W = 200
CELL_H = 370
COL_X = [60, 300, 540, 780]
ROW_Y = [165, 790]

for texture, src in GRID_SRC.items():
    if not src.exists():
        continue
    img = Image.open(src)
    idx = 0
    for r, y in enumerate(ROW_Y):
        for c, x in enumerate(COL_X):
            if idx >= len(GRID_CODES):
                break
            code, color_name = GRID_CODES[idx]
            crop = img.crop((x, y, x + CELL_W, y + CELL_H))
            crop.save(OUT / "grain" / f"{code}-{color_name}-{texture}.jpg",
                      quality=85, optimize=True)
            idx += 1


# ----- 2. CO-EX PRODUCT PHOTOS ------------------------------------------
# jackson_ce_p1..p9: 993 x 1404, product table.
# Leftmost product photo cell: x~50..180, rows start ~y=220, row height ~175px
# Product photos per page: 6 (most pages)
# We grab all photo cells we can detect; HTML references by SKU separately.
for pnum in range(1, 10):
    src = PDF / f"jackson_ce_p{pnum}.png"
    if not src.exists():
        continue
    img = Image.open(src)
    W, H = img.size
    # p1 has a tall header (AOLO logo + title bar) — first product row starts ~y=340
    # Subsequent pages start flush with an item row at y~15
    y0 = 340 if pnum == 1 else 15
    row_h = 155
    # Product photo cell: x~55..185, row height ~155, vertical padding inside cell
    for i in range(10):
        y1 = y0 + i * row_h + 8
        y2 = y0 + (i + 1) * row_h - 8
        if y2 > H - 20:
            break
        crop = img.crop((60, y1, 185, y2))
        # Reject rows that are mostly white (no product photo)
        gray = crop.convert("L")
        extrema = gray.getextrema()
        if extrema[1] - extrema[0] < 50:
            continue
        # Reject crops that are solid coloured (likely category-title bars)
        # by checking std deviation on a downsized version
        small = crop.resize((32, 32))
        pixels = list(small.convert("L").getdata())
        mean = sum(pixels) / len(pixels)
        var = sum((p - mean) ** 2 for p in pixels) / len(pixels)
        if var < 300:
            continue
        crop.save(OUT / "products" / f"coex-p{pnum}-r{i+1}.jpg",
                  quality=82, optimize=True)


# ----- 3. ASA SHIELD PRODUCT PHOTOS -------------------------------------
# aolo_asa p2..p7: 969 x 785, two products per page
# Product photo in left half, top and bottom.
# Top product: ~x=50..350, y=30..330
# Bottom product: ~x=50..350, y=410..720
ASA_PRODUCTS = [
    ("p2", "top",    "170x14-grille"),
    ("p2", "bottom", "189x20-grille"),
    ("p3", "top",    "219x25-grille"),
    ("p3", "bottom", "224x21-grille"),
    ("p4", "top",    "207x16-grille"),
    ("p4", "bottom", "122x10-panel"),
    ("p5", "top",    "112x16-smallpanel"),
    ("p5", "bottom", "121x12-smallgrille"),
    ("p6", "top",    "140x24-deckway"),
    ("p6", "bottom", "140x32-fence"),
    ("p7", "top",    "156x17-basketball"),
    ("p7", "bottom", "45x45-edging"),
]
for pnum, pos, slug in ASA_PRODUCTS:
    src = PDF / f"aolo_asa_{pnum}.png"
    if not src.exists():
        continue
    img = Image.open(src)
    if pos == "top":
        crop = img.crop((40, 30, 380, 360))
    else:
        crop = img.crop((40, 410, 380, 740))
    crop.save(OUT / "asa" / f"{slug}.jpg", quality=88, optimize=True)


# ----- 4. DIY TILE HERO PHOTOS ------------------------------------------
# diy_p2..p8: 1754 x 1241, spread layout (left table, right hero)
# Hero photo at right side: roughly x=900..1720, y=30..1200
DIY_PAGES = {
    "p2": "overview",
    "p3": "wpc-coex-tile",
    "p4": "pp-plastic-tile",
    "p5": "grass-stone-tile",
    "p6": "wood-finish-tile",
    "p7": "installation",
    "p8": "gallery",
}
for pnum, slug in DIY_PAGES.items():
    src = PDF / f"diy_{pnum}.png"
    if not src.exists():
        continue
    img = Image.open(src)
    # Right-side photo block
    crop = img.crop((880, 30, 1720, 1200))
    crop.save(OUT / "diy" / f"{slug}.jpg", quality=85, optimize=True)
    # Also extract the small product tile photo from left column (if table page)
    # Small tile preview: ~x=70..310, y=100..310
    if pnum in ("p3", "p4", "p5"):
        tile = img.crop((60, 85, 320, 320))
        tile.save(OUT / "diy" / f"{slug}-tile.jpg", quality=88, optimize=True)


# ----- 5. HERITAGE STRIP PHOTOS -----------------------------------------
# firstgen p3..p15: 1241 x 1755, product table with photos in leftmost column
# Row height ~155px, photo cell: x~30..180, rows start y~10
for pnum in range(3, 16):
    src = PDF / f"firstgen_p{pnum}.png"
    if not src.exists():
        continue
    img = Image.open(src)
    y0 = 10
    row_h = 155
    for i in range(10):
        y1 = y0 + i * row_h
        y2 = y1 + row_h - 10
        if y2 > img.size[1] - 10:
            break
        crop = img.crop((30, y1, 195, y2))
        gray = crop.convert("L")
        extrema = gray.getextrema()
        if extrema[1] - extrema[0] < 30:
            continue
        crop.save(OUT / "heritage" / f"hg-p{pnum}-r{i+1}.jpg",
                  quality=82, optimize=True)


# Summary
for sub in ("grain", "products", "asa", "diy", "heritage"):
    n = len(list((OUT / sub).glob("*")))
    print(f"{sub:10s}: {n} images")
print(f"\nOutput: {OUT}")
