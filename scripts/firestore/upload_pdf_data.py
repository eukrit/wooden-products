"""Upload PDF-parsed products and quotations to Firestore."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from setup_db import get_client
from datetime import datetime, timezone

db = get_client()
now = datetime.now(timezone.utc)

# Add Elegant Living vendor
db.collection("vendors").document("elegant-living").set({
    "vendor_id": "elegant-living",
    "name": "Elegant Living",
    "type": "manufacturer",
    "country": "CN",
    "contact": {"email": "sales@elegantliving.cn", "website": "www.elegantliving.com.cn", "phone": "+86-751-86487282"},
    "products_supplied": ["engineered_flooring"],
    "notes": "4 collections (City Vogue, Ventura, American Rustic, Premier Classic). Oak, Hickory, Maple. Also vinyl LVT/Rigid.",
    "source": "onedrive/pdf",
    "created_at": now, "updated_at": now,
})
print("Added vendor: Elegant Living")

# Update Kihome
db.collection("vendors").document("kihome").update({
    "contact": {"email": "ask@kihomegroup.com"},
    "notes": "Est. 2005. Factories in CN/MX/VN/TH. Laminate, SPC, LVT, WPC flooring. ISO 9001/14001, CE, SGS, French A+.",
    "updated_at": now,
})
print("Updated vendor: Kihome")

# Update Pinecross
db.collection("vendors").document("pinecross").update({
    "contact": {
        "email": "wt.pinecross@gmail.com",
        "phone": "086-369-6756",
        "line_id": "pinecross.com",
        "address": "191/1 Pracharasd Sai 1 Rd, Soi 10, Bangsue, Bangkok 10800",
    },
    "notes": "NZ Radiata Pine, kiln dried, CCA H3 treated. Contact: Khun On. Tel: 0-2912-5200. 25yr warranty.",
    "updated_at": now,
})
print("Updated vendor: Pinecross")

# Products from PDF parsing
products = [
    {"product_id": "el-oak-maroon", "vendor_id": "elegant-living", "name": "Elegant Living Oak Maroon (City Vogue)", "category": "engineered_flooring", "material": "Oak", "specifications": {"dimensions": "12.5x148x2130mm", "finish": "Brushed"}, "unit": "sqm", "source": "pdf"},
    {"product_id": "el-oak-hamilton", "vendor_id": "elegant-living", "name": "Elegant Living Oak Hamilton (City Vogue)", "category": "engineered_flooring", "material": "Oak", "specifications": {"dimensions": "12x190x2130mm", "finish": "Brushed"}, "unit": "sqm", "source": "pdf"},
    {"product_id": "el-hickory-ember", "vendor_id": "elegant-living", "name": "Elegant Living Hickory Ember (American Rustic)", "category": "engineered_flooring", "material": "Hickory", "specifications": {"dimensions": "12.5x190x2130mm", "finish": "Hand Scraped"}, "unit": "sqm", "source": "pdf"},
    {"product_id": "kihome-spc", "vendor_id": "kihome", "name": "Kihome SPC Flooring", "category": "engineered_flooring", "subcategory": "SPC", "material": "Stone Polymer Composite", "specifications": {"thickness": "4-6mm", "fire_rating": "Bfl-s1"}, "unit": "sqm", "certifications": ["ISO 9001", "ISO 14001", "CE", "SGS", "French A+"], "source": "pdf"},
    {"product_id": "kihome-lvt", "vendor_id": "kihome", "name": "Kihome LVT Flooring (Dry Back)", "category": "engineered_flooring", "subcategory": "LVT", "material": "Luxury Vinyl Tile", "specifications": {"thickness": "2-3.5mm"}, "unit": "sqm", "source": "pdf"},
    {"product_id": "kihome-wpc", "vendor_id": "kihome", "name": "Kihome WPC Flooring", "category": "engineered_flooring", "subcategory": "WPC", "material": "Wood Polymer Composite", "specifications": {"thickness": "5-12mm"}, "unit": "sqm", "source": "pdf"},
    {"product_id": "kihome-laminate", "vendor_id": "kihome", "name": "Kihome Waterproof Laminate Flooring", "category": "engineered_flooring", "subcategory": "laminate", "material": "HDF Core", "specifications": {"thickness": "8/10/12mm"}, "unit": "sqm", "source": "pdf"},
    {"product_id": "pinecross-1x3", "vendor_id": "pinecross", "name": "Pinecross Pine 70x19mm (1x3)", "category": "structural_timber", "material": "NZ Radiata Pine CCA H3 KD", "specifications": {"dimensions": "70x19mm", "width": 70, "thickness": 19}, "unit": "lineal_meter", "notes": "THB 140/m ex-VAT, 149.80 incl VAT", "source": "pdf"},
    {"product_id": "pinecross-1x4", "vendor_id": "pinecross", "name": "Pinecross Pine 90x19mm (1x4)", "category": "structural_timber", "material": "NZ Radiata Pine CCA H3 KD", "specifications": {"dimensions": "90x19mm", "width": 90, "thickness": 19}, "unit": "lineal_meter", "notes": "THB 190/m ex-VAT, 203.30 incl VAT", "source": "pdf"},
    {"product_id": "pinecross-1x6", "vendor_id": "pinecross", "name": "Pinecross Pine 140x19mm (1x6)", "category": "structural_timber", "material": "NZ Radiata Pine CCA H3 KD", "specifications": {"dimensions": "140x19mm", "width": 140, "thickness": 19}, "unit": "lineal_meter", "notes": "THB 295/m ex-VAT, 315.65 incl VAT", "source": "pdf"},
    {"product_id": "pinecross-1x8", "vendor_id": "pinecross", "name": "Pinecross Pine 190x19mm (1x8)", "category": "structural_timber", "material": "NZ Radiata Pine CCA H3 KD", "specifications": {"dimensions": "190x19mm", "width": 190, "thickness": 19}, "unit": "lineal_meter", "notes": "THB 375/m ex-VAT, 401.25 incl VAT", "source": "pdf"},
    {"product_id": "pinecross-2x3", "vendor_id": "pinecross", "name": "Pinecross Pine 70x45mm (2x3)", "category": "structural_timber", "material": "NZ Radiata Pine CCA H3 KD", "specifications": {"dimensions": "70x45mm", "width": 70, "thickness": 45}, "unit": "lineal_meter", "notes": "THB 165/m ex-VAT, 176.55 incl VAT", "source": "pdf"},
    {"product_id": "pinecross-2x4", "vendor_id": "pinecross", "name": "Pinecross Pine 90x45mm (2x4)", "category": "structural_timber", "material": "NZ Radiata Pine CCA H3 KD", "specifications": {"dimensions": "90x45mm", "width": 90, "thickness": 45}, "unit": "lineal_meter", "notes": "THB 220/m ex-VAT, 235.40 incl VAT", "source": "pdf"},
    {"product_id": "pinecross-2x6", "vendor_id": "pinecross", "name": "Pinecross Pine 140x45mm (2x6)", "category": "structural_timber", "material": "NZ Radiata Pine CCA H3 KD", "specifications": {"dimensions": "140x45mm", "width": 140, "thickness": 45}, "unit": "lineal_meter", "notes": "THB 330/m ex-VAT, 353.10 incl VAT", "source": "pdf"},
    {"product_id": "pinecross-2x8", "vendor_id": "pinecross", "name": "Pinecross Pine 190x45mm (2x8)", "category": "structural_timber", "material": "NZ Radiata Pine CCA H3 KD", "specifications": {"dimensions": "190x45mm", "width": 190, "thickness": 45}, "unit": "lineal_meter", "notes": "THB 430/m ex-VAT, 460.10 incl VAT", "source": "pdf"},
]

for p in products:
    p["created_at"] = now
    p["updated_at"] = now
    db.collection("products").document(p["product_id"]).set(p)
print(f"Added {len(products)} products")

# Quotations from PDF parsing
quotations = [
    {
        "quotation_id": "pinecross-pc-30092024",
        "vendor_id": "pinecross",
        "quote_number": "PC 30092024",
        "quote_date": "2024-09-30",
        "currency": "THB",
        "items": [
            {"product_name": "Pine 70x45mm (2x3)", "description": "1.8m x2, 1.5m x2, 1.2m x1", "unit": "piece", "quantity": 5},
            {"product_name": "Pine 140x45mm (2x6)", "description": "0.3m x5", "unit": "piece", "quantity": 5},
        ],
        "subtotal": 2937.00,
        "tax": 205.59,
        "total": 3142.59,
        "terms": "100% payment upon order, pickup at Rangsit warehouse",
        "status": "received",
        "notes": "TCDC Chiangrai STAIR project.",
        "source": "onedrive/pdf",
        "created_at": now, "updated_at": now,
    },
    {
        "quotation_id": "pinecross-pc-18112021",
        "vendor_id": "pinecross",
        "quote_number": "PC 18112021",
        "quote_date": "2021-11-18",
        "currency": "THB",
        "items": [
            {"product_name": "Pine 140x19mm flooring (corrugated)", "unit": "lineal_meter", "unit_price": 360.00, "total_price": 17820.00, "quantity": 29},
            {"product_name": "Pine 140x19mm wall cladding (smooth)", "unit": "lineal_meter", "unit_price": 245.00, "total_price": 7276.50, "quantity": 15},
            {"product_name": "Pine 240x19mm stair treads (corrugated+varnished)", "unit": "lineal_meter", "unit_price": 900.00, "total_price": 3240.00, "quantity": 4},
            {"product_name": "Delivery (6-wheel truck + pickup)", "unit": "lot", "total_price": 5000.00},
        ],
        "subtotal": 33336.50,
        "tax": 2333.56,
        "total": 35670.06,
        "terms": "50% deposit, 50% before factory pickup",
        "status": "received",
        "notes": "Brighton Amata (SO21-041) + Central Ayutthaya (SO21-039). 25yr warranty termites/rot.",
        "source": "onedrive/pdf",
        "created_at": now, "updated_at": now,
    },
]

for q in quotations:
    db.collection("quotations").document(q["quotation_id"]).set(q)
print(f"Added {len(quotations)} quotations")

# Final counts
print()
for col_name in ["vendors", "products", "quotations", "product_images", "categories"]:
    ref = db.collection(col_name)
    results = ref.count().get()
    count = results[0][0].value if results else 0
    print(f"  {col_name}: {count} documents")
