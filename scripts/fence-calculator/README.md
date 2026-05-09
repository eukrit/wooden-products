# WPC Fence Calculator

Pure-Python BOM and FOB-Guangzhou costing for the Anhui Aolo WPC co-extrusion
fence system (board `GK161.5/20C` + post `AL-80/80A`).

## Source of truth

All formulas, SKUs, and unit prices come from these Aolo Proforma Invoices,
already loaded by `scripts/firestore/upload_aolo_fence.py`:

- `GK20260402LJ` — 32 sets Type 2 (2.0m W × 3.0m H), 4 sets Type 3, 1 gate
- `GK20260410LJ` — 32 sets Type 2 (2.025m W × 3.0m H), 5 sets Type 3, 1 gate

Do **not** edit `fence_params.json` to add unit prices that aren't in a real
quotation. Add new vendors / new SKUs by extending the JSON shape with their
own quote reference instead.

## Formulas (verified against the PIs above)

```
boards_per_bay = floor(bay_height_mm / 148)         # 148 = effective face mm
posts          = bays + 1
boards         = bays * boards_per_bay
clamps,covers  = bays                               # 1 each
connectors     = 4 * bays
steel_screws   = 8 * bays
caps,pedestals = posts                              # 1 each
expansion      = 4 * posts
```

| Type | Bay (W × H) | boards/bay |
|------|-------------|------------|
| 2    | 2.0m × 3.0m | 20         |
| 3    | 2.0m × 2.0m | 13         |

## CLI

```bash
python scripts/fence-calculator/cli.py --bays 32 --type 2 --no-shipping
python scripts/fence-calculator/cli.py --bays 4  --type 3 --gates 1
python scripts/fence-calculator/cli.py --bays 32 --type 2 --width 2.025
```

## Tests

```bash
cd scripts/fence-calculator && python -m unittest tests.test_calculator -v
```

13 tests, all pinned to actual PI line-item values.

## What this does NOT do

- **Weight / CBM / container-loadability**: vendor density data is not in the
  repo. The calculator deliberately refuses to compute these so we never
  quote shipping weight from fabricated numbers.
- **Custom fence types** (heights other than 2000 / 3000 mm, widths other
  than 2.0 / 2.025 m): rejected at validation. Add to `fence_params.json`
  with a real quote reference before extending.
- **Retail/markup pricing**: outputs FOB Guangzhou cost only. Apply markup
  in the configurator UI or quoting layer.
