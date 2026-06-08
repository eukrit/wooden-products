"""
Build mapped vendors / products / product_images JSON for the WeChat wooden-flooring
handoff (data/incoming/wechat_wooden_flooring_export.json).

SCOPE: genuine wood flooring only. After parsing the source PDFs we determined:
  - Bimei  -> Italian brand "Foglie d'Oro": 2-layer engineered parquet  (INCLUDE, new vendor `bimei`)
  - "ENGINEERED CATALOG.pdf" -> brand "Elegant Living": engineered oak planks
        (INCLUDE, vendor `elegant-living` ALREADY EXISTS -> merge; Oak Maroon already imported -> skip)
  - Visconti -> Italian brand "Giorio Casa": three-layer engineered wood (INCLUDE, new vendor `visconti`)
  - Qihao Home Kihome -> Oasis Forestry MDF/HDF = LAMINATE (EXCLUDE per user, 2026-06-08)
  - needs_review (Hongyu) -> porcelain/ceramic wood-look tiles (EXCLUDE)

Outputs to data/incoming/parsed/: vendors.json, products.json, product_images.json
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
EXPORT = os.path.join(ROOT, "data", "incoming", "wechat_wooden_flooring_export.json")
OUTDIR = os.path.join(ROOT, "data", "incoming", "parsed")
os.makedirs(OUTDIR, exist_ok=True)

SOURCE = "wechat-automation:wechat-documents"

# GCS destinations after we copy the source PDFs into the asset bucket
ASSET = "gs://products-wood-assets"

data = json.load(open(EXPORT, encoding="utf-8"))
products_in = data["products"]


def slug(s):
    s = s.lower()
    s = s.replace("’", "").replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


# ---- species / finish parsing for Bimei (Foglie d'Oro) ----
SPECIES = [
    ("American Walnut", "American Walnut"),
    ("European Walnut", "European Walnut"),
    ("Maple", "Maple"),
    ("Cherry", "Cherry"),
    ("Oak", "Oak"),
]
FINISHES = ["brushed", "bleached", "varnished", "oiled", "stained", "smoked",
            "aged", "sanded", "hand patina", "inlay", "naturalized"]


def parse_english(material):
    """Return the English descriptor (inside parentheses) if present."""
    m = re.search(r"\(([^)]*)\)", material or "")
    return m.group(1).strip() if m else (material or "")


def derive_species(material):
    eng = parse_english(material)
    found = []
    for needle, label in SPECIES:
        if needle.lower() in eng.lower() and label not in found:
            found.append(label)
    return ", ".join(found) if found else (eng.split(",")[0].strip() if eng else "Wood")


def derive_finish(material):
    eng = parse_english(material).lower()
    found = [f for f in FINISHES if f in eng]
    return ", ".join(found)


vendors = []
products = []
images = []

# ----------------------------------------------------------------------------
# VENDORS (new). elegant-living already exists in Firestore -> do NOT recreate.
# ----------------------------------------------------------------------------
vendors.append({
    "vendor_id": "bimei",
    "name": "Bimei (必美地板)",
    "brand": "Foglie d'Oro",
    "type": "importer",
    "country": "IT",
    "contact": {},
    "products_supplied": ["engineered_flooring"],
    "notes": ("Chinese importer/distributor of the Italian parquet brand Foglie d'Oro. "
              "2-layer engineered panels: 4mm single-plank solid-wood noble top on birch "
              "multiply (12mm for 16mm panel / 16mm for 20mm panel), tongue&tongue or "
              "groove&groove with separate wood strip joint, micro-bevel 4 sides, glued "
              "laying, underfloor-heating compatible. Species: European/American Walnut, "
              "Oak, with Maple & Cherry inlays. Made in Italy; Dfl-S1, E1/HCHO. Boards up "
              "to 4.5m long x 0.5m wide. Source catalog: "
              "必美地板意大利菲列德罗画册（拼花）.pdf (Foglie d'Oro Design & Heritage Panels)."),
    "source": SOURCE,
})

vendors.append({
    "vendor_id": "visconti",
    "name": "Giorio Casa (意大利卓越卡萨)",
    "brand": "Giorio Casa",
    "type": "importer",
    "country": "IT",
    "contact": {},
    "products_supplied": ["engineered_flooring"],
    "notes": ("Italian brand Giorio Casa (GIORIO visconti). Company profile lists a "
              "three-layer solid/engineered wood flooring line among several product lines. "
              "Source: 2026-02-11 卓越卡萨公司简介 GIORIO visconti Profile.pdf."),
    "source": SOURCE,
})

# An update patch for the existing elegant-living vendor (merge traceability only).
elegant_living_update = {
    "vendor_id": "elegant-living",
    "_op": "merge",  # handled specially by uploader: do not overwrite existing fields wholesale
    "notes_append": (" Also seen via WeChat (wechat-automation): City Vogue Country Plank "
                     "engineered Oak (12x190x2100mm). Source file: 2026-01-07 ENGINEERED "
                     "CATALOG.pdf (cover brand 'Elegant Living', sales@elegantliving.co)."),
}

# ----------------------------------------------------------------------------
# PRODUCTS
# ----------------------------------------------------------------------------

# --- Elegant Living (6 new; Oak Maroon already exists as el-oak-maroon -> skip) ---
EL_SKIP = {"Oak Maroon"}
for p in products_in:
    if p["source_filename"] != "2026-01-07 ENGINEERED CATALOG.pdf":
        continue
    name = p["product_name"]
    if name in EL_SKIP:
        continue
    pid = "el-" + slug(name)
    products.append({
        "product_id": pid,
        "vendor_id": "elegant-living",
        "name": f"Elegant Living {name} (City Vogue)",
        "brand": "Elegant Living",
        "category": "engineered_flooring",
        "subcategory": "engineered oak plank",
        "material": "Oak",
        "specifications": {
            "dimensions": "12 x 190 x 2100 mm",
            "thickness": 12,
            "width": 190,
            "length": 2100,
            "grade": "Country Plank",
            "finish": "Brushed",
            "pattern": "plank",
        },
        "unit": "sqm",
        "origin_country": "China",
        "datasheet_url": f"{ASSET}/elegant-living/2026-01-07 ENGINEERED CATALOG.pdf",
        "notes": (f"City Vogue Collection Country Plank, brushed engineered oak. "
                  f"[wechat product_id={p['product_id']}; "
                  f"source_file_id={p['source_file_id']}; file={p['source_filename']}]"),
        "source": SOURCE,
    })

# --- Bimei / Foglie d'Oro (23) ---
for p in products_in:
    if p["vendor_id"] != "Bimei":
        continue
    name = p["product_name"]
    pid = "bimei-" + slug(name)
    dim = (p.get("dimensions") or "").strip()
    # export dims are the panel module W x L in mm (e.g. 590x590, 1000x1000)
    dim_full = f"{dim} mm panel module, 16/20mm thick (4mm solid-wood top)" if dim else \
               "16/20mm 2-layer engineered (4mm solid-wood top)"
    sub = p.get("subcategory") or "Wood Flooring"
    pattern = "parquet"
    if "Versailles" in name:
        pattern = "Versailles parquet"
    elif "Chevron" in name or "spina" in (p.get("material") or "").lower():
        pattern = "herringbone/chevron"
    elif "Parquet" in sub:
        pattern = "parquet"
    products.append({
        "product_id": pid,
        "vendor_id": "bimei",
        "name": name,
        "brand": "Foglie d'Oro",
        "category": "engineered_flooring",
        "subcategory": "engineered parquet module",
        "material": p.get("material") or "Wood",
        "specifications": {
            "dimensions": dim_full,
            "grade": "",
            "finish": derive_finish(p.get("material")) or "",
            "pattern": pattern,
            "construction": "2-layer engineered: 4mm solid-wood noble top + birch multiply",
        },
        "unit": "sqm",
        "origin_country": "Italy",
        "certifications": ["E1", "Dfl-S1 (fire reaction)"],
        "datasheet_url": f"{ASSET}/bimei/必美地板意大利菲列德罗画册（拼花）.pdf",
        "notes": (f"Foglie d'Oro {sub}. Species: {derive_species(p.get('material'))}. "
                  f"Made in Italy, glued laying, underfloor-heating compatible. "
                  f"[wechat product_id={p['product_id']}; "
                  f"source_file_id={p['source_file_id']}; file={p['source_filename']}]"),
        "source": SOURCE,
    })

# --- Visconti / Giorio Casa (1) ---
for p in products_in:
    if p["vendor_id"] != "Visconti":
        continue
    products.append({
        "product_id": "visconti-three-layer-solid-wood",
        "vendor_id": "visconti",
        "name": "Giorio Casa Three-layer Solid Wood Flooring (三层实木地板)",
        "name_th": "",
        "brand": "Giorio Casa",
        "category": "engineered_flooring",
        "subcategory": "three-layer engineered wood",
        "material": "Wood (three-layer)",
        "specifications": {
            "dimensions": "",
            "color": "Various wood tones",
            "construction": "Three-layer solid/engineered wood",
            "pattern": "plank",
        },
        "unit": "sqm",
        "origin_country": "Italy",
        "datasheet_url": f"{ASSET}/visconti/2026-02-11 卓越卡萨公司简介 GIORIO visconti Profile.pdf",
        "notes": (f"High-quality three-layer solid/engineered wood flooring. "
                  f"[wechat product_id={p['product_id']}; "
                  f"source_file_id={p['source_file_id']}; file={p['source_filename']}]"),
        "source": SOURCE,
    })

# ----------------------------------------------------------------------------
# PRODUCT IMAGES (catalog PDFs copied into the asset bucket)
# ----------------------------------------------------------------------------
IMG = [
    ("bimei", "必美地板意大利菲列德罗画册（拼花）.pdf", 51125588, "catalog",
     "Foglie d'Oro (Bimei) Italian engineered parquet catalog - Design & Heritage Panels."),
    ("elegant-living", "2026-01-07 ENGINEERED CATALOG.pdf", 18278807, "catalog",
     "Elegant Living engineered hardwood flooring catalog (City Vogue etc.)."),
    ("visconti", "2026-02-11 卓越卡萨公司简介 GIORIO visconti Profile.pdf", 50293603, "catalog",
     "Giorio Casa (GIORIO visconti) company profile incl. three-layer wood flooring."),
]
for vendor, fname, size, typ, desc in IMG:
    images.append({
        "vendor_id": vendor,
        "file_name": fname,
        "storage_path": f"{ASSET}/{vendor}/{fname}",
        "content_type": "application/pdf",
        "file_size_bytes": size,
        "description": desc,
        "type": typ,
        "source": SOURCE,
    })

json.dump(vendors, open(os.path.join(OUTDIR, "vendors.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
json.dump([elegant_living_update], open(os.path.join(OUTDIR, "vendor_updates.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
json.dump(products, open(os.path.join(OUTDIR, "products.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
json.dump(images, open(os.path.join(OUTDIR, "product_images.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

print(f"vendors (new):       {len(vendors)}  -> {[v['vendor_id'] for v in vendors]}")
print(f"vendor updates:      1  -> elegant-living (merge notes)")
print(f"products (new):      {len(products)}")
by_v = {}
for p in products:
    by_v[p['vendor_id']] = by_v.get(p['vendor_id'], 0) + 1
print(f"  by vendor:         {by_v}")
print(f"product_images:      {len(images)}")
