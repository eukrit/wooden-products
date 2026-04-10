"""Upload Aolo fence quotations from #vendor-anhui-aolo-wpc channel."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from setup_db import get_client
from datetime import datetime, timezone

db = get_client()
now = datetime.now(timezone.utc)

# Quotation 1: GK20260402LJ (Type 2+3, 2.0m boards)
db.collection("quotations").document("aolo-gk20260402lj").set({
    "quotation_id": "aolo-gk20260402lj",
    "vendor_id": "anhui-aolo",
    "quote_number": "GK20260402LJ",
    "quote_date": "2026-04-02",
    "currency": "USD",
    "delivery_terms": "FOB Guangzhou",
    "items": [
        {"product_name": "Aluminium Post AL-80/80A (3.0m)", "description": "80x80mm", "unit": "piece", "quantity": 33, "unit_price": 35.40, "total_price": 1168.20},
        {"product_name": "WPC Co-ex Fence Board GK161.5/20C (2.0m)", "description": "161.5x20mm, 20pcs/set", "unit": "piece", "quantity": 640, "unit_price": 4.40, "total_price": 2816.00},
        {"product_name": "Plastic Post Cap", "unit": "piece", "quantity": 33, "unit_price": 1.20, "total_price": 39.60},
        {"product_name": "Aluminium Upper Clamp Strip (2.0m)", "unit": "piece", "quantity": 32, "unit_price": 3.80, "total_price": 121.60},
        {"product_name": "Aluminium Lower Cover (2.0m)", "unit": "piece", "quantity": 32, "unit_price": 4.00, "total_price": 128.00},
        {"product_name": "L-shaped Connector", "unit": "piece", "quantity": 128, "unit_price": 0.15, "total_price": 19.20},
        {"product_name": "Steel Screws", "unit": "piece", "quantity": 256, "unit_price": 0.05, "total_price": 12.80},
        {"product_name": "Iron Pedestal 35x35x500mm", "unit": "piece", "quantity": 33, "unit_price": 7.80, "total_price": 257.40},
        {"product_name": "Expansion Screws", "unit": "piece", "quantity": 132, "unit_price": 0.35, "total_price": 46.20},
        {"product_name": "Aluminium Post AL-80/80A (2.0m)", "description": "Type-3", "unit": "piece", "quantity": 5, "unit_price": 23.60, "total_price": 118.00},
        {"product_name": "WPC Co-ex Fence Board GK161.5/20C (2.0m) Type-3", "description": "13pcs/set", "unit": "piece", "quantity": 52, "unit_price": 4.40, "total_price": 228.80},
        {"product_name": "WPC Gate 1.2mx2.0m", "unit": "set", "quantity": 1, "unit_price": 285.00, "total_price": 285.00},
    ],
    "subtotal": 5325.86, "shipping": 515.00, "total": 5840.86,
    "terms": "T/T or Alibaba",
    "status": "received",
    "notes": "Type-2: 32 sets (2.0mW x 3.0mH). Type-3: 4 sets (2.0m x 2.0m). +1 gate. Local to Guangzhou $515.",
    "source": "slack:#vendor-anhui-aolo-wpc",
    "source_document": "TYPE-2 &TYPE-3.pdf",
    "created_at": now, "updated_at": now,
})
print("Added: GK20260402LJ")

# Quotation 2: GK20260410LJ (Type 2+3, 2.025m boards)
db.collection("quotations").document("aolo-gk20260410lj").set({
    "quotation_id": "aolo-gk20260410lj",
    "vendor_id": "anhui-aolo",
    "quote_number": "GK20260410LJ",
    "quote_date": "2026-04-10",
    "currency": "USD",
    "delivery_terms": "FOB Guangzhou",
    "items": [
        {"product_name": "Aluminium Post AL-80/80A (3.0m)", "description": "80x80mm", "unit": "piece", "quantity": 33, "unit_price": 35.40, "total_price": 1168.20},
        {"product_name": "WPC Co-ex Fence Board GK161.5/20C (2.025m)", "description": "161.5x20mm, 20pcs/set", "unit": "piece", "quantity": 640, "unit_price": 4.455, "total_price": 2851.20},
        {"product_name": "Plastic Post Cap", "unit": "piece", "quantity": 33, "unit_price": 1.20, "total_price": 39.60},
        {"product_name": "Aluminium Upper Clamp Strip (2.025m)", "unit": "piece", "quantity": 32, "unit_price": 3.85, "total_price": 123.20},
        {"product_name": "Aluminium Lower Cover (2.025m)", "unit": "piece", "quantity": 32, "unit_price": 4.05, "total_price": 129.60},
        {"product_name": "L-shaped Connector", "unit": "piece", "quantity": 128, "unit_price": 0.15, "total_price": 19.20},
        {"product_name": "Steel Screws", "unit": "piece", "quantity": 256, "unit_price": 0.05, "total_price": 12.80},
        {"product_name": "Iron Pedestal 35x35x500mm", "unit": "piece", "quantity": 33, "unit_price": 7.80, "total_price": 257.40},
        {"product_name": "Expansion Screws", "unit": "piece", "quantity": 132, "unit_price": 0.35, "total_price": 46.20},
        {"product_name": "Aluminium Post AL-80/80A (2.0m)", "description": "Type-3: 5 sets", "unit": "piece", "quantity": 6, "unit_price": 23.60, "total_price": 141.60},
        {"product_name": "WPC Co-ex Fence Board GK161.5/20C (2.025m) Type-3", "description": "13pcs/set", "unit": "piece", "quantity": 65, "unit_price": 4.455, "total_price": 289.58},
        {"product_name": "WPC Gate 1.2mx2.0m", "unit": "set", "quantity": 1, "unit_price": 285.00, "total_price": 285.00},
    ],
    "subtotal": 5467.88, "shipping": 515.00, "total": 5982.88,
    "terms": "T/T or Alibaba",
    "status": "received",
    "notes": "Type-2: 32 sets (2.025mW x 3.0mH, 64.46m). Type-3: 5 sets (2.025m x 2.0m, 10.16m). +1 gate. Local $515.",
    "source": "slack:#vendor-anhui-aolo-wpc",
    "source_document": "32setsCO-extrusion fence GK161.5-20C ,2.025mX3 m  .pdf",
    "created_at": now, "updated_at": now,
})
print("Added: GK20260410LJ")

# Add fence products
products = [
    {"product_id": "aolo-post-al80-80a", "name": "Aluminium Alloy Hollow Post AL-80/80A", "category": "cladding", "subcategory": "fence_post",
     "material": "Aluminium Alloy", "specifications": {"dimensions": "80x80mm", "lengths_available": "2.0m, 3.0m"},
     "unit": "piece", "notes": "3.0m=$35.40/pc, 2.0m=$23.60/pc. Black finish."},
    {"product_id": "aolo-gk161-20c-fence", "name": "WPC Co-extrusion Fence Board GK161.5/20C", "category": "cladding", "subcategory": "fence_board",
     "material": "WPC Co-extrusion", "specifications": {"dimensions": "161.5x20mm", "width": 161.5, "thickness": 20, "effective_width": 148},
     "unit": "piece", "notes": "$4.40/pc (2.0m), $4.455/pc (2.025m). 20 boards/set for 3m fence, 13 boards/set for 2m fence. Charcoal or customized."},
    {"product_id": "aolo-gate-1200x2000", "name": "WPC Gate with Aluminium Post 1.2mx2.0m", "category": "cladding", "subcategory": "fence_gate",
     "material": "WPC + Aluminium", "specifications": {"dimensions": "1200x2000mm"}, "unit": "set", "notes": "$285/set."},
    {"product_id": "aolo-post-cap-80", "name": "Plastic Post Cap (80x80)", "category": "cladding", "subcategory": "fence_accessory",
     "material": "Plastic", "specifications": {}, "unit": "piece", "notes": "$1.20/pc."},
    {"product_id": "aolo-upper-clamp", "name": "Aluminium Upper Clamp Strip", "category": "cladding", "subcategory": "fence_accessory",
     "material": "Aluminium", "specifications": {}, "unit": "piece", "notes": "$3.80-3.85/pc."},
    {"product_id": "aolo-lower-cover", "name": "Aluminium Lower Cover", "category": "cladding", "subcategory": "fence_accessory",
     "material": "Aluminium", "specifications": {}, "unit": "piece", "notes": "$4.00-4.05/pc."},
    {"product_id": "aolo-iron-pedestal", "name": "Iron Pedestal incl. screws", "category": "cladding", "subcategory": "fence_accessory",
     "material": "Iron", "specifications": {"dimensions": "35x35x500mm"}, "unit": "piece", "notes": "$7.50-7.80/pc."},
]

for p in products:
    p["vendor_id"] = "anhui-aolo"
    p["origin_country"] = "CN"
    p["source"] = "slack:#vendor-anhui-aolo-wpc"
    p["created_at"] = now
    p["updated_at"] = now
    db.collection("products").document(p["product_id"]).set(p)
print(f"Added {len(products)} fence products")

# Final counts
for col_name in ["vendors", "products", "quotations", "product_images", "categories"]:
    ref = db.collection(col_name)
    results = ref.count().get()
    count = results[0][0].value if results else 0
    print(f"  {col_name}: {count}")
