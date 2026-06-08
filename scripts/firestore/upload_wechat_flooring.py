"""
Idempotent uploader for the WeChat wooden-flooring handoff.

Reads data/incoming/parsed/{vendors,vendor_updates,products,product_images}.json and
writes to Firestore `products-wood`:
  - new vendors (bimei, visconti) via set() with deterministic ids
  - elegant-living vendor: MERGE (append traceability note, keep existing fields)
  - products via set() with deterministic ids (safe to re-run)
  - product_images: add() only if a record with the same storage_path doesn't exist

Usage:
    python scripts/firestore/upload_wechat_flooring.py --dry-run
    python scripts/firestore/upload_wechat_flooring.py
"""
import argparse, json, os, sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from setup_db import get_client

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PARSED = os.path.join(ROOT, "data", "incoming", "parsed")


def load(name):
    with open(os.path.join(PARSED, name), encoding="utf-8") as f:
        return json.load(f)


def now():
    return datetime.now(timezone.utc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dry = args.dry_run
    db = get_client()

    vendors = load("vendors.json")
    vendor_updates = load("vendor_updates.json")
    products = load("products.json")
    images = load("product_images.json")

    print(f"{'DRY RUN — ' if dry else ''}Uploading to products-wood\n")

    # --- new vendors ---
    for v in vendors:
        ref = db.collection("vendors").document(v["vendor_id"])
        exists = ref.get().exists
        print(f"vendor  {v['vendor_id']:<16} {'(exists, will overwrite)' if exists else '(new)'}")
        if not dry:
            v = dict(v, created_at=now(), updated_at=now())
            ref.set(v)

    # --- vendor merges (elegant-living) ---
    for u in vendor_updates:
        vid = u["vendor_id"]
        ref = db.collection("vendors").document(vid)
        snap = ref.get()
        if not snap.exists:
            print(f"merge   {vid:<16} SKIP (vendor not found)")
            continue
        cur = snap.to_dict()
        patch = {}
        append = u.get("notes_append", "")
        if append and append.strip() not in (cur.get("notes") or ""):
            patch["notes"] = (cur.get("notes") or "") + append
        if "engineered_flooring" not in (cur.get("products_supplied") or []):
            patch["products_supplied"] = list(cur.get("products_supplied") or []) + ["engineered_flooring"]
        if patch:
            patch["updated_at"] = now()
            print(f"merge   {vid:<16} fields: {list(patch.keys())}")
            if not dry:
                ref.set(patch, merge=True)
        else:
            print(f"merge   {vid:<16} no change needed")

    # --- products ---
    new_p = upd_p = 0
    for p in products:
        ref = db.collection("products").document(p["product_id"])
        if ref.get().exists:
            upd_p += 1
        else:
            new_p += 1
        if not dry:
            ref.set(dict(p, created_at=now(), updated_at=now()))
    print(f"\nproducts: {new_p} new, {upd_p} overwrite ({len(products)} total)")

    # --- product_images (dedupe by storage_path) ---
    col = db.collection("product_images")
    added = skipped = 0
    for img in images:
        q = list(col.where("storage_path", "==", img["storage_path"]).limit(1).stream())
        if q:
            skipped += 1
            continue
        added += 1
        if not dry:
            col.add(dict(img, uploaded_at=now()))
    print(f"product_images: {added} added, {skipped} already present")

    print(f"\n{'DRY RUN complete — nothing written.' if dry else 'Upload complete.'}")


if __name__ == "__main__":
    main()
