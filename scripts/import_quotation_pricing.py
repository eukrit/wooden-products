"""Import priced line items from data/parsed/quotations.json into
Firestore `catalog_pricing/{sku}` so they're available as admin overrides
to the Order Portal's landed-cost computation.

Converts each source currency (USD, CNY, THB) to THB using the same
frankfurter.app FX source the portal uses, then applies the config
`fx_buffer_pct` so the import matches what the portal would compute
for a fresh ECB hit.

Default: DRY RUN. Pass --write to actually upsert to Firestore.

Usage:
    python scripts/import_quotation_pricing.py              # dry-run
    python scripts/import_quotation_pricing.py --write      # push to Firestore
    python scripts/import_quotation_pricing.py --write --skus leo-nature-teak,qihome-cherry

Notes:
  - The imported SKUs (leo-nature-teak, qihome-cherry, cn-*, sentai-*, ks-wood/wsb81)
    are NOT currently in data/catalog/leka-taxonomy.json. Adding them to
    catalog_pricing makes them usable as overrides IF they're added to
    the taxonomy. Until then, this only prepopulates the override store
    for future use — the order portal's /api/order/catalog won't surface
    them because that endpoint iterates the taxonomy.
  - The quotation `unit_price` is assumed to be a per-piece or per-sqm
    price depending on the vendor's convention — check each quote.
    For now we store as `unit_price_thb` (full retail) rather than
    `landed_thb_per_m` so the portal's default_markup doesn't inflate
    a quoted-and-already-final price. Admin can edit.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

import requests

log = logging.getLogger("import_quotation_pricing")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUOTATIONS = os.path.join(ROOT, "data", "parsed", "quotations.json")
CONFIG = os.path.join(ROOT, "data", "catalog", "order-portal-config.json")


# ---------- FX ----------

def load_fx_config() -> dict[str, Any]:
    with open(CONFIG, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    return cfg["pricing"]


def live_fx(base: str, target: str = "THB", cfg: dict[str, Any] | None = None) -> tuple[float, str]:
    """Returns (rate, source). source ∈ 'frankfurter' | 'fallback'."""
    cfg = cfg or load_fx_config()
    if base == "THB":
        return 1.0, "identity"
    try:
        url = cfg.get("fx_api_url", "https://api.frankfurter.app/latest")
        r = requests.get(url, params={"from": base, "to": target}, timeout=8)
        r.raise_for_status()
        ecb_mid = float(r.json()["rates"][target])
        buffered = ecb_mid * (1 + float(cfg.get("fx_buffer_pct", 3.0)) / 100.0)
        return round(buffered, 4), "frankfurter"
    except Exception as exc:
        log.warning("FX %s→%s live fetch failed (%s); using fallback", base, target, exc)
        if base == "USD":
            return float(cfg["fx_thb_per_usd_fallback"]), "fallback"
        # No fallback for CNY / EUR — re-raise
        raise


# ---------- Extraction ----------

def extract_priced_lines(quotations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for q in quotations:
        currency = (q.get("currency") or "").upper()
        for it in q.get("items") or []:
            unit = it.get("unit_price")
            if not unit or float(unit) <= 0:
                continue
            sku = it.get("sku") or it.get("product_id") or it.get("code")
            if not sku:
                continue
            out.append({
                "sku": sku,
                "name": it.get("product_name") or sku,
                "vendor_id": q.get("vendor_id"),
                "quote_id": q.get("quotation_id"),
                "quote_date": q.get("quote_date"),
                "source_currency": currency,
                "source_unit_price": float(unit),
                "unit_label": it.get("unit") or q.get("delivery_terms") or "",
            })
    return out


def convert_to_thb(row: dict[str, Any], fx_cache: dict[str, tuple[float, str]]) -> dict[str, Any]:
    cur = row["source_currency"]
    if cur not in fx_cache:
        fx_cache[cur] = live_fx(cur)
    rate, source = fx_cache[cur]
    thb = round(row["source_unit_price"] * rate, 2)
    return dict(row, thb_unit_price=thb, fx_rate_used=rate, fx_source=source)


# ---------- Write ----------

def write_to_firestore(rows: list[dict[str, Any]], actor: str = "import_script") -> None:
    # Lazy import to keep dry-run dep-free
    from google.cloud import firestore  # type: ignore

    project_id = os.environ.get("GCP_PROJECT_ID", "ai-agents-go")
    with open(CONFIG, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    db = firestore.Client(project=project_id, database=cfg["firestore"]["database_id"])

    now = datetime.now(timezone.utc)
    for row in rows:
        doc = {
            "sku": row["sku"],
            "unit_price_thb": row["thb_unit_price"],
            "source": f"quotation:{row['quote_id']}",
            "source_currency": row["source_currency"],
            "source_unit_price": row["source_unit_price"],
            "fx_rate_used": row["fx_rate_used"],
            "fx_source": row["fx_source"],
            "vendor_id": row["vendor_id"],
            "product_name": row["name"],
            "unit_label": row["unit_label"],
            "quote_date": row["quote_date"],
            "updated_by": actor,
            "updated_at": now,
        }
        db.collection("catalog_pricing").document(row["sku"]).set(doc, merge=True)
        log.info("  wrote catalog_pricing/%s (%s THB from %s %s)",
                 row["sku"], row["thb_unit_price"], row["source_unit_price"], row["source_currency"])


# ---------- CLI ----------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--write", action="store_true",
                    help="Actually upsert to Firestore. Default is dry-run.")
    ap.add_argument("--skus", default="",
                    help="Comma-separated SKU whitelist (default: all priced lines).")
    ap.add_argument("--actor", default="import_script",
                    help="Value for updated_by field in Firestore docs.")
    args = ap.parse_args()

    with open(QUOTATIONS, "r", encoding="utf-8") as fh:
        quotations = json.load(fh)
    priced = extract_priced_lines(quotations)
    log.info("Found %d priced line items across %d quotations", len(priced), len(quotations))

    whitelist = {s.strip() for s in args.skus.split(",") if s.strip()}
    if whitelist:
        before = len(priced)
        priced = [r for r in priced if r["sku"] in whitelist]
        log.info("Filtered by --skus: %d -> %d", before, len(priced))

    fx_cache: dict[str, tuple[float, str]] = {}
    converted = [convert_to_thb(r, fx_cache) for r in priced]

    print()
    print(f"{'SKU':<32} {'Vendor':<24} {'Source':>14} {'THB':>10}  Name")
    print(f"{'-' * 32} {'-' * 24} {'-' * 14} {'-' * 10}  {'-' * 40}")
    for r in converted:
        src = f"{r['source_unit_price']:.2f} {r['source_currency']}"
        print(f"{r['sku']:<32} {r['vendor_id']:<24} {src:>14} {r['thb_unit_price']:>10.2f}  {r['name']}")

    print()
    print("FX used:")
    for cur, (rate, src) in fx_cache.items():
        print(f"  1 {cur} = {rate:.4f} THB  ({src})")

    if args.write:
        print("\n==> Writing to Firestore catalog_pricing/{sku} (merge=True)")
        try:
            write_to_firestore(converted, actor=args.actor)
            print(f"Wrote {len(converted)} docs.")
        except Exception as exc:
            log.exception("Write failed")
            print(f"Write FAILED: {exc}")
            return 1
    else:
        print(f"\n==> DRY RUN — no changes made. Pass --write to push to Firestore.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
