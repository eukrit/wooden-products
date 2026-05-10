"""Configurator pricing API — called by the WPC Fence configurator on every
input change to surface indicative retail price to approved architects.

Endpoints (all behind require_approved — guests/pending/rejected get 401/403
so the internal SKU map and FOB cost never leak):

  GET /api/configurator/price        — indicative retail THB
  GET /api/configurator/cost-quote   — wholesale FOB Guangzhou USD + estimated
                                       weight (kg) + CBM (m^3) for the kit.
                                       Powered by the canonical fence
                                       calculator at scripts/fence-calculator/
                                       (see order_portal/fence_calc.py).
"""
from __future__ import annotations

import logging
import math
from typing import Any

from flask import g, jsonify, request

from . import bp, fx, pricing
from .auth import require_approved
from .fence_calc import FenceConfig, calculate as fence_calculate

log = logging.getLogger("order_portal.configurator_api")


_ALLOWED_SERIES = {"premium", "classic", "undecided"}


def _float(val: str | None, default: float, *, lo: float, hi: float) -> float:
    try:
        f = float(val) if val is not None and str(val).strip() else default
    except (TypeError, ValueError):
        f = default
    return max(lo, min(hi, f))


def _int(val: str | None, default: int, *, lo: int, hi: int) -> int:
    try:
        i = int(val) if val is not None and str(val).strip() else default
    except (TypeError, ValueError):
        i = default
    return max(lo, min(hi, i))


@bp.route("/api/configurator/price", methods=["GET"])
@require_approved
def configurator_price():
    """Return indicative retail THB for the current configurator spec."""
    args = request.args
    series = str(args.get("series", "premium")).lower().strip()
    if series not in _ALLOWED_SERIES:
        return jsonify({"ok": False, "error": "invalid_series"}), 400

    spec = {
        "series": series,
        "bay_m": _float(args.get("bayWidth"), 2.0, lo=0.5, hi=4.0),
        "height_m": _float(args.get("height"), 2.0, lo=0.6, hi=3.0),
        "gap_cm": _float(args.get("boardGap"), 0.0, lo=0.0, hi=10.0),
        "fence_run_m": _float(args.get("fenceRun"), 48.0, lo=0.0, hi=10000.0),
        "single_gates": _int(args.get("singleGates"), 0, lo=0, hi=50),
        "double_gates": _int(args.get("doubleGates"), 0, lo=0, hi=50),
    }

    fx_rate, fx_snapshot = fx.get_thb_per_usd()
    result: dict[str, Any] = pricing.fence_retail_thb(spec, fx_rate=fx_rate)

    return jsonify({
        "ok": True,
        "retail_thb": result["retail_thb"],
        "breakdown": result["breakdown"],
        "fx": {
            "thb_per_usd": fx_rate,
            "source": fx_snapshot.get("source"),
        },
        "warnings": result.get("warnings", []),
        "user": {
            "display_name": g.user.get("display_name"),
            "role": g.user.get("role"),
        },
    })


@bp.route("/api/configurator/cost-quote", methods=["GET"])
@require_approved
def configurator_cost_quote():
    """Return wholesale FOB Guangzhou cost + estimated shipping weight/CBM
    for the current configurator spec.

    Inputs (all optional, validated):
      bayWidth     m   default 2.0   range [0.5, 4.0]
      height       m   default 2.0   range [0.6, 3.0]
      fenceRun     m   default 48    range [1, 10000]
      singleGates  int default 0     range [0, 50]
      doubleGates  int default 0     range [0, 50]
      includeShipping bool default true ($515 local-to-Guangzhou trucking)

    The calculator's bay model is square: bays = ceil(fenceRun / bayWidth).
    Each gate replaces one bay's worth of fencing in the run, so we subtract
    gate-equivalent run length before computing bays. (1 single gate = 1.2m,
    1 double gate = 2.4m, matching the configurator's existing BOM math.)

    Posts auto-pick: 2.0m if height <= 2000mm else 3.0m.
    """
    args = request.args
    bay_width_m = _float(args.get("bayWidth"), 2.0, lo=0.5, hi=4.0)
    height_m = _float(args.get("height"), 2.0, lo=0.6, hi=3.0)
    fence_run_m = _float(args.get("fenceRun"), 48.0, lo=1.0, hi=10000.0)
    single_gates = _int(args.get("singleGates"), 0, lo=0, hi=50)
    double_gates = _int(args.get("doubleGates"), 0, lo=0, hi=50)
    include_shipping = str(args.get("includeShipping", "true")).lower() not in ("0", "false", "no")

    gate_run_m = single_gates * 1.2 + double_gates * 2.4
    fence_only_run_m = max(0.0, fence_run_m - gate_run_m)
    if fence_only_run_m <= 0:
        return jsonify({
            "ok": False,
            "error": "fence_run_too_short",
            "message": "Fence run is consumed entirely by gates. Increase fenceRun or reduce gate count.",
        }), 400

    bays = max(1, math.ceil(fence_only_run_m / bay_width_m))
    bay_height_mm = int(round(height_m * 1000))

    try:
        cfg = FenceConfig(
            bays=bays,
            bay_width_m=bay_width_m,
            bay_height_mm=bay_height_mm,
            gates=single_gates + double_gates,
        )
    except ValueError as ve:
        log.warning("cost-quote rejected config: %s", ve)
        return jsonify({"ok": False, "error": "invalid_config", "message": str(ve)}), 400

    quote = fence_calculate(cfg, include_shipping=include_shipping, include_shipping_estimate=True)

    return jsonify({
        "ok": True,
        "fob_guangzhou_usd": {
            "subtotal": quote.subtotal_usd,
            "trucking_to_guangzhou": quote.shipping_usd,
            "total": quote.total_usd,
        },
        "kit": {
            "bays": cfg.bays,
            "bay_width_m": cfg.bay_width_m,
            "bay_height_mm": cfg.bay_height_mm,
            "post_length_m": cfg.post_length_m,
            "boards_per_bay": quote.boards_per_bay(),
            "posts": cfg.bays + 1,
            "gates": cfg.gates,
        },
        "shipping_estimate": {
            "weight_kg": quote.shipping_estimate.weight_kg if quote.shipping_estimate else None,
            "cbm_m3": quote.shipping_estimate.cbm_m3 if quote.shipping_estimate else None,
            "notes": quote.shipping_estimate.notes if quote.shipping_estimate else [],
        },
        "items": [
            {"name": it.name, "qty": it.qty, "unit_price_usd": it.unit_price_usd, "total_usd": it.total_usd}
            for it in quote.items
        ],
        "warnings": list(quote.warnings),
        "user": {
            "display_name": g.user.get("display_name"),
            "role": g.user.get("role"),
        },
    })
