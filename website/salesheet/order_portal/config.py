"""Load the frozen order-portal config from data/catalog/order-portal-config.json.

Read once at module import, cached in memory. The file is copied into the
Docker image by cloudbuild.yaml (pre-step copies data/catalog/*.json into
website/salesheet/data/catalog/ before `docker build`).
"""
from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Any

log = logging.getLogger("order_portal.config")


def _candidate_paths() -> list[str]:
    """Return candidate paths in priority order.

    - Cloud Run: /app/data/catalog/order-portal-config.json (Dockerfile COPY target)
    - Local dev: repo-relative path from this file
    """
    here = os.path.dirname(os.path.abspath(__file__))
    return [
        os.path.join("/app", "data", "catalog", "order-portal-config.json"),
        os.path.abspath(os.path.join(here, "..", "data", "catalog", "order-portal-config.json")),
        os.path.abspath(os.path.join(here, "..", "..", "..", "data", "catalog", "order-portal-config.json")),
    ]


@lru_cache(maxsize=1)
def load() -> dict[str, Any]:
    """Return the frozen config. Raises if not found (fail loud at startup)."""
    for path in _candidate_paths():
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                cfg = json.load(fh)
            log.info("Loaded order-portal-config v%s from %s", cfg["_meta"]["version"], path)
            return cfg
    raise FileNotFoundError(
        "order-portal-config.json not found. Checked: " + ", ".join(_candidate_paths())
    )


# Convenience accessors — each returns a sub-section of the config.
def order_number() -> dict: return load()["order_number"]
def slack() -> dict: return load()["slack"]
def xero() -> dict: return load()["xero"]
def auth() -> dict: return load()["auth"]
def pricing() -> dict: return load()["pricing"]
def firestore() -> dict: return load()["firestore"]
def cloud_run() -> dict: return load()["cloud_run"]
