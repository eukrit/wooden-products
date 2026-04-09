"""
Upload parsed wood product data to Firestore 'products-wood' database.

Reads JSON files from data/parsed/ and uploads to appropriate collections.

Usage:
    python scripts/firestore/upload_data.py
    python scripts/firestore/upload_data.py --collection vendors
    python scripts/firestore/upload_data.py --file data/parsed/vendors.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from setup_db import get_client

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PARSED_DIR = os.path.join(PROJECT_ROOT, "data", "parsed")


def load_json(filepath):
    """Load JSON data from file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def upload_vendors(db, vendors):
    """Upload vendor records."""
    col = db.collection("vendors")
    count = 0
    for v in vendors:
        v["created_at"] = datetime.now(timezone.utc)
        v["updated_at"] = datetime.now(timezone.utc)
        if "vendor_id" in v and v["vendor_id"]:
            col.document(v["vendor_id"]).set(v)
        else:
            col.add(v)
        count += 1
    print(f"  Uploaded {count} vendors")
    return count


def upload_products(db, products):
    """Upload product records."""
    col = db.collection("products")
    count = 0
    for p in products:
        p["created_at"] = datetime.now(timezone.utc)
        p["updated_at"] = datetime.now(timezone.utc)
        if "product_id" in p and p["product_id"]:
            col.document(p["product_id"]).set(p)
        else:
            col.add(p)
        count += 1
    print(f"  Uploaded {count} products")
    return count


def upload_quotations(db, quotations):
    """Upload quotation records."""
    col = db.collection("quotations")
    count = 0
    for q in quotations:
        q["created_at"] = datetime.now(timezone.utc)
        q["updated_at"] = datetime.now(timezone.utc)
        if "quotation_id" in q and q["quotation_id"]:
            col.document(q["quotation_id"]).set(q)
        else:
            col.add(q)
        count += 1
    print(f"  Uploaded {count} quotations")
    return count


def upload_images(db, images):
    """Upload image metadata records."""
    col = db.collection("product_images")
    count = 0
    for img in images:
        img["uploaded_at"] = datetime.now(timezone.utc)
        col.add(img)
        count += 1
    print(f"  Uploaded {count} image records")
    return count


UPLOADERS = {
    "vendors": upload_vendors,
    "products": upload_products,
    "quotations": upload_quotations,
    "product_images": upload_images,
}


def main():
    parser = argparse.ArgumentParser(description="Upload data to Firestore products-wood")
    parser.add_argument("--collection", choices=list(UPLOADERS.keys()), help="Upload specific collection")
    parser.add_argument("--file", help="Upload specific JSON file")
    args = parser.parse_args()

    db = get_client()
    total = 0

    if args.file:
        data = load_json(args.file)
        collection = os.path.splitext(os.path.basename(args.file))[0]
        if collection in UPLOADERS:
            print(f"Uploading {collection} from {args.file}...")
            total += UPLOADERS[collection](db, data)
        else:
            print(f"Unknown collection: {collection}")
            sys.exit(1)
    else:
        for collection, uploader in UPLOADERS.items():
            if args.collection and args.collection != collection:
                continue
            filepath = os.path.join(PARSED_DIR, f"{collection}.json")
            if os.path.exists(filepath):
                data = load_json(filepath)
                print(f"Uploading {collection}...")
                total += uploader(db, data)
            else:
                print(f"  No data file: {filepath}")

    print(f"\nTotal records uploaded: {total}")


if __name__ == "__main__":
    main()
