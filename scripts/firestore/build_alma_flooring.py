"""Map the parsed Alma catalog into Firestore-ready JSON for products-wood.

Input:
  data/parsed/alma/alma_catalog.json   (from scripts/scrapers/alma_extract.py)

Outputs (data/incoming/parsed/, alma-prefixed so WeChat files are untouched):
  alma_vendors.json          — single `alma-giorio` manufacturer vendor
  alma_products.json         — model-level parents + colour/finish child SKUs
  alma_product_images.json   — one record per PDF + per scraped image (gs:// paths)

Granularity (per user decision): BOTH model-level products AND colour/finish SKUs.
  - Parent model product:  alma-<collection>-<model-slug>     (e.g. alma-doghe-alabama)
  - Child colour SKU:      alma-<species-slug>-<code>          (e.g. alma-european-oak-t02)

Run:
  python scripts/firestore/build_alma_flooring.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "data" / "parsed" / "alma" / "alma_catalog.json"
OUT = ROOT / "data" / "incoming" / "parsed"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE = "scrape:almafloor.it"
ASSET = "gs://products-wood-assets"
DOCS_PREFIX = f"{ASSET}/alma/docs"
IMG_PREFIX = f"{ASSET}/alma/images"
VENDOR_ID = "alma-giorio"


def slug(s: str) -> str:
    s = s.lower().replace("°", "").replace("’", "").replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


catalog = json.loads(CATALOG.read_text(encoding="utf-8"))

# ---------------------------------------------------------------------------
# VENDOR
# ---------------------------------------------------------------------------
vendors = [{
    "vendor_id": VENDOR_ID,
    "name": "GIORIO S.r.l.",
    "brand": "Alma",
    "type": "manufacturer",
    "country": "Italy",
    "contact": {
        "website": "https://www.almafloor.it",
        "address": "Italy (finishing & QC); production in Hungary",
    },
    "products_supplied": ["engineered_flooring", "decking", "moulding"],
    "certifications": ["FSC-C108523", "PEFC/18-31-374"],
    "notes": (
        "Italian engineered-parquet manufacturer (brand 'Alma by Giorio'), founded "
        "1969 by Pierino Giorio. Premium multi-layer oak/walnut parquet — plank, "
        "herringbone, chevron, geometric, design (Versailles/Chantilly) and inlay "
        "formats; Asian Teak & Austrian Larch Bio decking. Noble layers 3-6 mm, "
        "structures 10/3..17/6, boards up to 2200 mm. FSC C108523, PEFC/18-31-374, "
        "EPD + VOC tested, underfloor-heating compatible. Logs/production in Hungary, "
        "finishing & QC in Italy. NOTE: distinct from reseller 'visconti' (Giorio Casa, "
        "WeChat #25) which distributes Giorio in China. Full catalogue scraped from "
        "almafloor.it (2024 catalogue + per-model technical sheets in product_images)."
    ),
    "source": SOURCE,
}]

# ---------------------------------------------------------------------------
# DOCUMENT lookup: model token -> datasheet pdf file
# ---------------------------------------------------------------------------
datasheets = [d for d in catalog["documents"] if d["type"] == "datasheet"]


def datasheet_for(collection_slug: str, model_name: str) -> str | None:
    """Return gs:// path of the technical sheet covering this model, if any."""
    name_l = model_name.lower()
    # collection-level sheets (herringbone / chevron / geometric / design)
    coll_map = {
        "spina-italiana-90": "spine+90",
        "spina-ungherese-45": "spine+45",
        "geometrici": "geometrici",
        "design": "design",
    }
    if collection_slug in coll_map:
        tok = coll_map[collection_slug]
        for d in datasheets:
            if tok in d["file"].lower():
                return f"{DOCS_PREFIX}/{d['file']}"
    # plank: match by model token contained in the model name
    for d in datasheets:
        mt = (d.get("model_token") or "").lower()
        if mt and mt in name_l:
            return f"{DOCS_PREFIX}/{d['file']}"
    return None


CATALOGUE_PDF = next(
    (f"{DOCS_PREFIX}/{d['file']}" for d in catalog["documents"] if d["type"] == "catalog"),
    None)

# ---------------------------------------------------------------------------
# PRODUCTS — model-level parents
# ---------------------------------------------------------------------------
products = []
ESSENCE_SPECIES = [e["species"] for e in catalog["essences"]]

MAINTENANCE = {"alma clean", "alma lux", "alma soap", "alma oil", "oil care plus"}

for c in catalog["collections"]:
    for m in c["models"]:
        name = m["name"]
        pid = f"alma-{c['slug']}-{slug(name)}"
        specs_in = m.get("specs", {})
        is_maint = name.lower() in MAINTENANCE
        is_decking = c["slug"] == "esterno"
        is_accessory = c["slug"] == "accessori"

        if is_maint:
            material = ""
        elif is_decking:
            material = "Asian Teak"
        else:
            material = "European Oak"

        specifications = {
            "pattern": c["pattern"],
        }
        if specs_in:
            specifications.update({
                "dimensions": specs_in.get("dimension", ""),
                "structure": specs_in.get("structure", ""),
                "thickness": specs_in.get("thickness"),
                "width": specs_in.get("width"),
                "length": specs_in.get("length"),
                "noble_layer_mm": specs_in.get("noble_layer_mm"),
            })
        if is_decking:
            specifications["construction"] = "Outdoor teak decking board (Asian Teak), brushed natural"
            specifications["finish"] = "Brushed - Natural"
            specifications["use"] = "exterior / decking"
        elif not is_maint and not is_accessory:
            specifications["construction"] = (
                f"Multi-layer engineered parquet, {specs_in.get('noble_layer_mm') or 'n/a'} mm "
                "noble hardwood top, tongue & groove, micro-bevel, underfloor-heating compatible")
            specifications["finish"] = "Brushed; oiled or lacquered (UV)"
            specifications["species_available"] = ESSENCE_SPECIES

        image_urls = [f"{IMG_PREFIX}/{fn}" for fn in m.get("image_files", [])]
        ds = datasheet_for(c["slug"], name) or (CATALOGUE_PDF if not is_maint else None)

        category = c["category"]
        if is_maint:
            category = "moulding"  # accessory/consumable bucket

        notes = m.get("description", "")
        tag = "maintenance product" if is_maint else (
            "accessory" if is_accessory else f"model (is_model=true)")
        notes = (f"[{tag}; collection={c['name']}; pattern={c['pattern']}; "
                 f"source={c['url']}] {notes}").strip()

        products.append({
            "product_id": pid,
            "vendor_id": VENDOR_ID,
            "name": f"Alma {name}",
            "brand": "Alma",
            "category": category,
            "subcategory": f"{c['name']} — {name}",
            "material": material,
            "specifications": {k: v for k, v in specifications.items() if v not in (None, "")},
            "unit": "sqm" if not (is_maint or is_accessory) else "piece",
            "origin_country": "Italy",
            "certifications": [] if is_maint else ["FSC", "PEFC"],
            "datasheet_url": ds or "",
            "image_urls": image_urls,
            "notes": notes,
            "source": SOURCE,
        })

n_models = len(products)

# ---------------------------------------------------------------------------
# PRODUCTS — colour / finish child SKUs (granularity 2)
# ---------------------------------------------------------------------------
swatches = catalog["swatches"]


def swatch_path(species: str, code: str) -> list[str]:
    for s in swatches:
        if s["species"] == species and s["color_code"] == code:
            return [f"{IMG_PREFIX}/{s['file']}"]
    return []


for e in catalog["essences"]:
    species = e["species"]
    sp_slug = slug(species)
    for col in e["colors"]:
        code = col["code"]
        pid = f"alma-{sp_slug}-{slug(code)}"
        imgs = swatch_path(species, code)
        products.append({
            "product_id": pid,
            "vendor_id": VENDOR_ID,
            "name": f"Alma {species} — {col['name']}",
            "brand": "Alma",
            "category": "engineered_flooring" if "Larch" not in species and "Teak" not in species else "decking",
            "subcategory": "colour / finish variant",
            "material": species,
            "specifications": {
                "color": col["name"],
                "color_code": code,
                "finish": col["family"],
                "species": species,
                "pattern": "applies across plank/herringbone/chevron/geometric/design formats",
            },
            "unit": "sqm",
            "origin_country": "Italy",
            "certifications": ["FSC", "PEFC"],
            "datasheet_url": CATALOGUE_PDF or "",
            "image_urls": imgs,
            "notes": (f"[colour_sku; species_essence={species}; family={col['family']}; "
                      f"code={code}] Alma {species} in {col['name']} finish. One of the "
                      f"brand's colour/treatment options, selectable on any compatible "
                      f"model/format."),
            "source": SOURCE,
        })

n_colors = len(products) - n_models

# ---------------------------------------------------------------------------
# PRODUCT IMAGES — every PDF + every scraped image
# ---------------------------------------------------------------------------
manifest = json.loads((ROOT / "data" / "raw" / "alma" / "manifest.json").read_text(encoding="utf-8"))
images = []

# map image filename -> product_id (model hero or colour swatch)
img_to_product: dict[str, str] = {}
for c in catalog["collections"]:
    for m in c["models"]:
        pid = f"alma-{c['slug']}-{slug(m['name'])}"
        for fn in m.get("image_files", []):
            img_to_product.setdefault(fn, pid)
for s in swatches:
    for e in catalog["essences"]:
        if any(col["code"] == s["color_code"] for col in e["colors"]) and e["species"] == s["species"]:
            img_to_product.setdefault(s["file"], f"alma-{slug(s['species'])}-{slug(s['color_code'])}")

# datasheet pdf -> model product (first match)
doc_to_product: dict[str, str] = {}
for c in catalog["collections"]:
    for m in c["models"]:
        ds = datasheet_for(c["slug"], m["name"])
        if ds:
            doc_to_product.setdefault(ds.split("/")[-1], f"alma-{c['slug']}-{slug(m['name'])}")

# PDFs
for d in catalog["documents"]:
    rec = {
        "vendor_id": VENDOR_ID,
        "file_name": d["file"],
        "storage_path": f"{DOCS_PREFIX}/{d['file']}",
        "content_type": "application/pdf",
        "file_size_bytes": d.get("bytes", 0),
        "description": d.get("label", "") or d["file"],
        "type": "catalog" if d["type"] == "catalog" else (
            "datasheet" if d["type"] in ("datasheet", "declaration_of_performance") else "document"),
        "doc_class": d["type"],
        "source": SOURCE,
    }
    if d["file"] in doc_to_product:
        rec["product_id"] = doc_to_product[d["file"]]
    images.append(rec)

# images
for im in manifest.get("images", []):
    fn = im["file"]
    ext = fn.lower().rsplit(".", 1)[-1]
    ctype = "image/png" if ext == "png" else "image/jpeg"
    rec = {
        "vendor_id": VENDOR_ID,
        "file_name": fn,
        "storage_path": f"{IMG_PREFIX}/{fn}",
        "content_type": ctype,
        "file_size_bytes": im.get("bytes", 0),
        "description": "Alma product / swatch image",
        "type": "product_photo",
        "source": SOURCE,
    }
    if fn in img_to_product:
        rec["product_id"] = img_to_product[fn]
    images.append(rec)

# ---------------------------------------------------------------------------
# WRITE
# ---------------------------------------------------------------------------
json.dump(vendors, open(OUT / "alma_vendors.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
json.dump(products, open(OUT / "alma_products.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
json.dump(images, open(OUT / "alma_product_images.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

linked_imgs = sum(1 for i in images if i.get("product_id"))
print(f"vendors:        {len(vendors)}  -> {VENDOR_ID}")
print(f"products:       {len(products)}  ({n_models} model parents + {n_colors} colour SKUs)")
print(f"product_images: {len(images)}  ({len([i for i in images if i['content_type']=='application/pdf'])} PDFs + "
      f"{len([i for i in images if i['content_type'].startswith('image')])} images; {linked_imgs} linked to a product)")
print(f"  catalogue pdf: {CATALOGUE_PDF}")
print(f"  -> {OUT}")
