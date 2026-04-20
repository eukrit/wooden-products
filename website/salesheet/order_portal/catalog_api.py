"""Catalog API for the order builder.

GET /api/order/catalog         (any authed user)  — NEVER exposes vendor_code
GET /admin/api/catalog         (admin only)        — includes vendor_code + USD cost
GET /api/order/fx              (any authed user)  — current FX snapshot
POST /admin/api/fx/refresh     (admin only)        — force FX cache refresh

The catalog response is category-grouped JSON keyed by taxonomy category
slug. Each product includes resolved landed-cost + default-unit-price in
THB, computed from the live FX + SKU-map USD + Firestore overrides.
"""
from __future__ import annotations

import logging
from typing import Any

from flask import g, jsonify

from . import bp, fx, pricing
from .auth import require_auth, require_role

log = logging.getLogger("order_portal.catalog_api")


def _build_sku_payload(
    product: dict[str, Any],
    colours_full: list[dict[str, Any]],
    category_palette_codes: list[str],
    fx_rate: float,
    overrides: dict[str, dict[str, Any]],
    include_vendor: bool = False,
) -> dict[str, Any]:
    """Shape a product row for the catalog response.

    colours_full   — the taxonomy's palette_full (8 colours with hex + grain images)
    category_palette_codes — which of those apply to this category
    """
    sku = product["sku"]
    landed = pricing.landed_cost_thb_per_m(sku, fx_rate, overrides)
    default_price = pricing.default_unit_price_thb(sku, landed, overrides)

    colour_map = {c["code"]: c for c in colours_full}
    colours = [colour_map[code] for code in category_palette_codes if code in colour_map]

    payload = {
        "sku": sku,
        "sub": product.get("sub"),
        "name": product["name"],
        "w": product["w"],
        "t": product["t"],
        "len": product["len"],
        "image": product.get("image"),
        "finishes": product.get("finishes", []),
        "colours": colours,
        "landed_cost_thb_per_m": landed,
        "default_unit_price_thb": default_price,
    }

    if include_vendor:
        payload["vendor_code"] = product.get("vendor_code")
        sku_entry = pricing.lookup_sku_entry(sku) or {}
        payload["line_m_price_usd"] = sku_entry.get("line_m_price_usd")
        payload["pc_price_usd"] = sku_entry.get("pc_price_usd")
        payload["container_qty"] = sku_entry.get("container_qty")
        payload["sku_map_matched_as"] = sku_entry.get("leka_sku")

    return payload


def _build_catalog(include_vendor: bool) -> dict[str, Any]:
    tx = pricing.taxonomy()
    fx_rate, fx_snapshot = fx.get_thb_per_usd()
    overrides = pricing.load_pricing_overrides()

    colours_full = tx.get("palette_full", [])
    textures = tx.get("textures", [])

    categories: dict[str, dict[str, Any]] = {}
    for slug, cat in tx.get("categories", {}).items():
        palette_codes = cat.get("palette_codes", [])
        products = [
            _build_sku_payload(p, colours_full, palette_codes, fx_rate, overrides, include_vendor)
            for p in cat.get("products", [])
        ]
        categories[slug] = {
            "slug": slug,
            "name": cat["name"],
            "tagline": cat.get("tagline"),
            "subcategories": cat.get("subcategories", {}),
            "default_textures": cat.get("default_textures", []),
            "products": products,
        }
        # DIY tiles use their own per-family palettes, not palette_full
        if cat.get("diy_palettes"):
            categories[slug]["diy_palettes"] = cat["diy_palettes"]

    return {
        "ok": True,
        "fx": fx_snapshot,
        "textures": textures,
        "categories": categories,
        "meta": {
            "taxonomy_version": tx.get("_meta", {}).get("version"),
            "includes_vendor_code": include_vendor,
        },
    }


# ---------- Routes ----------

@bp.route("/api/order/catalog", methods=["GET"])
@require_auth
def catalog():
    # Never expose vendor_code to non-admin
    include_vendor = g.user.get("role") == "admin"
    return jsonify(_build_catalog(include_vendor=include_vendor))


@bp.route("/admin/api/catalog", methods=["GET"])
@require_role("admin")
def admin_catalog():
    return jsonify(_build_catalog(include_vendor=True))


@bp.route("/api/order/fx", methods=["GET"])
@require_auth
def fx_snapshot():
    rate, snap = fx.get_thb_per_usd()
    return jsonify({"ok": True, "rate_thb_per_usd": rate, "snapshot": snap})


@bp.route("/admin/api/fx/refresh", methods=["POST"])
@require_role("admin")
def fx_refresh():
    fx.reset_cache()
    rate, snap = fx.get_thb_per_usd()
    log.info("FX cache force-refreshed by %s → %.4f (%s)", g.user.get("email"), rate, snap.get("source"))
    return jsonify({"ok": True, "rate_thb_per_usd": rate, "snapshot": snap})
