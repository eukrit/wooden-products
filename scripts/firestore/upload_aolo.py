"""Upload Anhui Aolo products from parsed PI PDF."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from setup_db import get_client
from datetime import datetime, timezone

db = get_client()
now = datetime.now(timezone.utc)

# Update vendor
db.collection("vendors").document("anhui-aolo").update({
    "name": "Anhui Aolo New Materials Technology Co., Ltd.",
    "contact": {
        "phone": "+86 10021870520",
        "wechat": "+86 13023115889",
        "email": "winnerliu@yeah.net",
        "address": "No. 188, Renhe Rd, Dongshili Circular Economic Park, Suzhou, Anhui, China 234000",
    },
    "notes": "Contact: Jackson Liu. WPC co-extrusion + first gen. 30% deposit, balance before shipment. FOB Lianyungang. Bank: Huishang Bank Suzhou. PO.1285 issued Mar 2026.",
    "updated_at": now,
})
print("Updated vendor: Anhui Aolo")

products = [
    {"product_id": "aolo-gk219-26a", "name": "WPC Co-extrusion Panel AL-GK219/26A", "category": "cladding", "subcategory": "co-extrusion", "specs": "219x26mm", "w": 219, "t": 26, "usd_m": 2.91, "usd_pc": 8.439, "qty": 3240, "val": 27342.36},
    {"product_id": "aolo-gk219-26d", "name": "WPC Half-covered Co-extrusion Panel AL-GK219/26D", "category": "cladding", "subcategory": "co-extrusion", "specs": "219x26mm", "w": 219, "t": 26, "usd_m": 2.70, "usd_pc": 7.83, "qty": 3240, "val": 25369.20},
    {"product_id": "aolo-gk140-23c", "name": "WPC Co-extrusion Decking AL-GK140/23C", "category": "decking", "subcategory": "co-extrusion", "specs": "140x23mm", "w": 140, "t": 23, "usd_m": 2.55, "usd_pc": 7.395, "qty": 3400, "val": 25143.00},
    {"product_id": "aolo-gk148-22a", "name": "WPC Co-extrusion Decking AL-GK148/22A", "category": "decking", "subcategory": "co-extrusion", "specs": "148x22mm", "w": 148, "t": 22, "usd_m": 2.58, "usd_pc": 7.482, "qty": 3400, "val": 25438.80},
    {"product_id": "aolo-gs156-21c", "name": "WPC Co-extrusion Cladding AL-GS156/21C", "category": "cladding", "subcategory": "co-extrusion", "specs": "156x21mm", "w": 156, "t": 21, "usd_m": 1.56, "usd_pc": 4.524, "qty": 5600, "val": 25334.40},
    {"product_id": "aolo-k219-26b", "name": "First Gen WPC Wall Panel AL-K219/26B", "category": "cladding", "subcategory": "first_generation", "specs": "219x26mm", "w": 219, "t": 26, "usd_m": 2.05, "usd_pc": 5.95, "qty": 3240, "val": 19278.00},
    {"product_id": "aolo-k140-25l-2d", "name": "First Gen WPC Decking 2D Wood Grain AL-K140/25L", "category": "decking", "subcategory": "first_generation", "specs": "140x25mm", "w": 140, "t": 25, "usd_m": 1.75, "usd_pc": 5.104, "qty": 3800, "val": 19395.20},
    {"product_id": "aolo-k140-25l-3d", "name": "First Gen WPC Decking 3D Embossed AL-K140/25L", "category": "decking", "subcategory": "first_generation", "specs": "140x25mm", "w": 140, "t": 25, "usd_m": 1.85, "usd_pc": 5.365, "qty": 3800, "val": 20387.00},
    {"product_id": "aolo-k140-20a-2d", "name": "First Gen WPC Decking 2D Wood Grain AL-K140/20A", "category": "decking", "subcategory": "first_generation", "specs": "140x20mm", "w": 140, "t": 20, "usd_m": 1.39, "usd_pc": 4.031, "qty": 4600, "val": 18542.60},
    {"product_id": "aolo-k140-20a-3d", "name": "First Gen WPC Decking 3D Embossed AL-K140/20A", "category": "decking", "subcategory": "first_generation", "specs": "140x20mm", "w": 140, "t": 20, "usd_m": 1.49, "usd_pc": 4.321, "qty": 4600, "val": 19876.60},
    {"product_id": "aolo-s148-21a-2d", "name": "WPC Wall Cladding 2D Wood Grain AL-S148/21/A", "category": "cladding", "subcategory": "first_generation", "specs": "148x21mm", "w": 148, "t": 21, "usd_m": 1.18, "usd_pc": 3.422, "qty": 6000, "val": 20532.00},
    {"product_id": "aolo-s148-21a-3d", "name": "WPC Wall Cladding 3D Embossed AL-S148/21/A", "category": "cladding", "subcategory": "first_generation", "specs": "148x21mm", "w": 148, "t": 21, "usd_m": 1.20, "usd_pc": 3.48, "qty": 6000, "val": 20880.00},
    {"product_id": "aolo-k145-21a", "name": "First Gen WPC Decking 6-hole Grooved AL-K145/21A", "category": "decking", "subcategory": "first_generation", "specs": "145x21mm", "w": 145, "t": 21, "usd_m": 1.98, "usd_pc": 5.742, "qty": 3500, "val": 20097.00},
    {"product_id": "aolo-k140-23k", "name": "First Gen WPC Decking 2D 6-hole AL-K140/23.5K", "category": "decking", "subcategory": "first_generation", "specs": "140x23.5mm", "w": 140, "t": 23.5, "usd_m": 2.08, "usd_pc": 6.032, "qty": 3200, "val": 19302.40},
    {"product_id": "aolo-k148-23b", "name": "First Gen WPC Decking 3D Embossed AL-K148/23B", "category": "decking", "subcategory": "first_generation", "specs": "148x23mm", "w": 148, "t": 23, "usd_m": 1.98, "usd_pc": 5.742, "qty": 3500, "val": 20097.00},
]

for p in products:
    doc = {
        "product_id": p["product_id"],
        "vendor_id": "anhui-aolo",
        "name": p["name"],
        "category": p["category"],
        "subcategory": p["subcategory"],
        "material": "Wood Plastic Composite (WPC)",
        "specifications": {
            "dimensions": f'{p["specs"]}, L=2900mm',
            "width": p["w"],
            "thickness": p["t"],
            "length": 2900,
        },
        "unit": "piece (2.9m)",
        "origin_country": "CN",
        "notes": f'FOB Lianyungang. ${p["usd_m"]}/m = ${p["usd_pc"]}/pc. Container: {p["qty"]} pcs (1x40HC) = ${p["val"]:,.2f}',
        "source": "slack:PI_For_NIWAT_SAMRIT",
        "created_at": now,
        "updated_at": now,
    }
    db.collection("products").document(p["product_id"]).set(doc)

print(f"Added {len(products)} Anhui Aolo products")

# Add quotation
items = [{"product_id": p["product_id"], "product_name": p["name"], "unit_price": p["usd_m"], "unit": "meter", "quantity": p["qty"]} for p in products]
db.collection("quotations").document("aolo-ns20240516lj").set({
    "quotation_id": "aolo-ns20240516lj",
    "vendor_id": "anhui-aolo",
    "quote_number": "NS20240516LJ",
    "quote_date": "2025-11-25",
    "currency": "USD",
    "delivery_terms": "FOB Lianyungang",
    "items": items,
    "terms": "30% deposit, balance before shipment",
    "status": "received",
    "notes": "Container ~27.5 tons (68 cbm). Seafreight TBD.",
    "source": "slack:PI_For_NIWAT_SAMRIT",
    "source_document": "PI_For_NIWAT_SAMRIT_Aolo.pdf",
    "created_at": now,
    "updated_at": now,
})
print("Added quotation: NS20240516LJ")

# Final counts
for col_name in ["vendors", "products", "quotations", "product_images", "categories"]:
    ref = db.collection(col_name)
    results = ref.count().get()
    count = results[0][0].value if results else 0
    print(f"  {col_name}: {count} documents")
