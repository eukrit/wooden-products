"""
Firestore Schema for products-wood database
Database: products-wood (asia-southeast1)

Collections:
  - vendors          — Supplier/manufacturer profiles
  - products         — Individual wood products with specs
  - quotations       — Price quotes linked to vendors & products
  - product_images   — Image/attachment metadata (files in Cloud Storage)
  - categories       — Product category taxonomy
"""

SCHEMA = {
    "vendors": {
        "description": "Supplier and manufacturer profiles",
        "fields": {
            "vendor_id": "string (auto-generated)",
            "name": "string — company name",
            "name_th": "string — Thai name (optional)",
            "brand": "string — brand name if different",
            "type": "string — manufacturer | distributor | importer | agent",
            "country": "string — country of origin",
            "contact": {
                "email": "string",
                "phone": "string",
                "line_id": "string",
                "website": "string",
                "address": "string",
            },
            "products_supplied": "array[string] — product category refs",
            "notes": "string",
            "source": "string — where data was collected (slack/drive/email)",
            "created_at": "timestamp",
            "updated_at": "timestamp",
        },
    },
    "products": {
        "description": "Individual wood products with specifications",
        "fields": {
            "product_id": "string (auto-generated)",
            "vendor_id": "string — ref to vendors collection",
            "name": "string — product name",
            "name_th": "string — Thai name (optional)",
            "brand": "string",
            "category": "string — e.g. artificial_wood, engineered_flooring, timber, accoya, pinecross",
            "subcategory": "string",
            "material": "string — wood species or composite type",
            "specifications": {
                "dimensions": "string — e.g. 20x140x2200mm",
                "thickness": "number (mm)",
                "width": "number (mm)",
                "length": "number (mm)",
                "grade": "string — e.g. A, AB, Select",
                "finish": "string — e.g. unfinished, oiled, lacquered",
                "color": "string",
                "pattern": "string — e.g. herringbone, plank, parquet",
                "density": "string",
                "moisture_content": "string",
                "fire_rating": "string",
                "warranty_years": "number",
            },
            "unit": "string — sqm, piece, lineal_meter, sheet",
            "moq": "string — minimum order quantity",
            "lead_time_days": "number",
            "origin_country": "string",
            "certifications": "array[string] — FSC, PEFC, etc.",
            "datasheet_url": "string — Cloud Storage path",
            "image_urls": "array[string] — Cloud Storage paths",
            "notes": "string",
            "source": "string",
            "created_at": "timestamp",
            "updated_at": "timestamp",
        },
    },
    "quotations": {
        "description": "Price quotations linked to vendors and products",
        "fields": {
            "quotation_id": "string (auto-generated)",
            "vendor_id": "string — ref to vendors",
            "product_id": "string — ref to products (optional, can be general quote)",
            "quote_number": "string — vendor's reference number",
            "quote_date": "timestamp",
            "valid_until": "timestamp",
            "currency": "string — THB, USD, EUR, CNY",
            "items": [
                {
                    "product_name": "string",
                    "product_id": "string (optional ref)",
                    "description": "string",
                    "unit": "string",
                    "quantity": "number",
                    "unit_price": "number",
                    "total_price": "number",
                    "notes": "string",
                }
            ],
            "subtotal": "number",
            "tax": "number",
            "shipping": "number",
            "total": "number",
            "terms": "string — payment terms",
            "delivery_terms": "string — EXW, FOB, CIF, etc.",
            "status": "string — received, under_review, accepted, rejected, expired",
            "source_document": "string — Cloud Storage path to original PDF/file",
            "notes": "string",
            "source": "string",
            "created_at": "timestamp",
            "updated_at": "timestamp",
        },
    },
    "product_images": {
        "description": "Image and attachment metadata",
        "fields": {
            "image_id": "string (auto-generated)",
            "product_id": "string — ref to products",
            "vendor_id": "string — ref to vendors",
            "file_name": "string",
            "storage_path": "string — gs://bucket/path",
            "content_type": "string — image/jpeg, application/pdf, etc.",
            "file_size_bytes": "number",
            "description": "string",
            "type": "string — product_photo, datasheet, catalog, quotation_scan",
            "source": "string",
            "uploaded_at": "timestamp",
        },
    },
    "categories": {
        "description": "Product category taxonomy",
        "fields": {
            "category_id": "string",
            "name": "string",
            "name_th": "string",
            "parent_id": "string (optional)",
            "description": "string",
        },
    },
}

# Default categories to seed
DEFAULT_CATEGORIES = [
    {"category_id": "artificial_wood", "name": "Artificial Wood", "name_th": "ไม้เทียม", "description": "Composite and WPC wood products"},
    {"category_id": "engineered_flooring", "name": "Engineered Flooring", "name_th": "พื้นไม้เอ็นจิเนียร์", "description": "Engineered hardwood flooring"},
    {"category_id": "timber_flooring", "name": "Timber Flooring", "name_th": "พื้นไม้จริง", "description": "Solid timber flooring"},
    {"category_id": "accoya", "name": "Accoya", "name_th": "อะโคย่า", "description": "Acetylated modified wood (Accoya brand)"},
    {"category_id": "pinecross", "name": "Pinecross", "name_th": "ไพน์ครอส", "description": "Pinecross brand wood products"},
    {"category_id": "decking", "name": "Decking", "name_th": "ไม้ระเบียง", "description": "Outdoor decking and cladding"},
    {"category_id": "cladding", "name": "Cladding", "name_th": "ไม้ผนัง", "description": "Wall cladding and siding"},
    {"category_id": "structural_timber", "name": "Structural Timber", "name_th": "ไม้โครงสร้าง", "description": "Structural grade timber and lumber"},
    {"category_id": "plywood", "name": "Plywood", "name_th": "ไม้อัด", "description": "Plywood and panel products"},
    {"category_id": "veneer", "name": "Veneer", "name_th": "ไม้วีเนียร์", "description": "Natural and reconstituted veneer"},
    {"category_id": "moulding", "name": "Moulding & Trim", "name_th": "บัวไม้", "description": "Decorative mouldings and trim"},
]
