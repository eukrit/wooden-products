"""Firestore client singleton for the products-wood database.

Uses Application Default Credentials — on Cloud Run, this is the service
account attached to salesheet-leka. On local dev, set
GOOGLE_APPLICATION_CREDENTIALS to the service-account JSON path.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

from . import config as cfg

log = logging.getLogger("order_portal.firestore")


@lru_cache(maxsize=1)
def get_db():
    """Return a google.cloud.firestore.Client for the products-wood db.

    Lazy-imports google-cloud-firestore so tests can stub it without
    pulling the full dependency.
    """
    from google.cloud import firestore  # noqa: WPS433

    project_id = os.environ.get("GCP_PROJECT_ID", "ai-agents-go")
    database_id = cfg.firestore()["database_id"]
    log.info("Connecting to Firestore project=%s database=%s", project_id, database_id)
    return firestore.Client(project=project_id, database=database_id)
