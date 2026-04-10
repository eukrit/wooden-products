"""
Upload parsed product data from Slack PDF files to Firestore 'products-wood'.

Data sources:
  - SENTAI: 31 WPC products (USD FOB pricing)
  - BIOWOOD: 30 representative products (THB pricing)
  - FLEXISAND: 3 quotations (THB)

Also updates vendor contact info for Sentai and Flexisand.

Usage:
    python scripts/firestore/upload_slack_pdf_data.py
"""

import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from setup_db import get_client

NOW = datetime.now(timezone.utc)
SOURCE = "slack-pdf"


def upload_sentai_products(db):
    """Upload 16 Sentai WPC products (skipping STGJ68 already in DB)."""
    products = [
        # Decking
        {
            "product_id": "sentai-ST01E",
            "vendor_id": "sentai",
            "name": "Square Hollow Deck 150x25mm",
            "model": "ST01E",
            "brand": "Sentai",
            "category": "decking",
            "subcategory": "wpc_hollow_deck",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {
                "dimensions": "150x25mm",
                "width": 150,
                "thickness": 25,
                "profile": "square hollow",
            },
            "pricing": {
                "currency": "USD",
                "price_per_meter": 2.35,
                "price_per_sqm": 15.68,
                "terms": "FOB",
            },
            "unit": "lineal_meter",
            "origin_country": "China",
            "source": SOURCE,
        },
        {
            "product_id": "sentai-ST01AH",
            "vendor_id": "sentai",
            "name": "Round Hollow Deck 140x23mm",
            "model": "ST01AH",
            "brand": "Sentai",
            "category": "decking",
            "subcategory": "wpc_hollow_deck",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {
                "dimensions": "140x23mm",
                "width": 140,
                "thickness": 23,
                "profile": "round hollow",
            },
            "pricing": {
                "currency": "USD",
                "price_per_meter": 2.22,
                "price_per_sqm": 15.83,
                "terms": "FOB",
            },
            "unit": "lineal_meter",
            "origin_country": "China",
            "source": SOURCE,
        },
        {
            "product_id": "sentai-ST01CXX",
            "vendor_id": "sentai",
            "name": "Solid Deck 145x20mm",
            "model": "ST01CXX",
            "brand": "Sentai",
            "category": "decking",
            "subcategory": "wpc_solid_deck",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {
                "dimensions": "145x20mm",
                "width": 145,
                "thickness": 20,
                "profile": "solid",
            },
            "pricing": {
                "currency": "USD",
                "price_per_meter": 2.90,
                "price_per_sqm": 19.97,
                "terms": "FOB",
            },
            "unit": "lineal_meter",
            "origin_country": "China",
            "source": SOURCE,
        },
        {
            "product_id": "sentai-ST01BU",
            "vendor_id": "sentai",
            "name": "Solid Deck 140x20mm",
            "model": "ST01BU",
            "brand": "Sentai",
            "category": "decking",
            "subcategory": "wpc_solid_deck",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {
                "dimensions": "140x20mm",
                "width": 140,
                "thickness": 20,
                "profile": "solid",
            },
            "pricing": {
                "currency": "USD",
                "price_per_meter": 2.93,
                "price_per_sqm": 20.91,
                "terms": "FOB",
            },
            "unit": "lineal_meter",
            "origin_country": "China",
            "source": SOURCE,
        },
        {
            "product_id": "sentai-ST01LN",
            "vendor_id": "sentai",
            "name": "WPC Solid Deck Impress Tec 140x20mm",
            "model": "ST01LN",
            "brand": "Sentai",
            "category": "decking",
            "subcategory": "wpc_solid_deck",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {
                "dimensions": "140x20mm",
                "width": 140,
                "thickness": 20,
                "profile": "solid",
                "finish": "Impress Tec",
            },
            "pricing": {
                "currency": "USD",
                "price_per_meter": 2.01,
                "price_per_sqm": 14.38,
                "terms": "FOB",
            },
            "unit": "lineal_meter",
            "origin_country": "China",
            "source": SOURCE,
        },
        {
            "product_id": "sentai-STGJ01",
            "vendor_id": "sentai",
            "name": "Co-ex Solid Board Brushed 140x20mm",
            "model": "STGJ01",
            "brand": "Sentai",
            "category": "decking",
            "subcategory": "wpc_coex_deck",
            "material": "WPC Co-extrusion",
            "specifications": {
                "dimensions": "140x20mm",
                "width": 140,
                "thickness": 20,
                "profile": "solid",
                "finish": "brushed",
            },
            "pricing": {
                "currency": "USD",
                "price_per_meter": 3.76,
                "price_per_sqm": 26.88,
                "terms": "FOB",
            },
            "unit": "lineal_meter",
            "origin_country": "China",
            "source": SOURCE,
        },
        {
            "product_id": "sentai-STGJ08B",
            "vendor_id": "sentai",
            "name": "Co-ex Hollow Board Brushed (Origins) 136x21.5mm",
            "model": "STGJ08B",
            "brand": "Sentai",
            "category": "decking",
            "subcategory": "wpc_coex_deck",
            "material": "WPC Co-extrusion",
            "specifications": {
                "dimensions": "136x21.5mm",
                "width": 136,
                "thickness": 21.5,
                "profile": "hollow",
                "finish": "brushed",
                "series": "Origins",
            },
            "pricing": {
                "currency": "USD",
                "price_per_meter": 2.93,
                "price_per_sqm": 21.58,
                "terms": "FOB",
            },
            "unit": "lineal_meter",
            "origin_country": "China",
            "source": SOURCE,
        },
        {
            "product_id": "sentai-STGJ88",
            "vendor_id": "sentai",
            "name": "Co-ex Dual Tone 140x23mm",
            "model": "STGJ88",
            "brand": "Sentai",
            "category": "decking",
            "subcategory": "wpc_coex_deck",
            "material": "WPC Co-extrusion",
            "specifications": {
                "dimensions": "140x23mm",
                "width": 140,
                "thickness": 23,
                "finish": "dual tone",
            },
            "pricing": {
                "currency": "USD",
                "price_per_meter": 3.48,
                "price_per_sqm": 24.86,
                "terms": "FOB",
            },
            "unit": "lineal_meter",
            "origin_country": "China",
            "source": SOURCE,
        },
        {
            "product_id": "sentai-STTHM103",
            "vendor_id": "sentai",
            "name": "Apex 140x24mm",
            "model": "STTHM103",
            "brand": "Sentai",
            "category": "decking",
            "subcategory": "wpc_premium_deck",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {
                "dimensions": "140x24mm",
                "width": 140,
                "thickness": 24,
                "series": "Apex",
            },
            "pricing": {
                "currency": "USD",
                "price_per_meter": 5.81,
                "terms": "FOB",
            },
            "unit": "lineal_meter",
            "origin_country": "China",
            "source": SOURCE,
        },
        {
            "product_id": "sentai-STZQJAZ03D25",
            "vendor_id": "sentai",
            "name": "Regalboard 175x24mm",
            "model": "STZQJAZ03D25",
            "brand": "Sentai",
            "category": "decking",
            "subcategory": "wpc_premium_deck",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {
                "dimensions": "175x24mm",
                "width": 175,
                "thickness": 24,
                "series": "Regalboard",
            },
            "pricing": {
                "currency": "USD",
                "price_per_meter": 14.09,
                "price_per_sqm": 80.54,
                "terms": "FOB",
            },
            "unit": "lineal_meter",
            "origin_country": "China",
            "source": SOURCE,
        },
        {
            "product_id": "sentai-STZQJAZ03",
            "vendor_id": "sentai",
            "name": "Regalboard 175x22mm",
            "model": "STZQJAZ03",
            "brand": "Sentai",
            "category": "decking",
            "subcategory": "wpc_premium_deck",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {
                "dimensions": "175x22mm",
                "width": 175,
                "thickness": 22,
                "series": "Regalboard",
            },
            "pricing": {
                "currency": "USD",
                "price_per_meter": 11.39,
                "price_per_sqm": 65.11,
                "terms": "FOB",
            },
            "unit": "lineal_meter",
            "origin_country": "China",
            "source": SOURCE,
        },
        # Cladding
        {
            "product_id": "sentai-ST02LN",
            "vendor_id": "sentai",
            "name": "WPC Cladding Woodgrain 219x26mm",
            "model": "ST02LN",
            "brand": "Sentai",
            "category": "cladding",
            "subcategory": "wpc_cladding",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {
                "dimensions": "219x26mm",
                "width": 219,
                "thickness": 26,
                "finish": "woodgrain",
            },
            "pricing": {
                "currency": "USD",
                "price_per_meter": 2.44,
                "price_per_sqm": 12.18,
                "terms": "FOB",
            },
            "unit": "lineal_meter",
            "origin_country": "China",
            "source": SOURCE,
        },
        {
            "product_id": "sentai-STGJ86X",
            "vendor_id": "sentai",
            "name": "Co-ex Castellated Cladding 159x25.5mm",
            "model": "STGJ86X",
            "brand": "Sentai",
            "category": "cladding",
            "subcategory": "wpc_coex_cladding",
            "material": "WPC Co-extrusion",
            "specifications": {
                "dimensions": "159x25.5mm",
                "width": 159,
                "thickness": 25.5,
                "profile": "castellated",
            },
            "pricing": {
                "currency": "USD",
                "price_per_meter": 2.63,
                "price_per_sqm": 17.20,
                "terms": "FOB",
            },
            "unit": "lineal_meter",
            "origin_country": "China",
            "source": SOURCE,
        },
        {
            "product_id": "sentai-STGJ138",
            "vendor_id": "sentai",
            "name": "Co-ex Castellated Cladding 219x26mm",
            "model": "STGJ138",
            "brand": "Sentai",
            "category": "cladding",
            "subcategory": "wpc_coex_cladding",
            "material": "WPC Co-extrusion",
            "specifications": {
                "dimensions": "219x26mm",
                "width": 219,
                "thickness": 26,
                "profile": "castellated",
            },
            "pricing": {
                "currency": "USD",
                "price_per_meter": 2.98,
                "price_per_sqm": 14.90,
                "terms": "FOB",
            },
            "unit": "lineal_meter",
            "origin_country": "China",
            "source": SOURCE,
        },
        {
            "product_id": "sentai-STGJ166",
            "vendor_id": "sentai",
            "name": "BPC Co-ex Cladding Two Colors 209x25mm",
            "model": "STGJ166",
            "brand": "Sentai",
            "category": "cladding",
            "subcategory": "bpc_coex_cladding",
            "material": "BPC Co-extrusion",
            "specifications": {
                "dimensions": "209x25mm",
                "width": 209,
                "thickness": 25,
                "finish": "two colors",
            },
            "pricing": {
                "currency": "USD",
                "price_per_meter": 2.86,
                "price_per_sqm": 14.28,
                "terms": "FOB",
            },
            "unit": "lineal_meter",
            "origin_country": "China",
            "source": SOURCE,
        },
        # Structural
        {
            "product_id": "sentai-STLS01X",
            "vendor_id": "sentai",
            "name": "Alum-WPC Co-ex Beam 99.5x29.5mm",
            "model": "STLS01X",
            "brand": "Sentai",
            "category": "structural_timber",
            "subcategory": "wpc_beam",
            "material": "Aluminium-WPC Co-extrusion",
            "specifications": {
                "dimensions": "99.5x29.5mm",
                "width": 99.5,
                "thickness": 29.5,
            },
            "pricing": {
                "currency": "USD",
                "price_per_meter": 6.06,
                "terms": "FOB",
            },
            "unit": "lineal_meter",
            "origin_country": "China",
            "source": SOURCE,
        },
        {
            "product_id": "sentai-STLS02X",
            "vendor_id": "sentai",
            "name": "Alum-WPC Co-ex Beam 150x50mm",
            "model": "STLS02X",
            "brand": "Sentai",
            "category": "structural_timber",
            "subcategory": "wpc_beam",
            "material": "Aluminium-WPC Co-extrusion",
            "specifications": {
                "dimensions": "150x50mm",
                "width": 150,
                "thickness": 50,
            },
            "pricing": {
                "currency": "USD",
                "price_per_meter": 15.48,
                "terms": "FOB",
            },
            "unit": "lineal_meter",
            "origin_country": "China",
            "source": SOURCE,
        },
    ]

    col = db.collection("products")
    count = 0
    for p in products:
        p["created_at"] = NOW
        p["updated_at"] = NOW
        col.document(p["product_id"]).set(p)
        count += 1
    print(f"  Uploaded {count} Sentai products")
    return count


def upload_biowood_products(db):
    """Upload 30 Biowood representative products."""
    products = [
        # Decking (5)
        {
            "product_id": "biowood-DB30032",
            "vendor_id": "biowood",
            "name": "Decking 300x32mm",
            "model": "DB30032",
            "brand": "Biowood",
            "category": "decking",
            "subcategory": "wpc_deck",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "300x32mm", "width": 300, "thickness": 32},
            "pricing": {"currency": "THB", "price_per_meter": 1419, "price_per_sqm": 4730},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        {
            "product_id": "biowood-DB20025",
            "vendor_id": "biowood",
            "name": "Decking 200x25mm",
            "model": "DB20025",
            "brand": "Biowood",
            "category": "decking",
            "subcategory": "wpc_deck",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "200x25mm", "width": 200, "thickness": 25},
            "pricing": {"currency": "THB", "price_per_meter": 910.80, "price_per_sqm": 4486},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        {
            "product_id": "biowood-DB14028",
            "vendor_id": "biowood",
            "name": "Decking 140x28mm",
            "model": "DB14028",
            "brand": "Biowood",
            "category": "decking",
            "subcategory": "wpc_deck",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "140x28mm", "width": 140, "thickness": 28},
            "pricing": {"currency": "THB", "price_per_meter": 660, "price_per_sqm": 4615},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        {
            "product_id": "biowood-DBS14028",
            "vendor_id": "biowood",
            "name": "Decking Solid 140x28mm",
            "model": "DBS14028",
            "brand": "Biowood",
            "category": "decking",
            "subcategory": "wpc_solid_deck",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "140x28mm", "width": 140, "thickness": 28, "profile": "solid"},
            "pricing": {"currency": "THB", "price_per_meter": 1346.40, "price_per_sqm": 9415},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        {
            "product_id": "biowood-DB10020",
            "vendor_id": "biowood",
            "name": "Decking 100x20mm",
            "model": "DB10020",
            "brand": "Biowood",
            "category": "decking",
            "subcategory": "wpc_deck",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "100x20mm", "width": 100, "thickness": 20},
            "pricing": {"currency": "THB", "price_per_meter": 415.80},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        # Wall Panel Indoor (3)
        {
            "product_id": "biowood-WPI33314",
            "vendor_id": "biowood",
            "name": "Wall Panel Indoor 333x14mm",
            "model": "WPI33314",
            "brand": "Biowood",
            "category": "cladding",
            "subcategory": "wall_panel_indoor",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "333x14mm", "width": 333, "thickness": 14},
            "pricing": {"currency": "THB", "price_per_meter": 825, "price_per_sqm": 2477},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        {
            "product_id": "biowood-WPI25010",
            "vendor_id": "biowood",
            "name": "Wall Panel Indoor 250x10mm",
            "model": "WPI25010",
            "brand": "Biowood",
            "category": "cladding",
            "subcategory": "wall_panel_indoor",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "250x10mm", "width": 250, "thickness": 10},
            "pricing": {"currency": "THB", "price_per_meter": 508.20, "price_per_sqm": 2033},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        {
            "product_id": "biowood-WPI19535",
            "vendor_id": "biowood",
            "name": "Wall Panel Indoor 195x35mm",
            "model": "WPI19535",
            "brand": "Biowood",
            "category": "cladding",
            "subcategory": "wall_panel_indoor",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "195x35mm", "width": 195, "thickness": 35},
            "pricing": {"currency": "THB", "price_per_meter": 462, "price_per_sqm": 2369},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        # Wall Panel Outdoor (3)
        {
            "product_id": "biowood-WPO60018",
            "vendor_id": "biowood",
            "name": "Wall Panel Outdoor 600x18mm",
            "model": "WPO60018",
            "brand": "Biowood",
            "category": "cladding",
            "subcategory": "wall_panel_outdoor",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "600x18mm", "width": 600, "thickness": 18},
            "pricing": {"currency": "THB", "price_per_meter": 1914, "price_per_sqm": 3190},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        {
            "product_id": "biowood-WPO25035",
            "vendor_id": "biowood",
            "name": "Wall Panel Outdoor 250x35mm",
            "model": "WPO25035",
            "brand": "Biowood",
            "category": "cladding",
            "subcategory": "wall_panel_outdoor",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "250x35mm", "width": 250, "thickness": 35},
            "pricing": {"currency": "THB", "price_per_meter": 924, "price_per_sqm": 3696},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        {
            "product_id": "biowood-WPO20028",
            "vendor_id": "biowood",
            "name": "Wall Panel Outdoor 200x28mm",
            "model": "WPO20028",
            "brand": "Biowood",
            "category": "cladding",
            "subcategory": "wall_panel_outdoor",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "200x28mm", "width": 200, "thickness": 28},
            "pricing": {"currency": "THB", "price_per_meter": 660, "price_per_sqm": 3300},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        # Ceiling (3)
        {
            "product_id": "biowood-CL36010",
            "vendor_id": "biowood",
            "name": "Ceiling 360x10mm",
            "model": "CL36010",
            "brand": "Biowood",
            "category": "cladding",
            "subcategory": "ceiling",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "360x10mm", "width": 360, "thickness": 10},
            "pricing": {"currency": "THB", "price_per_meter": 528, "price_per_sqm": 1467},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        {
            "product_id": "biowood-CL20025",
            "vendor_id": "biowood",
            "name": "Ceiling 200x25mm",
            "model": "CL20025",
            "brand": "Biowood",
            "category": "cladding",
            "subcategory": "ceiling",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "200x25mm", "width": 200, "thickness": 25},
            "pricing": {"currency": "THB", "price_per_meter": 508.20, "price_per_sqm": 2541},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        {
            "product_id": "biowood-CL15008",
            "vendor_id": "biowood",
            "name": "Ceiling 150x8mm",
            "model": "CL15008",
            "brand": "Biowood",
            "category": "cladding",
            "subcategory": "ceiling",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "150x8mm", "width": 150, "thickness": 8},
            "pricing": {"currency": "THB", "price_per_meter": 231, "price_per_sqm": 1540},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        # Indoor Flooring (3)
        {
            "product_id": "biowood-IF25008",
            "vendor_id": "biowood",
            "name": "Indoor Flooring 250x8mm",
            "model": "IF25008",
            "brand": "Biowood",
            "category": "engineered_flooring",
            "subcategory": "wpc_indoor_flooring",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "250x8mm", "width": 250, "thickness": 8},
            "pricing": {"currency": "THB", "price_per_meter": 660, "price_per_sqm": 2640},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        {
            "product_id": "biowood-IF20012",
            "vendor_id": "biowood",
            "name": "Indoor Flooring 200x12mm",
            "model": "IF20012",
            "brand": "Biowood",
            "category": "engineered_flooring",
            "subcategory": "wpc_indoor_flooring",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "200x12mm", "width": 200, "thickness": 12},
            "pricing": {"currency": "THB", "price_per_meter": 646.80, "price_per_sqm": 3234},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        {
            "product_id": "biowood-IF14010",
            "vendor_id": "biowood",
            "name": "Indoor Flooring 140x10mm",
            "model": "IF14010",
            "brand": "Biowood",
            "category": "engineered_flooring",
            "subcategory": "wpc_indoor_flooring",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "140x10mm", "width": 140, "thickness": 10},
            "pricing": {"currency": "THB", "price_per_meter": 330, "price_per_sqm": 2357},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        # Louver (2)
        {
            "product_id": "biowood-LV30050",
            "vendor_id": "biowood",
            "name": "Louver 300x50mm",
            "model": "LV30050",
            "brand": "Biowood",
            "category": "cladding",
            "subcategory": "louver",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "300x50mm", "width": 300, "thickness": 50},
            "pricing": {"currency": "THB", "price_per_meter": 1221, "price_per_sqm": 3131},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        {
            "product_id": "biowood-LV15035",
            "vendor_id": "biowood",
            "name": "Louver 150x35mm",
            "model": "LV15035",
            "brand": "Biowood",
            "category": "cladding",
            "subcategory": "louver",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "150x35mm", "width": 150, "thickness": 35},
            "pricing": {"currency": "THB", "price_per_meter": 594, "price_per_sqm": 4097},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        # Facade Screen (2)
        {
            "product_id": "biowood-FS28040",
            "vendor_id": "biowood",
            "name": "Facade Screen 280x40mm",
            "model": "FS28040",
            "brand": "Biowood",
            "category": "cladding",
            "subcategory": "facade_screen",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "280x40mm", "width": 280, "thickness": 40},
            "pricing": {"currency": "THB", "price_per_meter": 1122},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        {
            "product_id": "biowood-FS22050",
            "vendor_id": "biowood",
            "name": "Facade Screen 220x50mm",
            "model": "FS22050",
            "brand": "Biowood",
            "category": "cladding",
            "subcategory": "facade_screen",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "220x50mm", "width": 220, "thickness": 50},
            "pricing": {"currency": "THB", "price_per_meter": 910.80},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        # Fencing (2)
        {
            "product_id": "biowood-FP30050",
            "vendor_id": "biowood",
            "name": "Fencing 300x50mm",
            "model": "FP30050",
            "brand": "Biowood",
            "category": "cladding",
            "subcategory": "fencing",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "300x50mm", "width": 300, "thickness": 50},
            "pricing": {"currency": "THB", "price_per_meter": 1254},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        {
            "product_id": "biowood-FP120120",
            "vendor_id": "biowood",
            "name": "Fence Post 120x120mm",
            "model": "FP120120",
            "brand": "Biowood",
            "category": "structural_timber",
            "subcategory": "fence_post",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "120x120mm", "width": 120, "thickness": 120},
            "pricing": {"currency": "THB", "price_per_meter": 1419},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        # Handrail (1)
        {
            "product_id": "biowood-HR13050",
            "vendor_id": "biowood",
            "name": "Handrail 130x50mm",
            "model": "HR13050",
            "brand": "Biowood",
            "category": "moulding",
            "subcategory": "handrail",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "130x50mm", "width": 130, "thickness": 50},
            "pricing": {"currency": "THB", "price_per_meter": 726},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
        # Staircase (1)
        {
            "product_id": "biowood-SC30032",
            "vendor_id": "biowood",
            "name": "Staircase 300x32mm",
            "model": "SC30032",
            "brand": "Biowood",
            "category": "decking",
            "subcategory": "staircase",
            "material": "WPC (Wood Plastic Composite)",
            "specifications": {"dimensions": "300x32mm", "width": 300, "thickness": 32},
            "pricing": {"currency": "THB", "price_per_meter": 1702.80},
            "unit": "lineal_meter",
            "origin_country": "Thailand",
            "source": SOURCE,
        },
    ]

    col = db.collection("products")
    count = 0
    for p in products:
        p["created_at"] = NOW
        p["updated_at"] = NOW
        col.document(p["product_id"]).set(p)
        count += 1
    print(f"  Uploaded {count} Biowood products")
    return count


def upload_flexisand_quotations(db):
    """Upload 3 Flexisand quotations."""
    quotations = [
        {
            "quotation_id": "QO2024110012",
            "vendor_id": "flexisand",
            "quote_number": "QO2024110012",
            "quote_date": datetime(2024, 11, 11, tzinfo=timezone.utc),
            "currency": "THB",
            "items": [
                {
                    "product_name": "FlexiSand Installation",
                    "description": "Banyan Tree Phuket WaterPlay",
                    "unit": "sqm",
                    "quantity": 175,
                    "unit_price": 1550,
                    "total_price": 271250,
                },
                {
                    "product_name": "Project Management",
                    "description": "Site management fee",
                    "unit": "lump_sum",
                    "quantity": 1,
                    "unit_price": 15000,
                    "total_price": 15000,
                },
            ],
            "subtotal": 286250,
            "tax": 20037.50,
            "total": 306287.50,
            "terms": "30/60/10",
            "delivery_terms": "installed",
            "status": "received",
            "notes": "Banyan Tree Phuket WaterPlay project",
            "source": SOURCE,
        },
        {
            "quotation_id": "QO2025070062",
            "vendor_id": "flexisand",
            "quote_number": "QO2025070062",
            "quote_date": datetime(2025, 7, 31, tzinfo=timezone.utc),
            "currency": "THB",
            "items": [
                {
                    "product_name": "FlexiSand Installation",
                    "description": "Koh Phangan project",
                    "unit": "sqm",
                    "quantity": 110,
                    "unit_price": 1550,
                    "total_price": 170500,
                },
                {
                    "product_name": "Project Management (10%)",
                    "description": "Site management fee",
                    "unit": "lump_sum",
                    "quantity": 1,
                    "unit_price": 17050,
                    "total_price": 17050,
                },
            ],
            "subtotal": 187550,
            "tax": 13128.50,
            "total": 200678.50,
            "terms": "50/40/10",
            "delivery_terms": "installed",
            "status": "received",
            "notes": "Koh Phangan project",
            "source": SOURCE,
        },
        {
            "quotation_id": "QO2025080021",
            "vendor_id": "flexisand",
            "quote_number": "QO2025080021",
            "quote_date": datetime(2025, 8, 18, tzinfo=timezone.utc),
            "currency": "THB",
            "items": [
                {
                    "product_name": "FlexiSand Installation",
                    "description": "Phuket small job",
                    "unit": "lump_sum",
                    "quantity": 1,
                    "unit_price": 31000,
                    "total_price": 31000,
                },
                {
                    "product_name": "Project Management",
                    "description": "Site management fee",
                    "unit": "lump_sum",
                    "quantity": 1,
                    "unit_price": 5000,
                    "total_price": 5000,
                },
            ],
            "subtotal": 36000,
            "tax": 2520,
            "total": 38520,
            "terms": "50/40/10",
            "delivery_terms": "installed",
            "status": "received",
            "notes": "Phuket small job",
            "source": SOURCE,
        },
    ]

    col = db.collection("quotations")
    count = 0
    for q in quotations:
        q["created_at"] = NOW
        q["updated_at"] = NOW
        col.document(q["quotation_id"]).set(q)
        count += 1
    print(f"  Uploaded {count} Flexisand quotations")
    return count


def update_vendor_contacts(db):
    """Update Sentai contact info and Flexisand company name."""
    vendors_ref = db.collection("vendors")

    # Update Sentai vendor contact
    sentai_ref = vendors_ref.document("sentai")
    sentai_doc = sentai_ref.get()
    if sentai_doc.exists:
        sentai_ref.update({
            "contact": {
                "email": "sarah@sentaigroup.com",
                "phone": "+86-13868266272",
                "contact_person": "Sarah Pan",
                "address": "Guangde City, Anhui Province, China",
            },
            "country": "China",
            "updated_at": NOW,
        })
        print("  Updated Sentai vendor contact (Sarah Pan)")
    else:
        # Create if not exists
        sentai_ref.set({
            "vendor_id": "sentai",
            "name": "Sentai Group",
            "brand": "Sentai",
            "type": "manufacturer",
            "country": "China",
            "contact": {
                "email": "sarah@sentaigroup.com",
                "phone": "+86-13868266272",
                "contact_person": "Sarah Pan",
                "address": "Guangde City, Anhui Province, China",
            },
            "products_supplied": ["decking", "cladding", "structural_timber"],
            "notes": "WPC/BPC manufacturer, co-extrusion specialist",
            "source": SOURCE,
            "created_at": NOW,
            "updated_at": NOW,
        })
        print("  Created Sentai vendor with contact (Sarah Pan)")

    # Update Flexisand vendor — real company name
    flexisand_ref = vendors_ref.document("flexisand")
    flexisand_doc = flexisand_ref.get()
    if flexisand_doc.exists:
        flexisand_ref.update({
            "name": "Au Kun Sam Co., Ltd.",
            "brand": "FlexiSand",
            "updated_at": NOW,
        })
        print("  Updated Flexisand vendor (Au Kun Sam Co., Ltd.)")
    else:
        flexisand_ref.set({
            "vendor_id": "flexisand",
            "name": "Au Kun Sam Co., Ltd.",
            "brand": "FlexiSand",
            "type": "distributor",
            "country": "Thailand",
            "contact": {},
            "products_supplied": ["decking"],
            "notes": "FlexiSand rubber safety surfacing installer",
            "source": SOURCE,
            "created_at": NOW,
            "updated_at": NOW,
        })
        print("  Created Flexisand vendor (Au Kun Sam Co., Ltd.)")

    # Ensure Biowood vendor exists
    biowood_ref = vendors_ref.document("biowood")
    biowood_doc = biowood_ref.get()
    if not biowood_doc.exists:
        biowood_ref.set({
            "vendor_id": "biowood",
            "name": "Biowood Co., Ltd.",
            "brand": "Biowood",
            "type": "manufacturer",
            "country": "Thailand",
            "contact": {},
            "products_supplied": [
                "decking", "cladding", "engineered_flooring",
                "moulding", "structural_timber",
            ],
            "notes": "Thai WPC manufacturer — full product range",
            "source": SOURCE,
            "created_at": NOW,
            "updated_at": NOW,
        })
        print("  Created Biowood vendor")
    else:
        print("  Biowood vendor already exists")


def print_collection_counts(db):
    """Print final counts for all collections."""
    print("\n--- Final Firestore Collection Counts ---")
    collections = ["vendors", "products", "quotations", "product_images", "categories"]
    for name in collections:
        ref = db.collection(name)
        count_query = ref.count()
        results = count_query.get()
        count = results[0][0].value if results else 0
        print(f"  {name}: {count} documents")


def main():
    print("=" * 60)
    print("Uploading Slack PDF data to Firestore 'products-wood'")
    print("=" * 60)

    db = get_client()
    total = 0

    print("\n1. Updating vendor contacts...")
    update_vendor_contacts(db)

    print("\n2. Uploading Sentai WPC products (17 products, USD FOB)...")
    total += upload_sentai_products(db)

    print("\n3. Uploading Biowood products (26 products, THB)...")
    total += upload_biowood_products(db)

    print("\n4. Uploading Flexisand quotations (3 quotations, THB)...")
    total += upload_flexisand_quotations(db)

    print(f"\nTotal records uploaded: {total}")

    print_collection_counts(db)
    print("\nDone!")


if __name__ == "__main__":
    main()
