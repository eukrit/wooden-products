"""
Setup Firestore database 'products-wood' in asia-southeast1
and seed default categories.

Usage:
    python scripts/firestore/setup_db.py
"""

import os
import sys
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from google.cloud import firestore
from schema import DEFAULT_CATEGORIES

PROJECT_ID = "ai-agents-go"
DATABASE_ID = "products-wood"


def get_client():
    """Get Firestore client for products-wood database."""
    # Check for service account key
    cred_path = os.path.join(
        "C:\\Users\\eukri\\OneDrive\\Documents\\Claude Code",
        "Credentials Claude Code",
        "ai-agents-go-9b4219be8c01.json",
    )
    if os.path.exists(cred_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path

    return firestore.Client(project=PROJECT_ID, database=DATABASE_ID)


def seed_categories(db):
    """Seed default product categories."""
    categories_ref = db.collection("categories")
    for cat in DEFAULT_CATEGORIES:
        doc_ref = categories_ref.document(cat["category_id"])
        if not doc_ref.get().exists:
            cat["created_at"] = datetime.now(timezone.utc)
            doc_ref.set(cat)
            print(f"  Created category: {cat['name']}")
        else:
            print(f"  Category exists: {cat['name']}")


def verify_collections(db):
    """Verify all collections are accessible."""
    collections = ["vendors", "products", "quotations", "product_images", "categories"]
    for name in collections:
        ref = db.collection(name)
        docs = list(ref.limit(1).stream())
        count_query = ref.count()
        results = count_query.get()
        count = results[0][0].value if results else 0
        print(f"  {name}: {count} documents")


def main():
    print(f"Setting up Firestore database: {DATABASE_ID}")
    print(f"Project: {PROJECT_ID}")
    print(f"Region: asia-southeast1")
    print()

    db = get_client()

    print("Seeding categories...")
    seed_categories(db)
    print()

    print("Verifying collections...")
    verify_collections(db)
    print()

    print("Database setup complete!")
    return db


if __name__ == "__main__":
    main()
