"""
Upload product images and attachments to Cloud Storage
and create metadata records in Firestore.

Usage:
    python scripts/firestore/upload_images.py
    python scripts/firestore/upload_images.py --path data/images/
"""

import argparse
import mimetypes
import os
import sys
from datetime import datetime, timezone

from google.cloud import storage

sys.path.insert(0, os.path.dirname(__file__))
from setup_db import get_client

BUCKET_NAME = "products-wood-assets"
PROJECT_ID = "ai-agents-go"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
IMAGES_DIR = os.path.join(PROJECT_ROOT, "data", "images")


def get_storage_client():
    cred_path = os.path.join(
        "C:\\Users\\eukri\\OneDrive\\Documents\\Claude Code",
        "Credentials Claude Code",
        "ai-agents-go-4c81b70995db.json",
    )
    if os.path.exists(cred_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path
    return storage.Client(project=PROJECT_ID)


def upload_file(storage_client, local_path, dest_folder=""):
    """Upload a file to Cloud Storage and return the gs:// path."""
    bucket = storage_client.bucket(BUCKET_NAME)
    filename = os.path.basename(local_path)
    blob_path = f"{dest_folder}/{filename}" if dest_folder else filename
    blob = bucket.blob(blob_path)

    content_type = mimetypes.guess_type(local_path)[0] or "application/octet-stream"
    blob.upload_from_filename(local_path, content_type=content_type)

    gs_path = f"gs://{BUCKET_NAME}/{blob_path}"
    print(f"  Uploaded: {filename} -> {gs_path}")
    return gs_path, content_type, os.path.getsize(local_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=IMAGES_DIR, help="Directory of files to upload")
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Directory not found: {args.path}")
        sys.exit(1)

    storage_client = get_storage_client()
    db = get_client()
    images_col = db.collection("product_images")

    count = 0
    for root, dirs, files in os.walk(args.path):
        for fname in files:
            local_path = os.path.join(root, fname)
            rel_folder = os.path.relpath(root, args.path).replace("\\", "/")
            if rel_folder == ".":
                rel_folder = ""

            gs_path, content_type, file_size = upload_file(
                storage_client, local_path, dest_folder=rel_folder
            )

            # Create Firestore metadata record
            images_col.add({
                "file_name": fname,
                "storage_path": gs_path,
                "content_type": content_type,
                "file_size_bytes": file_size,
                "description": "",
                "type": classify_file(fname, content_type),
                "source": "local_upload",
                "uploaded_at": datetime.now(timezone.utc),
            })
            count += 1

    print(f"\nTotal files uploaded: {count}")


def classify_file(filename, content_type):
    """Classify file type for Firestore record."""
    lower = filename.lower()
    if content_type and content_type.startswith("image/"):
        return "product_photo"
    if lower.endswith(".pdf"):
        if "quote" in lower or "quotation" in lower:
            return "quotation_scan"
        if "catalog" in lower or "catalogue" in lower:
            return "catalog"
        return "datasheet"
    if "catalog" in lower or "catalogue" in lower:
        return "catalog"
    return "document"


if __name__ == "__main__":
    main()
