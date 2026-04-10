"""
Download all files from Slack wood product channels,
upload to Cloud Storage, and create Firestore metadata.
"""
import os
import sys
import json
import requests
import time

sys.path.insert(0, os.path.dirname(__file__))
from setup_db import get_client
from google.cloud import storage
from datetime import datetime, timezone

SLACK_TOKEN = os.environ.get("SLACK_USER_TOKEN", "")
BUCKET_NAME = "products-wood-assets"
PROJECT_ID = "ai-agents-go"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DOWNLOAD_DIR = os.path.join(PROJECT_ROOT, "data", "raw", "slack")

# All files from the 3 channels
SLACK_FILES = [
    # Channel: #supplier-artificial-wood
    {"id": "F08JH629TTJ", "name": "QC6800211_GO_Corporation.pdf", "vendor": "sksdecor", "channel": "supplier-artificial-wood"},
    {"id": "F08NVJD7849", "name": "QC6800211_GO_Corporation_Rev.pdf", "vendor": "sksdecor", "channel": "supplier-artificial-wood"},
    {"id": "F0AHDE0F96Z", "name": "Sono_Catalogue_Khun_X.pdf", "vendor": "sono", "channel": "supplier-artificial-wood"},
    {"id": "F0AEWJ53E57", "name": "VIROBUILD_CATALOGUE_2024.pdf", "vendor": "virobuild", "channel": "supplier-artificial-wood"},
    {"id": "F0A1MQU5J22", "name": "Sono_Catalogue_Final_2.pdf", "vendor": "sono", "channel": "supplier-artificial-wood"},
    {"id": "F08HHJYKEQ6", "name": "E-Catalog_RainbodeckTH_2025.pdf", "vendor": "rainbodeck", "channel": "supplier-artificial-wood"},
    {"id": "F09N0LQKP0D", "name": "SENTAI_WPC_PRICE_2025.pdf", "vendor": "sentai", "channel": "supplier-artificial-wood"},
    {"id": "F09UMQQM3E3", "name": "PI_For_NIWAT_SAMRIT_Aolo.pdf", "vendor": "anhui-aolo", "channel": "supplier-artificial-wood"},
    {"id": "F09U5KG9872", "name": "First_generation_catalog_Jackson_251108.pdf", "vendor": "anhui-aolo", "channel": "supplier-artificial-wood"},
    {"id": "F09C759KE8M", "name": "First_generation_catalog_Jackson_250801.pdf", "vendor": "anhui-aolo", "channel": "supplier-artificial-wood"},
    {"id": "F09TQ7L5073", "name": "DIY_CATALOG_Aolo.pdf", "vendor": "anhui-aolo", "channel": "supplier-artificial-wood"},
    {"id": "F09C8G8S350", "name": "Co-extrusion_catalog_Jackson_Aug.pdf", "vendor": "anhui-aolo", "channel": "supplier-artificial-wood"},
    {"id": "F09SVSM971V", "name": "Co-extrusion_catalog_Jackson_Nov.pdf", "vendor": "anhui-aolo", "channel": "supplier-artificial-wood"},
    {"id": "F09TET3C6TE", "name": "AOLO_ASA.pdf", "vendor": "anhui-aolo", "channel": "supplier-artificial-wood"},
    # Channel: #supplier-ks-wood (PDFs)
    {"id": "F0AS4JHJZB3", "name": "QC6900296_WSB81.pdf", "vendor": "ks-wood", "channel": "supplier-ks-wood"},
    {"id": "F0AQ36B7T4N", "name": "QC6900267_GO_Corporation.pdf", "vendor": "ks-wood", "channel": "supplier-ks-wood"},
    {"id": "F09RAMV16E9", "name": "QC6800869_GO_Corporation.pdf", "vendor": "ks-wood", "channel": "supplier-ks-wood"},
    {"id": "F09HENFSG9H", "name": "QC6800786_GO_Corporation.pdf", "vendor": "ks-wood", "channel": "supplier-ks-wood"},
    {"id": "F09USFTLD3P", "name": "QC6800936_GO_Corporation.pdf", "vendor": "ks-wood", "channel": "supplier-ks-wood"},
    {"id": "F09KC02URL7", "name": "QC6800814_GO_Corporation.pdf", "vendor": "ks-wood", "channel": "supplier-ks-wood"},
    {"id": "F0955SCMG4D", "name": "QC6800560_GO_Corporation.pdf", "vendor": "ks-wood", "channel": "supplier-ks-wood"},
    {"id": "F0951J1BFDZ", "name": "QC6800561_Rev1_installation.pdf", "vendor": "ks-wood", "channel": "supplier-ks-wood"},
    {"id": "F0953KJTP9C", "name": "QC6800561_GO_Corporation.pdf", "vendor": "ks-wood", "channel": "supplier-ks-wood"},
    {"id": "F095V4X1PH6", "name": "QC6800560_Rev1_product.pdf", "vendor": "ks-wood", "channel": "supplier-ks-wood"},
    # Channel: #supplier-ks-wood (Spreadsheets)
    {"id": "F09J81KU274", "name": "NTW_WCL_WCE_CL2_CL3.xls", "vendor": "ks-wood", "channel": "supplier-ks-wood"},
    {"id": "F09JLRWTE01", "name": "List_Price_NTW_UHL.xlsx", "vendor": "ks-wood", "channel": "supplier-ks-wood"},
    {"id": "F09J81LAZ2N", "name": "Price_list_NTW_Decking.xls", "vendor": "ks-wood", "channel": "supplier-ks-wood"},
    {"id": "F09J5UNTYGN", "name": "Price_End_Cap_ALusions.xlsx", "vendor": "ks-wood", "channel": "supplier-ks-wood"},
    {"id": "F09JLRVEBBK", "name": "Price_List_ALusions_old.xlsx", "vendor": "ks-wood", "channel": "supplier-ks-wood"},
    # Channel: #vendor-wood-flooring
    {"id": "F0AQ579TC7K", "name": "Bimei_flooring_Italy_parquet.pdf", "vendor": "chinese-teak-vendor", "channel": "vendor-wood-flooring"},
    {"id": "F0APVRP36UC", "name": "2026_Main_product_price_list.pdf", "vendor": "chinese-teak-vendor", "channel": "vendor-wood-flooring"},
    {"id": "F0A7AK8SUAW", "name": "ENGINEERED_CATALOG.pdf", "vendor": "elegant-living", "channel": "vendor-wood-flooring"},
    {"id": "F0A7AK6FXUJ", "name": "Laminate_Catalogue.pdf", "vendor": "elegant-living", "channel": "vendor-wood-flooring"},
    {"id": "F0A7E7GR2RJ", "name": "Catalog_2019_Vinyl.pdf", "vendor": "elegant-living", "channel": "vendor-wood-flooring"},
    {"id": "F0A9Z68H8G1", "name": "Engineered_flooring_proposals_20260108.pdf", "vendor": "leo-nature", "channel": "vendor-wood-flooring"},
    {"id": "F0APC0RV2S0", "name": "2025_Flat_clasp_solid_wood_flooring.pdf", "vendor": "chinese-teak-vendor", "channel": "vendor-wood-flooring"},
    {"id": "F0A96KQBVN0", "name": "UV_Wall_Panel_Price_List.pdf", "vendor": "kejie-lidu", "channel": "vendor-wood-flooring"},
    {"id": "F0A8WLETZ1R", "name": "PVC_Foam_Board_Wall_Panel_Price_List.pdf", "vendor": "kejie-lidu", "channel": "vendor-wood-flooring"},
    {"id": "F0A931XDS7L", "name": "Indoor_Grille_Wall_Panel_Price_List.pdf", "vendor": "kejie-lidu", "channel": "vendor-wood-flooring"},
    {"id": "F0A8MJECA6B", "name": "SPC_Floor_Wall_Panel_Price.pdf", "vendor": "kejie-lidu", "channel": "vendor-wood-flooring"},
    {"id": "F0A931Y1YEN", "name": "Hot_Sale_WPC_Decking_Price_List.pdf", "vendor": "kejie-lidu", "channel": "vendor-wood-flooring"},
]


def get_file_info(file_id):
    """Get file info including download URL from Slack API."""
    resp = requests.get(
        "https://slack.com/api/files.info",
        headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
        params={"file": file_id},
    )
    data = resp.json()
    if not data.get("ok"):
        print(f"  ERROR getting file info: {data.get('error', 'unknown')}")
        return None
    return data["file"]


def download_file(url, local_path):
    """Download file from Slack."""
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {SLACK_TOKEN}"},
        stream=True,
    )
    if resp.status_code == 200:
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    print(f"  Download failed: HTTP {resp.status_code}")
    return False


def upload_to_gcs(storage_client, local_path, dest_folder, filename):
    """Upload to Cloud Storage."""
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"{dest_folder}/{filename}")
    blob.upload_from_filename(local_path)
    return f"gs://{BUCKET_NAME}/{dest_folder}/{filename}"


def main():
    if not SLACK_TOKEN:
        print("ERROR: Set SLACK_USER_TOKEN environment variable")
        sys.exit(1)

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    cred_path = os.path.join(
        "C:\\Users\\eukri\\OneDrive\\Documents\\Claude Code",
        "Credentials Claude Code",
        "ai-agents-go-4c81b70995db.json",
    )
    if os.path.exists(cred_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path

    storage_client = storage.Client(project=PROJECT_ID)
    db = get_client()
    images_col = db.collection("product_images")

    downloaded = 0
    uploaded = 0
    errors = 0

    for entry in SLACK_FILES:
        file_id = entry["id"]
        filename = entry["name"]
        vendor = entry["vendor"]
        channel = entry["channel"]
        local_path = os.path.join(DOWNLOAD_DIR, filename)

        # Skip if already downloaded
        if os.path.exists(local_path) and os.path.getsize(local_path) > 500:
            print(f"  SKIP (exists): {filename}")
            downloaded += 1
        else:
            print(f"  Downloading: {filename} ({file_id})...", end=" ")
            file_info = get_file_info(file_id)
            if not file_info:
                errors += 1
                continue

            dl_url = file_info.get("url_private_download") or file_info.get("url_private")
            if not dl_url:
                print("NO URL")
                errors += 1
                continue

            if download_file(dl_url, local_path):
                size = os.path.getsize(local_path)
                print(f"OK ({size/1024:.0f} KB)")
                downloaded += 1
            else:
                errors += 1
                continue

            time.sleep(0.5)  # Rate limit

        # Upload to Cloud Storage
        file_size = os.path.getsize(local_path)
        if file_size < 500:
            print(f"  SKIP upload (too small, likely error): {filename}")
            errors += 1
            continue
        if file_size > 100_000_000:
            print(f"  SKIP upload (>100MB): {filename}")
            continue

        dest_folder = f"slack/{vendor}"
        gs_path = upload_to_gcs(storage_client, local_path, dest_folder, filename)

        ext = filename.lower().split(".")[-1]
        content_type = {
            "pdf": "application/pdf",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xls": "application/vnd.ms-excel",
        }.get(ext, "application/octet-stream")

        # Check if already in Firestore
        existing = list(images_col.where("file_name", "==", filename).limit(1).stream())
        if not existing:
            images_col.add({
                "file_name": filename,
                "storage_path": gs_path,
                "content_type": content_type,
                "file_size_bytes": file_size,
                "vendor_id": vendor,
                "type": "quotation_scan" if "QC" in filename else "catalog" if "catalog" in filename.lower() or "catalogue" in filename.lower() else "datasheet",
                "source": f"slack:#{channel}",
                "slack_file_id": file_id,
                "uploaded_at": datetime.now(timezone.utc),
            })
        uploaded += 1
        print(f"  -> {gs_path}")

    print(f"\nDone: {downloaded} downloaded, {uploaded} uploaded, {errors} errors")

    # Final counts
    for col_name in ["vendors", "products", "quotations", "product_images", "categories"]:
        ref = db.collection(col_name)
        results = ref.count().get()
        count = results[0][0].value if results else 0
        print(f"  {col_name}: {count} documents")


if __name__ == "__main__":
    main()
