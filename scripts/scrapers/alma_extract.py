"""Parse the raw Alma scrape (data/raw/alma/) into a normalised catalog.

Reads:
  data/raw/alma/pages/*.html      — collection + essence + info pages
  data/raw/alma/manifest.json     — list of downloaded PDFs + images

Writes:
  data/parsed/alma/alma_catalog.json   — nested: vendor, collections>models,
                                          essences>colours, documents, image index
  data/parsed/alma/alma_catalog.csv    — flat, one row per model
  data/parsed/alma/alma_skus.csv       — flat, one row per colour SKU

The catalog feeds scripts/firestore/build_alma_flooring.py.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "alma"
PAGES = RAW / "pages"
OUT = ROOT / "data" / "parsed" / "alma"
OUT.mkdir(parents=True, exist_ok=True)

BASE = "https://www.almafloor.it"

COLLECTIONS = [
    ("doghe",              "/en-gb/collezione-doghe",              "Plank",         "plank",         "engineered_flooring"),
    ("spina-ungherese-45", "/en-gb/collezione-spina-ungherese-45", "Chevron 45°",   "chevron-45",    "engineered_flooring"),
    ("spina-italiana-90",  "/en-gb/collezione-spina-italiana-90",  "Herringbone 90°", "herringbone-90", "engineered_flooring"),
    ("spina-francese-30",  "/en-gb/collezione-spina-francese-30",  "Chevron 30°",   "chevron-30",    "engineered_flooring"),
    ("geometrici",         "/en-gb/collezione-geometrici",         "Geometric",     "geometric",     "engineered_flooring"),
    ("design",             "/en-gb/collezione-design",             "Design",        "design",        "engineered_flooring"),
    ("intarsi",            "/en-gb/collezione-intarsi",            "Inlay",         "inlay",         "engineered_flooring"),
    ("esterno",            "/en-gb/collezione-esterno",            "Decking",       "decking",       "decking"),
    ("accessori",          "/en-gb/collezione-accessori",          "Accessories",   "accessory",     "moulding"),
]

ESSENCES = [
    ("european-oak",       "/en-gb/essence-european-oak",    "European Oak"),
    ("glacial-oak",        "/en-gb/glacial-oak",             "Glacial Oak"),
    ("european-walnut",    "/en-gb/essence-european-walnut", "European Walnut"),
    ("american-walnut",    "/en-gb/essence-american-walnut", "American Walnut"),
    ("asian-teak",         "/en-gb/Asian-teak",              "Asian Teak"),
    ("austrian-larch-bio", "/en-gb/austrian-larch-bio",      "Austrian Larch Bio"),
]

# Named products on the "thin" collection pages that carry no <div id=modello-*>
THIN_PRODUCTS = {
    "esterno":  [("Teak Asia", "Asian teak outdoor decking board.")],
    "accessori": [
        ("Stair skirt", "Matching stair skirting / nosing profile."),
        ("Skirting",    "Matching wood skirting board (battiscopa)."),
        ("Alma Clean",  "Maintenance product: routine cleaner for finished floors."),
        ("Alma Lux",    "Maintenance product: protective polish for lacquered floors."),
        ("Alma Soap",   "Maintenance product: soap for oiled floors."),
        ("Alma Oil",    "Maintenance product: refreshing oil for oiled floors."),
        ("Oil Care Plus", "Maintenance product: deep nourishing oil care."),
    ],
    "spina-francese-30": [("Chevron 30° (Spina Francese)", "French herringbone laid at 30° — made to order in the Alma essences and colours.")],
    "intarsi": [("Inlay (Intarsi)", "Custom marquetry / inlay parquet — bespoke designs, borders and medallions.")],
}

NOISE = re.compile(
    r"(Scrivi qui la tua didascalia|Write your caption here|Slide title|"
    r"Button|Read more|Discover more|Leggi tutto|Scopri di più)", re.I)

# ---------------------------------------------------------------------------


def soup_of(slug: str) -> BeautifulSoup | None:
    f = PAGES / f"{slug}.html"
    if not f.exists():
        return None
    return BeautifulSoup(f.read_text(encoding="utf-8"), "html.parser")


def clean(txt: str) -> str:
    txt = NOISE.sub(" ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def img_name(src: str) -> str | None:
    """Return a stable filename for a CDN image src (matches the scraper's naming)."""
    if "cdn-website.com" not in src:
        return None
    from urllib.parse import unquote
    norm = re.sub(r"-\d+w(\.(?:jpg|jpeg|png))", r"-640w\1", src, flags=re.I)
    name = unquote(norm.split("?")[0].split("/")[-1])
    name = re.sub(r"[^A-Za-z0-9._+\-]+", "_", name)
    return name[:160] or None


DIM_RE = re.compile(
    r"DIMENSION[S]?:\s*([0-9]+/[0-9]+)\s*x\s*([0-9.,/\- ]+?)\s*x\s*([0-9.,/\- ]+?)\s*mm",
    re.I)


def parse_dimension(text: str) -> dict | None:
    m = DIM_RE.search(text)
    if not m:
        return None
    struct, width_s, length_s = m.group(1), m.group(2).strip(), m.group(3).strip()
    total, noble = (struct.split("/") + [""])[:2]

    def first_num(s):
        n = re.search(r"[0-9]+(?:[.,][0-9]+)?", s)
        return float(n.group(0).replace(",", ".")) if n else None

    return {
        "dimension": clean(m.group(0).split(":", 1)[1]),
        "structure": struct,
        "thickness": _to_num(total),
        "noble_layer_mm": _to_num(noble),
        "width": first_num(width_s),
        "length": first_num(length_s),
        "width_raw": width_s,
        "length_raw": length_s,
    }


def _to_num(s):
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


def parse_models(slug: str) -> list[dict]:
    soup = soup_of(slug)
    if not soup:
        return []
    models = []
    for d in soup.find_all("div", id=re.compile(r"^modello-")):
        head = d.find(re.compile(r"^h[1-6]$"))
        name = head.get_text(" ", strip=True) if head else ""
        if not name or name.lower() == "slide title":
            continue
        full = d.get_text(" ", strip=True)
        dim = parse_dimension(full)
        # description: text after the dimension line, de-noised, first ~500 chars
        desc = ""
        if dim:
            after = full.split("mm", 1)[-1]
            after = clean(after)
            # drop a leading repeat of the model name
            after = re.sub(rf"^{re.escape(name)}\s*", "", after)
            desc = after[:500].strip()
        imgs = []
        for im in d.find_all("img"):
            nm = img_name(im.get("src") or im.get("data-src") or "")
            if nm and nm not in imgs and not re.search(r"logo|icon|flag", nm, re.I):
                imgs.append(nm)
        models.append({
            "name": name,
            "id": d.get("id"),
            "specs": dim or {},
            "description": desc,
            "image_files": imgs[:8],
        })
    return models


COLLECTION_HEADS = {"plank", "chevron 45", "herringbone 90", "chevron 30",
                    "geometric", "design", "inlay", "decking", "accessories"}
COLOR_RE = re.compile(r"(Natural|Stained|Smoked|Reagent|Retr|Brushed|Planed|Oiled|Bio|^T\d)", re.I)
TCODE_RE = re.compile(r"\bT[0-9A-Z]+\b")

RETRO_NAMES = {  # trade names lifted from the Retrò swatch images
    "T80": "Bronzo", "T81": "Lino", "T82": "Ibisco",
    "T83": "Cotone", "T84": "Pastello", "T85": "Alcantara",
}


def colour_family(label: str) -> str:
    l = label.lower()
    if "retr" in l:
        return "Retrò"
    if "reagent" in l:
        return "Reagent"
    if "smoked stained" in l:
        return "Smoked Stained"
    if "smoked" in l:
        return "Smoked"
    if "stained" in l:
        return "Stained"
    if "natural" in l:
        return "Natural"
    return "Other"


def parse_essence(slug: str, species: str) -> dict:
    soup = soup_of(slug)
    colors = []
    if soup:
        seen = set()
        for h in soup.find_all(re.compile(r"^h[1-6]$")):
            x = h.get_text(" ", strip=True)
            if not x:
                continue
            xl = x.lower().replace("°", "").strip()
            if xl in ("slide title", "") or xl in COLLECTION_HEADS:
                continue
            if x.upper() in ("THE BRAND", "USEFUL LINKS", "WHERE TO FIND US", "FOLLOW US"):
                continue
            if not COLOR_RE.search(x):
                continue
            # normalise "Glacial Oak, Brushed - T02" -> code/name
            label = x.split("-")[-1].strip() if " - " in x else x
            code_m = TCODE_RE.search(x)
            code = code_m.group(0) if code_m else ("NAT" if "natural" in x.lower() else label[:8])
            key = (code, label)
            if key in seen:
                continue
            seen.add(key)
            name = label
            if code in RETRO_NAMES:
                name = f"{label} {RETRO_NAMES[code]}".strip()
            colors.append({
                "code": code,
                "label": clean(x),
                "name": name,
                "family": colour_family(x),
            })
    return {"slug": slug, "species": species, "colors": colors}


# --- documents (PDFs) ------------------------------------------------------

def classify_doc(label: str, fname: str) -> str:
    s = (label + " " + fname).lower()
    if "dop" in s or "performance" in s:
        return "declaration_of_performance"
    if "scheda" in s or "technical" in s or "product sheet" in s:
        return "datasheet"
    if "catalog" in s:
        return "catalog"
    if "fsc" in s or "pefc" in s or "epd" in s or "voc" in s or "mapping" in s or "indoor" in s:
        return "certification"
    if "maintenance" in s or "manutenz" in s:
        return "maintenance"
    if "install" in s or "subfloor" in s:
        return "installation"
    if "garanz" in s or "warranty" in s:
        return "warranty"
    if "folder" in s or "presentation" in s or "retro" in s:
        return "brochure"
    return "document"


def model_token_for_doc(fname: str) -> str | None:
    """Map a technical-sheet filename to a model name (best-effort)."""
    m = re.search(r"Scheda\+Prodotto\+([A-Za-z0-9]+)", fname)
    if m:
        return m.group(1)
    return None


def parse_documents(manifest: dict) -> list[dict]:
    docs = []
    for p in manifest.get("pdfs", []):
        fname = p["file"]
        label = p.get("label") or fname
        docs.append({
            "file": fname,
            "label": clean(label),
            "url": p["url"],
            "bytes": p.get("bytes", 0),
            "type": classify_doc(label, fname),
            "model_token": model_token_for_doc(fname),
        })
    return docs


# --- swatch image index (ground-truth colour SKUs with photos) -------------

SPECIES_TOKENS = {
    "Rovere-Europeo": "European Oak", "Rovere-Glaciale": "Glacial Oak",
    "Noce-Europeo": "European Walnut", "Noce-Americano": "American Walnut",
}


def index_swatches(manifest: dict) -> list[dict]:
    out = []
    for im in manifest.get("images", []):
        f = im["file"]
        for tok, species in SPECIES_TOKENS.items():
            if f.startswith(tok):
                rest = f[len(tok) + 1:]
                code = TCODE_RE.search(rest)
                grade = re.search(r"-(AB|ABC|CD|C|D)(?:[-._]|$)", rest)
                out.append({
                    "file": f, "species": species,
                    "color_code": code.group(0) if code else None,
                    "grade": grade.group(1) if grade else None,
                })
                break
    return out


def find_swatch(swatches: list[dict], species: str, code: str) -> str | None:
    for s in swatches:
        if s["species"] == species and s["color_code"] == code:
            return s["file"]
    return None


# ---------------------------------------------------------------------------

def main() -> int:
    manifest = json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))

    collections = []
    for slug, path, name, pattern, category in COLLECTIONS:
        models = parse_models(slug)
        for nm, desc in THIN_PRODUCTS.get(slug, []):
            if not any(m["name"].lower() == nm.lower() for m in models):
                models.append({"name": nm, "id": None, "specs": {},
                               "description": desc, "image_files": []})
        collections.append({
            "slug": slug, "url": BASE + path, "name": name,
            "pattern": pattern, "category": category, "models": models,
        })
        print(f"  {name:16} ({slug:20}) -> {len(models)} models")

    essences = [parse_essence(slug, sp) for slug, _p, sp in ESSENCES]
    for e in essences:
        print(f"  essence {e['species']:18} -> {len(e['colors'])} colours")

    documents = parse_documents(manifest)
    swatches = index_swatches(manifest)
    print(f"  documents: {len(documents)} | swatch-coded images: {len(swatches)}")

    catalog = {
        "source": BASE,
        "brand": "Alma",
        "manufacturer": "GIORIO S.r.l.",
        "collections": collections,
        "essences": essences,
        "documents": documents,
        "swatches": swatches,
        "image_count": manifest.get("counts", {}).get("images", 0),
    }
    (OUT / "alma_catalog.json").write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")

    # flat model CSV
    with (OUT / "alma_catalog.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["collection", "pattern", "model", "structure", "dimension",
                    "thickness", "width", "length", "images", "description"])
        for c in collections:
            for m in c["models"]:
                s = m["specs"]
                w.writerow([c["name"], c["pattern"], m["name"],
                            s.get("structure", ""), s.get("dimension", ""),
                            s.get("thickness", ""), s.get("width", ""),
                            s.get("length", ""), len(m["image_files"]),
                            m["description"][:120]])

    # flat colour-SKU CSV
    with (OUT / "alma_skus.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["species", "code", "name", "family", "swatch_image"])
        for e in essences:
            for col in e["colors"]:
                w.writerow([e["species"], col["code"], col["name"],
                            col["family"], find_swatch(swatches, e["species"], col["code"]) or ""])

    n_models = sum(len(c["models"]) for c in collections)
    n_colors = sum(len(e["colors"]) for e in essences)
    print(f"\nTotals: {n_models} models, {n_colors} colour SKUs, "
          f"{len(documents)} docs")
    print(f"  -> {OUT / 'alma_catalog.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
