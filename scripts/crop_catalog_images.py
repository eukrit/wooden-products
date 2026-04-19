"""Crop vendor catalog PDF pages into clean, brand-free Leka assets.

v2: re-extracted at 220 DPI + auto-tight-bbox centering + tighter source coords
to eliminate Chinese titles, row numbers, and adjacent-cell bleed.

Output: website/salesheet/wpc-profile/images/{grain,products,asa,diy,heritage}/
"""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / ".claude" / "pdf-pages"
OUT = ROOT / "website" / "salesheet" / "wpc-profile" / "images"
for sub in ("grain", "products", "asa", "diy", "heritage"):
    (OUT / sub).mkdir(parents=True, exist_ok=True)


def auto_tight(img: Image.Image, pad: int = 20, threshold: int = 235) -> Image.Image:
    """Detect non-white content and crop tight to its bbox, with padding."""
    gray = img.convert("L")
    # Non-white pixels have value < threshold
    mask = gray.point(lambda p: 255 if p < threshold else 0)
    bbox = mask.getbbox()
    if not bbox:
        return img
    x1, y1, x2, y2 = bbox
    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(img.width, x2 + pad)
    y2 = min(img.height, y2 + pad)
    return img.crop((x1, y1, x2, y2))


def has_content(img: Image.Image, min_var: int = 300) -> bool:
    """Check if crop contains meaningful image content (not blank or uniform)."""
    gray = img.resize((32, 32)).convert("L")
    pixels = list(gray.getdata())
    mean = sum(pixels) / len(pixels)
    var = sum((p - mean) ** 2 for p in pixels) / len(pixels)
    return var >= min_var


# ===================================================================
# 1. COLOUR GRID CARDS (jackson_ce_p10/p11/p12/p13)
# ===================================================================
# At 220 DPI each page is 1820x2573.
# Grid: 4 cols x 2 rows of wood-grain swatches.
# Header strip at top (~220px); then 2 rows of swatches.

COLOUR_CARDS = {
    "p10": ("knifecut",   "Knife-Cut Texture"),
    "p11": ("stipple",    "Stipple Texture"),
    "p12": ("woodgrain",  "2nd-Gen Wood-Grain (Main)"),
    "p13": ("wallpanel",  "Wall-Panel Profile Card"),
}
for pnum, (slug, _) in COLOUR_CARDS.items():
    src = PDF / f"jackson_ce_{pnum}.png"
    if not src.exists():
        continue
    img = Image.open(src)
    # Crop below header (header in top ~230px), trim small bottom margin
    grid = img.crop((20, 230, img.width - 20, img.height - 30))
    grid.save(OUT / "grain" / f"grid-{slug}.jpg", quality=90, optimize=True)

# Individual swatch cells from jackson_ce_p12 (main wood-grain)
GRID_CODES = [
    ("lk-08", "maple"),        # 枫木
    ("lk-05", "teak"),         # 柚木
    ("lk-06", "mahogany"),     # 红木
    ("lk-07", "rosewood"),     # 紫檀
    ("lk-04", "sand-white"),   # 沙白
    ("lk-02", "ancient-wood"), # 古木
    ("lk-03", "light-grey"),   # 浅灰
    ("lk-01", "charcoal"),     # 炭黑
]
# 220 DPI: 4-col × 2-row grid occupies roughly x=40..1780, y=230..2540
# Each cell ≈ 440 wide, 1150 tall (incl. Chinese label at bottom ~100px)
# Tight swatch crop (excl. label): 380w × 990h per cell
CELL_W, CELL_H = 380, 990
COL_X = [80, 520, 960, 1400]
ROW_Y = [260, 1420]

GRID_SRC = {
    "woodgrain": PDF / "jackson_ce_p12.png",
    "knifecut":  PDF / "jackson_ce_p10.png",
    "stipple":   PDF / "jackson_ce_p11.png",
}
for texture, src in GRID_SRC.items():
    if not src.exists():
        continue
    img = Image.open(src)
    idx = 0
    for y in ROW_Y:
        for x in COL_X:
            if idx >= len(GRID_CODES):
                break
            code, color_name = GRID_CODES[idx]
            crop = img.crop((x, y, x + CELL_W, y + CELL_H))
            crop.save(OUT / "grain" / f"{code}-{color_name}-{texture}.jpg",
                      quality=88, optimize=True)
            idx += 1


# ===================================================================
# 2. CO-EX PRODUCT PHOTOS (jackson_ce_p1..p9)
# ===================================================================
# At 220 DPI: 1820x2573. Table structure (measured against _debug_p1_topleft.png):
#   Col 1 (row#):   x=  0 .. ~105  (EXCLUDE)
#   Col 2 (photo):  x=105 .. ~355  (TARGET)
#   Col 3 (code):   x=365 .. ~560  (EXCLUDE — vendor code)
# Row height: ~270px. p1 has a tall header (title+logo+header row + green banner)
# so first product row starts at y~770; pages p2-p9 start at y~30.
for pnum in range(1, 10):
    src = PDF / f"jackson_ce_p{pnum}.png"
    if not src.exists():
        continue
    img = Image.open(src)
    H = img.size[1]
    y0 = 770 if pnum == 1 else 25
    row_h = 270
    for i in range(10):
        # Very conservative y-pads: 30 top / 30 bottom — fully inside the 270px cell
        # so bordering rows/gridlines cannot leak in.
        y_top = y0 + i * row_h + 28
        y_bot = y0 + (i + 1) * row_h - 28
        if y_bot > H - 30:
            break
        # x window strictly within the photo column
        rough = img.crop((115, y_top, 350, y_bot))
        if not has_content(rough, min_var=400):
            continue
        # Trim only internal whitespace — bbox within these hard bounds, small pad
        tight = auto_tight(rough, pad=6, threshold=238)
        if tight.width < 80 or tight.height < 80:
            continue
        tight.save(OUT / "products" / f"coex-p{pnum}-r{i+1}.jpg",
                   quality=90, optimize=True)


# ===================================================================
# 3. ASA SHIELD PRODUCT PHOTOS (aolo_asa_p2..p7)
# ===================================================================
# At 220 DPI: 1777x1439. Two products per page (top + bottom half).
# Each half: title text at top (~120px), then product photo + cross-section drawing.
# Product PHOTO occupies left portion of each half (photos of physical samples).
# Cross-section drawing is on right (which we want OUT — that's a technical diagram).
# So: crop left ~45% of each half, and skip the top ~130px title.

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
    W, H = img.size
    # Main 3D hero photo only. ASA page layout per half:
    #   Title "XXX*YY格栅" at top  (y ~ 20..170 within each half)
    #   Hero photo on LEFT  (x ~ 60..860, y ~ 180..500)
    #   Cross-section drawing + spec text on RIGHT (x > 900) — EXCLUDE
    #   On p3 there are small auxiliary photos below the hero (y > 500) — EXCLUDE
    half = H // 2
    if pos == "top":
        rough = img.crop((60, 185, int(W * 0.50), 490))
    else:
        rough = img.crop((60, half + 185, int(W * 0.50), half + 490))
    # Auto-tight INWARDS only: no top-padding (prevents re-expansion into title)
    gray = rough.convert("L")
    mask = gray.point(lambda p: 255 if p < 235 else 0)
    bbox = mask.getbbox()
    if bbox:
        x1, y1, x2, y2 = bbox
        pad = 14
        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - min(pad, 4))  # minimal upward pad
        x2 = min(rough.width, x2 + pad)
        y2 = min(rough.height, y2 + pad)
        rough = rough.crop((x1, y1, x2, y2))
    rough.save(OUT / "asa" / f"{slug}.jpg", quality=90, optimize=True)


# ===================================================================
# 4. DIY HERO PHOTOS (diy_p2..p8)
# ===================================================================
# At 220 DPI: 2573x1820 (landscape). Right side has large hero photo(s).
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
    # Right-side hero block ~x=1290..2530, y=40..1760
    rough = img.crop((1290, 40, 2530, 1760))
    tight = auto_tight(rough, pad=20)
    tight.save(OUT / "diy" / f"{slug}.jpg", quality=88, optimize=True)
    # Tile sample swatch for category pages (top-left quadrant of table pages)
    if pnum in ("p3", "p4", "p5"):
        sample = img.crop((90, 120, 470, 470))
        sample_tight = auto_tight(sample, pad=12)
        sample_tight.save(OUT / "diy" / f"{slug}-tile.jpg", quality=90, optimize=True)


# ===================================================================
# 5. HERITAGE STRIP PHOTOS (firstgen_p3..p15)
# ===================================================================
# At 220 DPI: 1820x2573. Measured via _debug_fg3_topleft.png:
#   Col 1 (row#):   x=  0 .. ~140  (EXCLUDE — row numbers like "15", "16")
#   Col 2 (photo):  x=140 .. ~405  (TARGET)
#   Col 3 (code):   x=410 .. ~610  (EXCLUDE — vendor codes AL-K140-40A etc.)
# Row height ~310px at 220 DPI. First row at y~15.
for pnum in range(3, 16):
    src = PDF / f"firstgen_p{pnum}.png"
    if not src.exists():
        continue
    img = Image.open(src)
    H = img.size[1]
    y0 = 15
    row_h = 310
    for i in range(10):
        # Conservative 35px vertical pad — keeps crop inside the 310px cell.
        y_top = y0 + i * row_h + 35
        y_bot = y0 + (i + 1) * row_h - 35
        if y_bot > H - 20:
            break
        rough = img.crop((150, y_top, 400, y_bot))
        if not has_content(rough, min_var=400):
            continue
        tight = auto_tight(rough, pad=6, threshold=238)
        if tight.width < 80 or tight.height < 80:
            continue
        tight.save(OUT / "heritage" / f"hg-p{pnum}-r{i+1}.jpg",
                   quality=88, optimize=True)


# ===================================================================
# SUMMARY
# ===================================================================
for sub in ("grain", "products", "asa", "diy", "heritage"):
    n = len(list((OUT / sub).glob("*")))
    print(f"{sub:10s}: {n} images")
print(f"\nOutput: {OUT}")
