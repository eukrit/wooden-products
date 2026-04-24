"""Backfill users/{uid}.status for existing order-portal users.

Before the architect flow shipped, the order portal only had staff users
(admin + external_sales) and their docs had no `status` field. This script
adds `status='approved'` to any user doc missing the field so existing
staff don't get locked out by `require_approved`.

Run:
    GOOGLE_APPLICATION_CREDENTIALS=... python scripts/firestore/backfill_user_status.py
    python scripts/firestore/backfill_user_status.py --dry-run

Idempotent. Only writes docs where `status` is missing.
"""
from __future__ import annotations

import argparse
import logging
import sys

from google.cloud import firestore  # type: ignore

log = logging.getLogger("backfill_user_status")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="ai-agents-go")
    parser.add_argument("--database", default="products-wood")
    parser.add_argument("--dry-run", action="store_true", help="Print actions, don't write")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    db = firestore.Client(project=args.project, database=args.database)
    users = db.collection("users")

    seen = 0
    updated = 0
    skipped = 0
    for snap in users.stream():
        seen += 1
        data = snap.to_dict() or {}
        if "status" in data and data["status"]:
            skipped += 1
            continue
        log.info(
            "Would set status=approved on users/%s (email=%s, role=%s)",
            snap.id, data.get("email", ""), data.get("role", ""),
        )
        if not args.dry_run:
            users.document(snap.id).update({"status": "approved"})
            updated += 1

    log.info("Done. seen=%d updated=%d already_set=%d dry_run=%s",
             seen, updated, skipped, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
