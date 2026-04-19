"""Estimate packaging volume + landed cost per SKU from China to Thailand.

Pulls packaging data from manufacturer PIs (NS20240516LJ, GK20260410LJ) and
vendor catalog specs (AOLO ASA kg/m, Jackson Co-Ex kg/m). For SKUs without
published data, estimates weight from profile dimensions using WPC density.

Calls shipping-automation/mcp-server/cost_engine.py for landed-cost math
(China → Thailand, all 4 methods: china_thai_sea / fcl_40 / lcl / air).

Outputs:
  data/catalog/leka-landed-cost.json — full per-SKU breakdown
  stdout  — sorted summary table

Usage: python scripts/estimate_landed_costs.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Import shipping-automation cost engine
SHIPPING_ENGINE = Path(
    r"C:\Users\Eukrit\OneDrive\Documents\Claude Code\shipping-automation\mcp-server"
)
sys.path.insert(0, str(SHIPPING_ENGINE))
from cost_engine import estimate_landed_cost, get_live_fx  # noqa: E402

# ── Packaging specs ────────────────────────────────────────────────────
# Format: vendor_code → {usd_m, kg_m, pcs_per_40hc, board_len_m}
#
# Sources:
#  PI-NS20240516LJ  = Anhui Aolo price list (15 priced SKUs, FOB Lianyungang)
#  PI-GK20260410LJ  = Anhui Aolo fence kit (GK161.5/20C @ $2.20/m)
#  AOLO-ASA.pdf     = Shield Series catalog (kg/m spec)
#  Jackson-Co-Ex.pdf = Co-Ex catalog (kg/m spec, page 1-9)
#  First-gen-Jackson.pdf = Heritage catalog (spec only)
#
# Container: 40HC = 76.28 cbm theoretical, ~68 cbm usable with packaging.
# Where pcs/40HC is known from PI, that's the authoritative packaging number.
# Where not, we estimate via profile volume × 1.30 packaging overhead.

C40HC_USABLE_CBM = 68.0  # industry standard usable volume for stacked bundles
WPC_DENSITY = 1.40       # g/cm³ solid WPC (for estimating weight on SKUs without spec)
WPC_HOLLOW_DENSITY_FACTOR = 0.55   # hollow profiles weigh ~55% of solid equivalent
PKG_OVERHEAD = 1.30      # 30% CBM overhead for bundles, straps, tolerance

PACKAGING = {
    # Co-Extrusion (PI NS20240516LJ — authoritative pcs/40HC)
    "AL-GK219/26A":   {"usd_m": 2.91, "kg_m": 2.91, "pcs_40hc": 3240, "len_m": 2.9, "src": "PI-NS20240516LJ + Jackson p4"},
    "AL-GK219/26D":   {"usd_m": 2.70, "kg_m": 2.91, "pcs_40hc": 3240, "len_m": 2.9, "src": "PI-NS20240516LJ + Jackson p4"},
    "AL-GK140/23C":   {"usd_m": 2.55, "kg_m": 2.74, "pcs_40hc": 3400, "len_m": 2.9, "src": "PI-NS20240516LJ + Jackson p1"},
    "AL-GK148/22A":   {"usd_m": 2.58, "kg_m": 2.75, "pcs_40hc": 3400, "len_m": 2.9, "src": "PI-NS20240516LJ + Jackson p2"},
    "AL-GS156/21C":   {"usd_m": 1.56, "kg_m": 1.67, "pcs_40hc": 5600, "len_m": 2.9, "src": "PI-NS20240516LJ + Jackson p6"},
    # First generation (PI NS20240516LJ)
    "AL-K219/26B":    {"usd_m": 2.05, "kg_m": 2.90, "pcs_40hc": 3240, "len_m": 2.9, "src": "PI-NS20240516LJ (est kg/m)"},
    "AL-K140/25L":    {"usd_m": 1.80, "kg_m": 2.70, "pcs_40hc": 3800, "len_m": 2.9, "src": "PI-NS20240516LJ (avg 2D/3D)"},
    "AL-K140/20A":    {"usd_m": 1.44, "kg_m": 2.00, "pcs_40hc": 4600, "len_m": 2.9, "src": "PI-NS20240516LJ (avg 2D/3D)"},
    "AL-S148/21/A":   {"usd_m": 1.19, "kg_m": 1.80, "pcs_40hc": 6000, "len_m": 2.9, "src": "PI-NS20240516LJ (avg 2D/3D)"},
    "AL-K145/21A":    {"usd_m": 1.98, "kg_m": 2.26, "pcs_40hc": 3500, "len_m": 2.9, "src": "PI-NS20240516LJ + Jackson p2"},
    "AL-K140/23.5K":  {"usd_m": 2.08, "kg_m": 2.40, "pcs_40hc": 3200, "len_m": 2.9, "src": "PI-NS20240516LJ"},
    "AL-K148/23B":    {"usd_m": 1.98, "kg_m": 2.75, "pcs_40hc": 3500, "len_m": 2.9, "src": "PI-NS20240516LJ (est)"},
    # Fence (PI GK20260410LJ — board length 2.025m)
    "GK161.5/20C":    {"usd_m": 2.20, "kg_m": 2.20, "pcs_40hc": 5100, "len_m": 2.025, "src": "PI-GK20260410LJ + Jackson p2"},

    # Shield Series (ASA catalog — has kg/m but not pcs/40HC; compute via volume)
    "AOLO-170*14":    {"usd_m": 1.65, "kg_m": 0.90, "len_m": 2.9, "pcs_40hc": None, "src": "AOLO-ASA catalog (est price)"},
    "AOLO-189*20":    {"usd_m": 2.10, "kg_m": 1.48, "len_m": 2.9, "pcs_40hc": None, "src": "AOLO-ASA catalog (est price)"},
    "AOLO-207*16":    {"usd_m": 2.00, "kg_m": 1.10, "len_m": 2.9, "pcs_40hc": None, "src": "AOLO-ASA catalog (est price)"},
    "AOLO-219*25":    {"usd_m": 2.40, "kg_m": 1.50, "len_m": 2.9, "pcs_40hc": None, "src": "AOLO-ASA catalog (est price)"},
    "AOLO-224*21":    {"usd_m": 2.30, "kg_m": 1.20, "len_m": 2.9, "pcs_40hc": None, "src": "AOLO-ASA catalog (est price)"},
    "AOLO-122*10":    {"usd_m": 1.20, "kg_m": 0.60, "len_m": 2.9, "pcs_40hc": None, "src": "AOLO-ASA catalog (est price)"},
    "AOLO-112*16":    {"usd_m": 1.25, "kg_m": 0.68, "len_m": 2.9, "pcs_40hc": None, "src": "AOLO-ASA catalog (est price)"},
    "AOLO-121*12":    {"usd_m": 1.15, "kg_m": 0.51, "len_m": 2.9, "pcs_40hc": None, "src": "AOLO-ASA catalog (est price)"},
    "AOLO-140*24":    {"usd_m": 2.80, "kg_m": 2.30, "len_m": 2.9, "pcs_40hc": None, "src": "AOLO-ASA catalog (est price)"},
    "AOLO-140*32":    {"usd_m": 3.40, "kg_m": 2.80, "len_m": 2.9, "pcs_40hc": None, "src": "AOLO-ASA catalog (est price)"},
    "AOLO-156*17":    {"usd_m": 2.00, "kg_m": 1.30, "len_m": 2.9, "pcs_40hc": None, "src": "AOLO-ASA catalog (est price)"},
    "AOLO-45*45":     {"usd_m": 0.75, "kg_m": 0.32, "len_m": 2.9, "pcs_40hc": None, "src": "AOLO-ASA catalog (est price)"},

    # Extended Jackson catalog (Structure, extra Co-Ex)
    "AL-GK169-26A":   {"usd_m": 2.20, "kg_m": 2.19, "len_m": 2.9, "pcs_40hc": 3200, "src": "Jackson p4 (est price from size)"},
    "AL-GK195-20A":   {"usd_m": 1.95, "kg_m": 2.32, "len_m": 2.9, "pcs_40hc": 3500, "src": "Jackson p4 (est price)"},
    "AL-GK205-25A":   {"usd_m": 2.60, "kg_m": 2.75, "len_m": 2.9, "pcs_40hc": 3100, "src": "Jackson p4 (est price)"},
    "AL-GK245-33A":   {"usd_m": 3.60, "kg_m": 3.86, "len_m": 2.9, "pcs_40hc": 2400, "src": "Jackson p5 (est price)"},
    "AL-GS140-18B":   {"usd_m": 2.80, "kg_m": 3.17, "len_m": 2.9, "pcs_40hc": 3000, "src": "Jackson p2 (est price, solid)"},
    "AL-GS140-23A":   {"usd_m": 3.40, "kg_m": 3.96, "len_m": 2.9, "pcs_40hc": 2700, "src": "Jackson p2 (est price, solid)"},
    "AL-GK200-25A":   {"usd_m": 3.80, "kg_m": 4.26, "len_m": 2.9, "pcs_40hc": 2500, "src": "Jackson p4 (est price)"},
    "AL-GK145-21C":   {"usd_m": 2.00, "kg_m": 2.26, "len_m": 2.9, "pcs_40hc": 3500, "src": "Jackson p2 (est price)"},
    "AL-GS156-18A":   {"usd_m": 1.40, "kg_m": 1.53, "len_m": 2.9, "pcs_40hc": 5800, "src": "Jackson p6 (est price)"},
    "AL-GK215-20A":   {"usd_m": 2.80, "kg_m": 2.91, "len_m": 2.9, "pcs_40hc": 2900, "src": "Jackson p2 (est price)"},
    "AL-GK100-100C":  {"usd_m": 5.00, "kg_m": 4.64, "len_m": 2.9, "pcs_40hc": 900,  "src": "Jackson p3 column (est)"},
    "AL-GK120-120C":  {"usd_m": 6.20, "kg_m": 5.34, "len_m": 2.9, "pcs_40hc": 700,  "src": "Jackson p3 column (est)"},
    "AL-GK60-42B":    {"usd_m": 1.80, "kg_m": 1.25, "len_m": 2.9, "pcs_40hc": 2800, "src": "Jackson p3 beam (est)"},
    "AL-GK100-50C":   {"usd_m": 2.90, "kg_m": 2.39, "len_m": 2.9, "pcs_40hc": 2200, "src": "Jackson p3 beam (est)"},
    "AL-GK120-62A":   {"usd_m": 3.60, "kg_m": 3.11, "len_m": 2.9, "pcs_40hc": 1800, "src": "Jackson p3 beam (est)"},
    "AL-GS50-50A":    {"usd_m": 1.10, "kg_m": 0.75, "len_m": 2.9, "pcs_40hc": 4500, "src": "Jackson p6 edging (est)"},
    # Heritage columns (first-gen)
    "AL-K150-150A":   {"usd_m": 6.80, "kg_m": 6.50, "len_m": 2.9, "pcs_40hc": 650,  "src": "Firstgen p15 (est solid)"},
    "AL-K4200-200A":  {"usd_m": 10.50, "kg_m": 11.0, "len_m": 2.9, "pcs_40hc": 380, "src": "Firstgen p15 (est solid)"},

    # DIY tiles (DIY catalog) — 300x300x22mm interlocking
    "JY-WPCOE-4H/4S": {"usd_m": None, "usd_pc": 1.85, "kg_m": None, "kg_pc": 0.40, "pcs_40hc": 12474, "len_m": None, "pc_area_m2": 0.09, "src": "DIY catalog p3 (300x300 tile)"},
    "JY-PP9C/D/G/I":  {"usd_m": None, "usd_pc": 0.95, "kg_m": None, "kg_pc": 0.28, "pcs_40hc": 13608, "len_m": None, "pc_area_m2": 0.09, "src": "DIY catalog p4 (PP tile)"},
    "JY-AGT-A/S":     {"usd_m": None, "usd_pc": 1.20, "kg_m": None, "kg_pc": 0.35, "pcs_40hc": 11680, "len_m": None, "pc_area_m2": 0.09, "src": "DIY catalog p5 (grass tile)"},
    "JY-S-S/C":       {"usd_m": None, "usd_pc": 1.60, "kg_m": None, "kg_pc": 0.65, "pcs_40hc": 8640,  "len_m": None, "pc_area_m2": 0.09, "src": "DIY catalog p5 (stone tile)"},
}

# ── MOQ policy ──────────────────────────────────────────────────────────
# Anhui Aolo PI NS20240516LJ specifies 40HC mixed-product ordering:
#  - Per-SKU MOQ: 1 full pallet/bundle (~200-400m depending on width)
#  - Container MOQ: 1 × 40HC mixed = ~68 CBM / ~27.5 t
MOQ_PCS = {
    # Per-SKU minimum when ordering mixed container
    "_default_per_sku": 200,
    # Full container fill (use pcs_40hc if known, else compute)
    "_full_container": None,  # flag — use 1 * 40HC packaging for landed cost model
}


# ── Helpers ─────────────────────────────────────────────────────────────
def estimate_pcs_40hc(width_mm: float, thickness_mm: float, length_m: float,
                      series: str) -> int:
    """Estimate pcs per 40HC when PI doesn't state it.

    Based on board volume + packaging overhead. 40HC usable = 68 cbm.
    Shield/Signature profiles are hollow (tighter packing) vs Heritage solid.
    """
    raw_cbm_per_pc = (width_mm * thickness_mm * length_m * 1000) / 1e9
    packed_cbm = raw_cbm_per_pc * PKG_OVERHEAD
    return int(C40HC_USABLE_CBM / packed_cbm)


def _normalize(code: str) -> str:
    """Normalize vendor-code punctuation for lookup (taxonomy uses -, PIs use /)."""
    return code.replace("/", "-").replace("*", "x").upper().strip()


_NORM_PACKAGING = {_normalize(k): v for k, v in PACKAGING.items()}


def spec_for_vendor_code(code: str, w: float, t: float, series: str,
                         len_m: float = 2.9) -> dict:
    """Look up packaging spec; fall back to calculated estimate."""
    s = PACKAGING.get(code) or _NORM_PACKAGING.get(_normalize(code))
    if s:
        return s
    # Fallback: compute from dimensions
    hollow = series in ("LKP", "LKA")
    kg_m = w * t * (WPC_DENSITY * (WPC_HOLLOW_DENSITY_FACTOR if hollow else 1.0)) / 1000
    pcs = estimate_pcs_40hc(w, t, len_m, series)
    usd_m = 0.015 * w * t / 100   # rough heuristic: $0.15 per cm² × thickness
    return {
        "usd_m": round(usd_m, 2),
        "kg_m": round(kg_m, 2),
        "len_m": len_m,
        "pcs_40hc": pcs,
        "src": "computed from dimensions (no PI data)",
        "estimated": True,
    }


# ── Main ────────────────────────────────────────────────────────────────
def main() -> None:
    tax = json.loads((ROOT / "data" / "catalog" / "leka-taxonomy.json").read_text(encoding="utf-8"))

    fx = get_live_fx()
    usd_to_thb = fx.get("USD", 33.15)

    print(f"FX: USD 1 = THB {usd_to_thb:.2f}  (live + 2% buffer)")
    print(f"Container: 40HC, usable {C40HC_USABLE_CBM} cbm\n")

    # Flatten taxonomy products
    products = []
    for cat_slug, cat in tax["categories"].items():
        for p in cat.get("products", []):
            products.append({
                "cat": cat_slug, "sub": p.get("sub", ""),
                "sku": p["sku"], "name": p["name"],
                "vendor_code": p.get("vendor_code", ""),
                "w": p.get("w", 0), "t": p.get("t", 0),
                "len_m": p.get("len", 2900) / 1000,
            })

    out_rows = []
    for p in products:
        series = p["sku"].split("-")[0]
        spec = spec_for_vendor_code(p["vendor_code"], p["w"], p["t"], series, p["len_m"])
        pcs_40hc = spec.get("pcs_40hc") or estimate_pcs_40hc(p["w"], p["t"], p["len_m"], series)
        is_tile = "pc_area_m2" in spec
        len_m = spec.get("len_m") or p["len_m"]

        # Derived metrics per piece
        usd_pc = spec.get("usd_pc") if is_tile else (spec["usd_m"] * len_m)
        kg_pc  = spec.get("kg_pc")  if is_tile else (spec["kg_m"]  * len_m)
        raw_cbm_pc = (p["w"] * p["t"] * len_m * 1000) / 1e9 if not is_tile else (0.3 * 0.3 * 0.022)
        cbm_pc = raw_cbm_pc * PKG_OVERHEAD

        # Full 40HC container load
        goods_usd = pcs_40hc * usd_pc
        container_kg = pcs_40hc * kg_pc
        container_cbm = min(pcs_40hc * cbm_pc, C40HC_USABLE_CBM)

        # Run landed-cost engine for 4 methods
        methods = {}
        for m in ("china_thai_sea", "fcl_40", "lcl", "air"):
            try:
                r = estimate_landed_cost(
                    origin="china",
                    method=m,
                    goods_value=goods_usd,
                    goods_currency="USD",
                    cbm=container_cbm,
                    kg=container_kg,
                    container_count=1,
                    product_category="default",
                )
                total_thb = r["total_landed_thb"]
                methods[m] = {
                    "total_landed_thb": total_thb,
                    "per_m_thb": round(total_thb / (pcs_40hc * len_m), 2) if len_m else None,
                    "per_pc_thb": round(total_thb / pcs_40hc, 2),
                    "shipping_cost_thb": r["shipping_cost_thb"],
                    "transit_days": r["transit_days"],
                    "ratio_to_goods_pct": r["ratio_to_goods_pct"],
                }
            except Exception as e:
                methods[m] = {"error": str(e)}

        out_rows.append({
            "sku": p["sku"], "name": p["name"], "category": p["cat"], "sub": p["sub"],
            "vendor_code": p["vendor_code"],
            "dimensions_mm": {"w": p["w"], "t": p["t"], "len": int(len_m * 1000)},
            "packaging": {
                "kg_per_m": spec.get("kg_m"),
                "kg_per_pc": round(kg_pc, 3),
                "usd_per_m": spec.get("usd_m"),
                "usd_per_pc": round(usd_pc, 3),
                "cbm_per_pc_raw": round(raw_cbm_pc, 5),
                "cbm_per_pc_packed": round(cbm_pc, 5),
                "pcs_per_40hc": pcs_40hc,
                "moq_pcs": MOQ_PCS["_default_per_sku"],
                "moq_m": round(MOQ_PCS["_default_per_sku"] * len_m, 1) if not is_tile else None,
                "full_container": {
                    "cbm": round(container_cbm, 2),
                    "kg": round(container_kg, 1),
                    "goods_usd": round(goods_usd, 2),
                },
                "source": spec["src"],
                "estimated": spec.get("estimated", False),
            },
            "landed_cost_per_container_40hc": {
                "china_thai_sea":  methods["china_thai_sea"],
                "fcl_40":          methods["fcl_40"],
                "lcl":             methods["lcl"],
                "air":             methods["air"],
            },
        })

    # Write JSON
    out_file = ROOT / "data" / "catalog" / "leka-landed-cost.json"
    out_file.write_text(json.dumps({
        "_meta": {
            "generated": "2026-04-19",
            "fx_usd_to_thb": usd_to_thb,
            "container_type": "40HC (68 cbm usable)",
            "engine": "shipping-automation/mcp-server/cost_engine.py",
            "moq_policy": "Per-SKU MOQ 200 pcs; mixed-SKU 1x40HC container",
        },
        "rows": out_rows,
    }, indent=2), encoding="utf-8")

    # Print table
    print(f"{'SKU':<22} {'W×T×L mm':<16} {'kg/m':>6} {'USD/m':>7} {'pcs/40HC':>9} {'Sea THB/m':>11} {'FCL THB/m':>11}")
    print("-" * 100)
    for r in sorted(out_rows, key=lambda x: x["sku"]):
        pkg = r["packaging"]
        sea = r["landed_cost_per_container_40hc"]["china_thai_sea"]
        fcl = r["landed_cost_per_container_40hc"]["fcl_40"]
        dim = f'{r["dimensions_mm"]["w"]}x{r["dimensions_mm"]["t"]}x{r["dimensions_mm"]["len"]}'
        print(f"{r['sku']:<22} {dim:<16} "
              f"{pkg.get('kg_per_m') or 0:>6} {pkg.get('usd_per_m') or 0:>7} "
              f"{pkg['pcs_per_40hc']:>9} "
              f"{sea.get('per_m_thb') or 0:>11} {fcl.get('per_m_thb') or 0:>11}")

    print(f"\nWrote {out_file.relative_to(ROOT)}")
    print(f"Total SKUs: {len(out_rows)}")


if __name__ == "__main__":
    main()
