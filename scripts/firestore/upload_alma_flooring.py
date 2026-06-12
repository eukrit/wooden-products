"""Idempotent uploader for the Alma by Giorio ingestion.

Two phases:
  1. GCS  — mirror data/raw/alma/pdfs/* -> gs://products-wood-assets/alma/docs/
            and    data/raw/alma/images/* -> gs://products-wood-assets/alma/images/
            (skips blobs that already exist)
  2. Firestore (products-wood):
       - vendor `alma-giorio`           via set() (deterministic id)
       - products (models + colour SKUs) via set() (deterministic ids — safe re-run)
       - product_images                 add() only if storage_path not already present

Reads data/incoming/parsed/alma_{vendors,products,product_images}.json
(produced by build_alma_flooring.py).

Usage:
    python scripts/firestore/upload_alma_flooring.py --dry-run
    python scripts/firestore/upload_alma_flooring.py            # full
    python scripts/firestore/upload_alma_flooring.py --skip-gcs # Firestore only
"""
import argparse
import json
import mimetypes
import os
import sys
from datetime import datetime, timezone

from google.cloud import storage

sys.path.insert(0, os.path.dirname(__file__))
from setup_db import get_client  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PARSED = os.path.join(ROOT, "data", "incoming", "parsed")
RAW = os.path.join(ROOT, "data", "raw", "alma")
BUCKET = "products-wood-assets"
PROJECT_ID = "ai-agents-go"

GCS_DIRS = [
    (os.path.join(RAW, "pdfs"), "alma/docs"),
    (os.path.join(RAW, "images"), "alma/images"),
]


def load(name):
    with open(os.path.join(PARSED, name), encoding="utf-8") as f:
        return json.load(f)


def now():
    return datetime.now(timezone.utc)


def get_storage_client():
    cred = os.path.join(
        "C:\\Users\\eukri\\OneDrive\\Documents\\Claude Code",
        "Credentials Claude Code", "ai-agents-go-9b4219be8c01.json")
    if os.path.exists(cred):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred
    return storage.Client(project=PROJECT_ID)  # falls back to ADC otherwise


def upload_gcs(dry):
    sc = get_storage_client()
    bucket = sc.bucket(BUCKET)
    up = skip = 0
    for local_dir, prefix in GCS_DIRS:
        if not os.path.isdir(local_dir):
            print(f"  (no dir {local_dir})")
            continue
        files = sorted(os.listdir(local_dir))
        for fn in files:
            lp = os.path.join(local_dir, fn)
            if not os.path.isfile(lp):
                continue
            blob_path = f"{prefix}/{fn}"
            blob = bucket.blob(blob_path)
            if blob.exists():
                skip += 1
                continue
            up += 1
            if not dry:
                ctype = mimetypes.guess_type(lp)[0] or "application/octet-stream"
                blob.upload_from_filename(lp, content_type=ctype)
        print(f"  {prefix:12} {len(files):4} files  ({up} to upload so far, {skip} present)")
    print(f"GCS: {up} {'would upload' if dry else 'uploaded'}, {skip} already present")
    return up, skip


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-gcs", action="store_true")
    args = ap.parse_args()
    dry = args.dry_run

    print(f"{'DRY RUN — ' if dry else ''}Alma by Giorio -> products-wood\n")

    # --- phase 1: GCS ---
    if not args.skip_gcs:
        print("Phase 1: Cloud Storage")
        upload_gcs(dry)
        print()

    # --- phase 2: Firestore ---
    print("Phase 2: Firestore")
    db = get_client()
    vendors = load("alma_vendors.json")
    products = load("alma_products.json")
    images = load("alma_product_images.json")

    for v in vendors:
        ref = db.collection("vendors").document(v["vendor_id"])
        exists = ref.get().exists
        print(f"  vendor  {v['vendor_id']:<14} {'(exists, overwrite)' if exists else '(new)'}")
        if not dry:
            ref.set(dict(v, created_at=now(), updated_at=now()))

    new_p = upd_p = 0
    for p in products:
        ref = db.collection("products").document(p["product_id"])
        if ref.get().exists:
            upd_p += 1
        else:
            new_p += 1
        if not dry:
            ref.set(dict(p, created_at=now(), updated_at=now()))
    print(f"  products: {new_p} new, {upd_p} overwrite ({len(products)} total)")

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
    print(f"  product_images: {added} added, {skipped} already present ({len(images)} total)")

    print(f"\n{'DRY RUN complete — nothing written.' if dry else 'Upload complete.'}")


if __name__ == "__main__":
    main()
