"""
Re-download ALL PDF/XLSX/XLS files from 4 Slack channels using the Slack API,
then upload to Cloud Storage and create Firestore product_images metadata.

Usage:
    python scripts/firestore/redownload_all_slack.py
"""

import io
import mimetypes
import os
import re
import sys
import time
from datetime import datetime, timezone

# Fix encoding for Windows console
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests

# Add script dir for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
from setup_db import get_client

# ── Config ──────────────────────────────────────────────────────────────────
SLACK_TOKEN = os.environ.get("SLACK_USER_TOKEN", "")

CHANNELS = {
    "C07PGBYGKHQ": "supplier-artificial-wood",
    "C092B3GDMQE": "supplier-ks-wood",
    "C0A776N9FEZ": "vendor-wood-flooring",
    "C07TZM9A1BK": "supplier-flooring-and-decking",
}

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_SLACK_DIR = os.path.join(PROJECT_ROOT, "data", "raw", "slack")

BUCKET_NAME = "products-wood-assets"
PROJECT_ID = "ai-agents-go"
CRED_PATH = os.path.join(
    "C:\\Users\\eukri\\OneDrive\\Documents\\Claude Code",
    "Credentials Claude Code",
    "ai-agents-go-9b4219be8c01.json",
)

# Target extensions
TARGET_EXTENSIONS = (".pdf", ".xlsx", ".xls")

# ── Vendor mapping ──────────────────────────────────────────────────────────
VENDOR_RULES = [
    (r"(?i)(QC68|QC69|NTW|ALusion|WSB)", "ks-wood"),
    (r"(?i)(Aolo|Jackson|co-?extrusion|first.?generation|DIY|ASA)", "anhui-aolo"),
    (r"(?i)Sentai", "sentai"),
    (r"(?i)Sono", "sono"),
    (r"(?i)(Biowood|GRM)", "biowood"),
    (r"(?i)(Flexisand|QO20)", "flexisand"),
    (r"(?i)Consmos", "consmos"),
    (r"(?i)Kentier", "kentier"),
    (r"(?i)Laikeman", "laikeman"),
    (r"(?i)Rainbodeck", "rainbodeck"),
    (r"(?i)(Engineered|Catalog|Vinyl|Laminate)", "elegant-living"),
    (r"(?i)(UV\s*Wall|SPC\s*Floor|PVC\s*Foam|Grille|WPC\s*Decking\s*Price)", "kejie-lidu"),
    (r"[\u4e00-\u9fff]", "chinese-teak-vendor"),
    (r"(?i)Yardcom", "yardcom"),
]


def map_vendor(filename):
    """Map a filename to a vendor folder using regex rules."""
    for pattern, vendor in VENDOR_RULES:
        if re.search(pattern, filename):
            return vendor
    return "misc"


def is_valid_existing_file(filepath):
    """Check if file exists, is >1000 bytes, and is a real PDF (if .pdf)."""
    if not os.path.exists(filepath):
        return False
    size = os.path.getsize(filepath)
    if size <= 1000:
        return False
    if filepath.lower().endswith(".pdf"):
        try:
            with open(filepath, "rb") as f:
                header = f.read(5)
            if header != b"%PDF-":
                return False
        except Exception:
            return False
    return True


# ── Step 1: List and download files from Slack ──────────────────────────────
def list_channel_files(channel_id, channel_name):
    """Get all PDF/XLSX/XLS files from a channel using conversations.history."""
    print(f"\n{'='*60}")
    print(f"Channel: #{channel_name} ({channel_id})")
    print(f"{'='*60}")

    files_found = []
    cursor = None
    page = 0

    while True:
        page += 1
        params = {
            "channel": channel_id,
            "limit": 200,
        }
        if cursor:
            params["cursor"] = cursor

        resp = requests.get(
            "https://slack.com/api/conversations.history",
            headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
            params=params,
        )
        data = resp.json()

        if not data.get("ok"):
            print(f"  ERROR: {data.get('error', 'unknown')}")
            break

        messages = data.get("messages", [])
        print(f"  Page {page}: {len(messages)} messages")

        for msg in messages:
            if "files" in msg:
                for f in msg["files"]:
                    name = f.get("name", "")
                    if any(name.lower().endswith(ext) for ext in TARGET_EXTENSIONS):
                        files_found.append({
                            "name": name,
                            "url_private_download": f.get("url_private_download", ""),
                            "size": f.get("size", 0),
                            "filetype": f.get("filetype", ""),
                            "id": f.get("id", ""),
                            "timestamp": f.get("timestamp", 0),
                        })

        # Check pagination
        meta = data.get("response_metadata", {})
        cursor = meta.get("next_cursor", "")
        if not cursor:
            break
        time.sleep(1.1)  # Rate limit

    print(f"  Found {len(files_found)} target files")
    return files_found


def download_files(channel_name, files):
    """Download files to data/raw/slack/{channel-name}/."""
    dest_dir = os.path.join(RAW_SLACK_DIR, channel_name)
    os.makedirs(dest_dir, exist_ok=True)

    downloaded = 0
    skipped = 0
    failed = 0

    for f in files:
        filepath = os.path.join(dest_dir, f["name"])

        # Skip if already valid
        if is_valid_existing_file(filepath):
            print(f"  SKIP (exists): {f['name']}")
            skipped += 1
            continue

        url = f.get("url_private_download", "")
        if not url:
            print(f"  SKIP (no URL): {f['name']}")
            failed += 1
            continue

        try:
            resp = requests.get(
                url,
                headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
                timeout=60,
            )
            if resp.status_code == 200 and len(resp.content) > 100:
                with open(filepath, "wb") as out:
                    out.write(resp.content)
                print(f"  OK ({len(resp.content):,} bytes): {f['name']}")
                downloaded += 1
            else:
                print(f"  FAIL (HTTP {resp.status_code}, {len(resp.content)} bytes): {f['name']}")
                failed += 1
        except Exception as e:
            print(f"  FAIL ({e}): {f['name']}")
            failed += 1

        time.sleep(0.5)  # Rate limit

    return downloaded, skipped, failed


# ── Step 2: Upload to Cloud Storage + Firestore ────────────────────────────
def upload_to_gcs_and_firestore():
    """Upload all files from data/raw/slack/ to GCS and create Firestore metadata."""
    print(f"\n{'='*60}")
    print("Uploading to Cloud Storage + Firestore")
    print(f"{'='*60}")

    if os.path.exists(CRED_PATH):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CRED_PATH

    from google.cloud import storage as gcs_storage

    storage_client = gcs_storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)

    db = get_client()
    images_col = db.collection("product_images")

    uploaded_count = 0
    skipped_count = 0

    for root, dirs, files in os.walk(RAW_SLACK_DIR):
        for fname in files:
            if not any(fname.lower().endswith(ext) for ext in TARGET_EXTENSIONS):
                continue

            local_path = os.path.join(root, fname)
            file_size = os.path.getsize(local_path)
            if file_size <= 100:
                continue

            # Determine vendor
            vendor = map_vendor(fname)
            blob_path = f"slack/{vendor}/{fname}"

            # Check if already in GCS
            blob = bucket.blob(blob_path)
            if blob.exists():
                print(f"  GCS EXISTS: {blob_path}")
                skipped_count += 1
                continue

            # Upload
            content_type = mimetypes.guess_type(fname)[0] or "application/octet-stream"
            blob.upload_from_filename(local_path, content_type=content_type)

            gs_path = f"gs://{BUCKET_NAME}/{blob_path}"
            print(f"  UPLOADED: {fname} -> {gs_path}")

            # Determine channel from parent directory
            channel_dir = os.path.basename(root)

            # Create Firestore metadata
            doc_data = {
                "file_name": fname,
                "storage_path": gs_path,
                "content_type": content_type,
                "file_size_bytes": file_size,
                "vendor": vendor,
                "source": "slack",
                "source_channel": channel_dir,
                "type": classify_file(fname),
                "description": "",
                "uploaded_at": datetime.now(timezone.utc),
            }
            images_col.add(doc_data)
            uploaded_count += 1

    return uploaded_count, skipped_count


def classify_file(filename):
    """Classify file type for Firestore record."""
    lower = filename.lower()
    if lower.endswith((".xlsx", ".xls")):
        if "price" in lower or "quote" in lower or "quotation" in lower:
            return "price_list"
        return "spreadsheet"
    if lower.endswith(".pdf"):
        if "quote" in lower or "quotation" in lower or "proforma" in lower:
            return "quotation_scan"
        if "catalog" in lower or "catalogue" in lower:
            return "catalog"
        if "spec" in lower or "data" in lower or "technical" in lower:
            return "datasheet"
        return "datasheet"
    return "document"


def print_firestore_counts():
    """Print counts for all Firestore collections."""
    print(f"\n{'='*60}")
    print("Firestore Collection Counts (products-wood)")
    print(f"{'='*60}")

    db = get_client()
    collections = ["vendors", "products", "quotations", "product_images", "categories"]
    for col_name in collections:
        docs = list(db.collection(col_name).stream())
        print(f"  {col_name}: {len(docs)} documents")


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    print("Slack File Re-Downloader + GCS Uploader")
    print(f"Target directory: {RAW_SLACK_DIR}")

    # Phase 1: Download from Slack
    total_downloaded = 0
    total_skipped = 0
    total_failed = 0
    total_found = 0

    for channel_id, channel_name in CHANNELS.items():
        files = list_channel_files(channel_id, channel_name)
        total_found += len(files)
        if files:
            dl, sk, fa = download_files(channel_name, files)
            total_downloaded += dl
            total_skipped += sk
            total_failed += fa

    print(f"\n{'='*60}")
    print("DOWNLOAD SUMMARY")
    print(f"{'='*60}")
    print(f"  Files found:      {total_found}")
    print(f"  Downloaded:       {total_downloaded}")
    print(f"  Skipped (exist):  {total_skipped}")
    print(f"  Failed:           {total_failed}")

    # Phase 2: Upload to GCS + Firestore
    gcs_uploaded, gcs_skipped = upload_to_gcs_and_firestore()

    print(f"\n{'='*60}")
    print("UPLOAD SUMMARY")
    print(f"{'='*60}")
    print(f"  Uploaded to GCS:  {gcs_uploaded}")
    print(f"  Already in GCS:   {gcs_skipped}")

    # Phase 3: Final counts
    print_firestore_counts()


if __name__ == "__main__":
    main()
