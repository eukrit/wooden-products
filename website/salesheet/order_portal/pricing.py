"""Pricing formulas for the order portal.

landed_cost_thb_per_m = sku_map.line_m_price_usd * fx_rate * landed_multiplier
default_unit_price_thb = landed_cost_thb_per_m * default_markup
gm_percent              = (unit_price - landed) / unit_price * 100

Sources of truth:
  - data/catalog/leka-sku-map.json  (vendor USD per metre)
  - data/catalog/leka-taxonomy.json (customer-facing catalog)
  - data/catalog/order-portal-config.json (fx fallback, multipliers, GM floor)
  - Firestore catalog_pricing/{sku}  (admin per-SKU overrides)
"""
from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Any

from . import config as cfg

log = logging.getLogger("order_portal.pricing")


def _candidate_paths(filename: str) -> list[str]:
    here = os.path.dirname(os.path.abspath(__file__))
    return [
        os.path.join("/app", "data", "catalog", filename),
        os.path.abspath(os.path.join(here, "..", "data", "catalog", filename)),
        os.path.abspath(os.path.join(here, "..", "..", "..", "data", "catalog", filename)),
    ]


def _load_json(filename: str) -> dict[str, Any]:
    for path in _candidate_paths(filename):
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                log.info("Loaded %s from %s", filename, path)
                return json.load(fh)
    raise FileNotFoundError(f"{filename} not found. Checked: {_candidate_paths(filename)}")


@lru_cache(maxsize=1)
def taxonomy() -> dict[str, Any]:
    return _load_json("leka-taxonomy.json")


@lru_cache(maxsize=1)
def sku_map() -> dict[str, dict[str, Any]]:
    """Return dict keyed by leka_sku -> full sku-map entry."""
    raw = _load_json("leka-sku-map.json")
    return {entry["leka_sku"]: entry for entry in raw.get("products", [])}


# Taxonomy uses LKP-DK-H-140-23 (with sub-type segment H/S/G).
# SKU-map uses LKP-DK-140-23 (no sub-type segment). Wall panels have
# special case R/V → "" / "-HC".  Build a lookup that tries the exact
# SKU first, then falls back to known transformations.
def lookup_sku_entry(sku: str) -> dict[str, Any] | None:
    m = sku_map()
    if sku in m:
        return m[sku]

    parts = sku.split("-")
    # Strip single-letter sub-type segment at index 2 (after SERIES, TYPE)
    # e.g. LKP-DK-H-140-23 -> LKP-DK-140-23
    if len(parts) >= 5 and len(parts[2]) == 1:
        candidate = "-".join([parts[0], parts[1]] + parts[3:])
        if candidate in m:
            return m[candidate]
        # Wall panel special: R→"", V→-HC
        if parts[2] == "V":
            candidate_hc = candidate + "-HC"
            if candidate_hc in m:
                return m[candidate_hc]

    # Strip trailing -WG / -EM / -KC / -ST finish suffix
    # e.g. LKH-CL-F-148-21-WG -> LKH-CL-F-148-21
    if len(parts) >= 4 and parts[-1] in {"WG", "EM", "KC", "ST", "2D", "3D"}:
        stripped = lookup_sku_entry("-".join(parts[:-1]))
        if stripped:
            return stripped
        # Heritage SKU-map uses 2D/3D while taxonomy uses WG/EM. Try aliases.
        finish_alias = {"WG": "2D", "EM": "3D", "2D": "WG", "3D": "EM"}
        aliased_finish = finish_alias.get(parts[-1])
        if aliased_finish:
            alt = "-".join(parts[:-1] + [aliased_finish])
            if alt in m:
                return m[alt]
            # Also try stripping sub-type then applying the finish alias
            if len(parts) >= 5 and len(parts[2]) == 1:
                alt2 = "-".join([parts[0], parts[1]] + parts[3:-1] + [aliased_finish])
                if alt2 in m:
                    return m[alt2]

    return None


# ---------- Firestore admin overrides ----------

def load_pricing_overrides() -> dict[str, dict[str, Any]]:
    """Return {sku: {landed_thb_per_m?, unit_price_thb?, updated_by_uid, updated_at}}."""
    try:
        from . import firestore_client as fs  # lazy import
        db = fs.get_db()
        overrides: dict[str, dict[str, Any]] = {}
        for doc in db.collection("catalog_pricing").stream():
            overrides[doc.id] = doc.to_dict() or {}
        return overrides
    except Exception as exc:  # Firestore unavailable = no overrides, safe default
        log.warning("Could not load catalog_pricing overrides: %s", exc)
        return {}


# ---------- Formulas ----------

def landed_cost_thb_per_m(
    sku: str,
    fx_rate: float,
    overrides: dict[str, dict[str, Any]] | None = None,
) -> float | None:
    """Return the landed cost (THB/m) for a SKU, or None if no USD price known.

    Precedence: Firestore override > computed from SKU-map USD.
    """
    overrides = overrides or {}
    ovr = overrides.get(sku, {})
    if ovr.get("landed_thb_per_m"):
        return float(ovr["landed_thb_per_m"])

    entry = lookup_sku_entry(sku)
    if not entry:
        return None
    usd_per_m = entry.get("line_m_price_usd")
    if not usd_per_m:
        return None
    multiplier = float(cfg.pricing()["landed_multiplier"])
    return round(float(usd_per_m) * fx_rate * multiplier, 2)


def default_unit_price_thb(
    sku: str,
    landed_thb_per_m: float | None,
    overrides: dict[str, dict[str, Any]] | None = None,
) -> float | None:
    overrides = overrides or {}
    ovr = overrides.get(sku, {})
    if ovr.get("unit_price_thb"):
        return float(ovr["unit_price_thb"])
    if landed_thb_per_m is None:
        return None
    markup = float(cfg.pricing()["default_markup"])
    return round(landed_thb_per_m * markup, 2)


def gm_percent(unit_price_thb: float | None, landed_thb_per_m: float | None) -> float | None:
    if unit_price_thb is None or landed_thb_per_m is None or unit_price_thb <= 0:
        return None
    return round((unit_price_thb - landed_thb_per_m) / unit_price_thb * 100, 2)


def gm_floor_for_role(role: str) -> float:
    p = cfg.pricing()
    if role == cfg.auth()["default_role_admin"]:
        return float(p["gm_floor_admin_pct"])
    return float(p["gm_floor_sales_pct"])


def validate_line_gm(unit_price: float, landed: float, role: str) -> tuple[bool, str]:
    floor = gm_floor_for_role(role)
    gm = gm_percent(unit_price, landed)
    if gm + 0.01 < floor:  # small tolerance for rounding
        return False, f"GM {gm:.1f}% below floor {floor:.1f}% for role '{role}'"
    return True, ""


# ---------- Fence configurator pricing ----------

def _compute_boards_per_bay(height_m: float, gap_cm: float) -> int:
    """Mirror the configurator's JS math so client UI + server agree."""
    board_mm = 148
    gap_mm = max(0.0, float(gap_cm)) * 10
    top_rail = 40
    bottom_rail = 60
    usable_mm = max(0.0, float(height_m) * 1000 - top_rail - bottom_rail)
    pitch_mm = board_mm + (gap_mm if gap_mm > 0 else 0)
    if pitch_mm <= 0:
        return 0
    full_planks = max(1, int((usable_mm + gap_mm) // pitch_mm))
    used = full_planks * board_mm + max(0, full_planks - 1) * gap_mm
    remaining = max(0.0, usable_mm - used)
    trim_visible = max(0.0, remaining - (gap_mm if full_planks >= 1 else 0))
    has_trim = trim_visible > 0.5
    return full_planks + (1 if has_trim else 0)


def fence_retail_thb(spec: dict[str, Any], fx_rate: float) -> dict[str, Any]:
    """Compute the indicative retail price for a WPC fence configuration.

    Returns a dict with { retail_thb, breakdown, warnings }. None-safe:
    missing SKU prices degrade to 0 rather than raising, so the UI can
    render a "pricing unavailable" message without a 500.

    spec keys (all floats/ints unless noted):
      - series: "premium" | "classic"  (currently both priced off fence_sku)
      - height_m, bay_m, gap_cm, fence_run_m
      - single_gates, double_gates
    """
    pricing_cfg = cfg.pricing()
    series = str(spec.get("series", "premium")).lower()
    # Classic (Heritage solid WPC) is cheaper than Premium (co-ex). If ops
    # hasn't given us a separate Heritage fence SKU yet, both keys point to
    # the same LKP-FN board and we discount Classic via price_ratio.
    if series == "classic":
        sku = pricing_cfg.get("fence_sku_classic", pricing_cfg.get("fence_sku_premium", "LKP-FN-161-20"))
        price_ratio = float(pricing_cfg.get("fence_classic_price_ratio", 1.0))
    else:
        # Premium or "undecided" → price at Premium (gives the honest upper bound)
        sku = pricing_cfg.get("fence_sku_premium", "LKP-FN-161-20")
        price_ratio = 1.0

    overrides = load_pricing_overrides()
    landed = landed_cost_thb_per_m(sku, fx_rate=fx_rate, overrides=overrides)
    unit_price_per_m = default_unit_price_thb(sku, landed, overrides=overrides)

    warnings: list[str] = []
    if unit_price_per_m is None:
        warnings.append(f"No unit price for SKU {sku}; returning zero fence-board cost")
        unit_price_per_m = 0.0
    # Apply Classic discount after override lookup so Firestore per-SKU
    # admin overrides still respect the series relationship.
    if price_ratio != 1.0:
        unit_price_per_m = round(unit_price_per_m * price_ratio, 2)

    fence_run_m = float(spec.get("fence_run_m", 0) or 0)
    height_m = float(spec.get("height_m", 2.0) or 2.0)
    gap_cm = float(spec.get("gap_cm", 0) or 0)
    bay_m = float(spec.get("bay_m", 2.0) or 2.0)

    boards_per_bay = _compute_boards_per_bay(height_m, gap_cm)
    # Total linear metres of fence-board stock needed:
    #   bays_in_run * bay_width * boards_per_bay
    # Each bay is a rectangle with bay_m horizontal run × boards_per_bay rows.
    # Round bays up (partial bays still need a full bay's worth of boards).
    import math
    bays = max(1, math.ceil(fence_run_m / bay_m)) if bay_m > 0 else 0
    board_linear_m = bays * bay_m * boards_per_bay
    board_cost_thb = round(board_linear_m * unit_price_per_m)

    # Post + sub-frame + install allowance is not priced off the SKU map.
    # We roll it into a simple per-metre uplift to keep the indicative
    # number honest without modelling every hardware line.
    structural_uplift_per_m = float(pricing_cfg.get("fence_structural_uplift_thb_per_m", 900))
    structural_cost = round(fence_run_m * structural_uplift_per_m)

    gate_cfg = pricing_cfg.get("fence_gate_hardware_thb", {"single": 0, "double": 0})
    single_gates = int(spec.get("single_gates", 0) or 0)
    double_gates = int(spec.get("double_gates", 0) or 0)
    gate_cost = round(
        single_gates * float(gate_cfg.get("single", 0))
        + double_gates * float(gate_cfg.get("double", 0))
    )

    precision = max(1, int(cfg.load().get("architect_portal", {}).get("price_precision_thb", 100)))
    subtotal = board_cost_thb + structural_cost + gate_cost
    rounded = int(round(subtotal / precision) * precision)

    return {
        "retail_thb": rounded,
        "breakdown": {
            "series": series,
            "sku": sku,
            "price_ratio": price_ratio,
            "unit_price_thb_per_m": unit_price_per_m,
            "board_linear_m": round(board_linear_m, 2),
            "board_cost_thb": board_cost_thb,
            "structural_cost_thb": structural_cost,
            "structural_uplift_thb_per_m": structural_uplift_per_m,
            "gate_cost_thb": gate_cost,
            "single_gates": single_gates,
            "double_gates": double_gates,
            "precision_thb": precision,
            "subtotal_thb": subtotal,
        },
        "warnings": warnings,
    }
