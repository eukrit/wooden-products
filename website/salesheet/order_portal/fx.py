"""Live FX rates via frankfurter.app + configurable exchange buffer.

Frankfurter publishes ECB mid-market rates — free, no API key, JSON.
ECB mid is below the rate a Thai bank will charge on a TT Selling
transaction, so we add `fx_buffer_pct` (default 3%) to approximate the
real cost-to-import FX. Final rate = ecb_mid * (1 + buffer_pct / 100).

Usage:
    rate, snapshot = fx.get_thb_per_usd()
    # snapshot is dict {rate, source, ecb_mid?, buffer_pct, fetched_at}
    # source ∈ {"frankfurter", "cache", "fallback_api_error"}
"""
from __future__ import annotations

import logging
import time
from typing import Any

import requests

from . import config as cfg

log = logging.getLogger("order_portal.fx")

_CACHE: dict[str, Any] = {"rate": None, "fetched_at": 0, "source": None, "ecb_mid": None}


def _apply_buffer(ecb_mid: float, buffer_pct: float) -> float:
    return round(ecb_mid * (1 + buffer_pct / 100.0), 4)


def get_thb_per_usd() -> tuple[float, dict[str, Any]]:
    """Returns (rate_with_buffer, snapshot)."""
    pricing = cfg.pricing()
    ttl = int(pricing.get("fx_cache_ttl_s", 3600))
    buffer_pct = float(pricing.get("fx_buffer_pct", 3.0))
    now = time.time()

    if _CACHE["rate"] and now - _CACHE["fetched_at"] < ttl:
        return _CACHE["rate"], {
            "rate": _CACHE["rate"],
            "source": "cache",
            "ecb_mid": _CACHE["ecb_mid"],
            "buffer_pct": buffer_pct,
            "fetched_at": _CACHE["fetched_at"],
        }

    api_url = pricing.get("fx_api_url", "https://api.frankfurter.app/latest")
    try:
        r = requests.get(api_url, params={"from": "USD", "to": "THB"}, timeout=6)
        r.raise_for_status()
        body = r.json()
        ecb_mid = float(body["rates"]["THB"])
        rate = _apply_buffer(ecb_mid, buffer_pct)
        _CACHE.update(rate=rate, fetched_at=now, source="frankfurter", ecb_mid=ecb_mid)
        log.info("FX live: USD→THB ecb_mid=%.4f buffered=%.4f (+%.1f%%)", ecb_mid, rate, buffer_pct)
        return rate, {
            "rate": rate,
            "source": "frankfurter",
            "ecb_mid": ecb_mid,
            "buffer_pct": buffer_pct,
            "fetched_at": now,
        }
    except Exception as exc:
        fallback = float(pricing["fx_thb_per_usd_fallback"])
        log.warning("FX live fetch failed (%s); using fallback %.2f", exc, fallback)
        return fallback, {
            "rate": fallback,
            "source": "fallback_api_error",
            "ecb_mid": None,
            "buffer_pct": buffer_pct,
            "fetched_at": now,
        }


def reset_cache() -> None:
    """For tests + admin 'refresh FX now' endpoint."""
    _CACHE.update(rate=None, fetched_at=0, source=None, ecb_mid=None)
