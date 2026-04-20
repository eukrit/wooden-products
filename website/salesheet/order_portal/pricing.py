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
