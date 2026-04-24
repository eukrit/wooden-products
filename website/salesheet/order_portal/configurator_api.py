"""Configurator pricing API — called by the WPC Fence configurator on every
input change to surface indicative retail price to approved architects.

  GET /api/configurator/price?series=premium&bayWidth=2.0&boardGap=0
                              &height=2.0&colorCode=LK-05&fenceRun=48
                              &singleGates=0&doubleGates=0

Behind require_approved — unapproved or guest requests get 401/403 so the
internal SKU map never leaks.
"""
from __future__ import annotations

import logging
from typing import Any

from flask import g, jsonify, request

from . import bp, fx, pricing
from .auth import require_approved

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
