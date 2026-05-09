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

## Weight & CBM (estimate, opt-in)

Pass `--ship-est` to the CLI (or `include_shipping_estimate=True` to
`calculate()`) to also get an estimated total weight and bounding-box CBM.

Inputs:
- **Board weight** = `2.2 kg/m` — manufacturer's published spec, sourced
  from `website/PROMPT.md` and `website/products.html`.
- **Post weight** = `1.685 kg/m` — computed from physics, not pulled from
  a quote: `(80² − 76²) mm² × 2700 kg/m³ = 1.685 kg/m` (80×80mm hollow
  aluminium with assumed 2 mm wall thickness).
- **Accessories** = `+5%` flat buffer over board+post weight. Clamps,
  covers, connectors, screws, caps, pedestals, expansion screws each
  contribute well under 1% of the kit weight; we don't fabricate per-SKU
  densities for them.
- **CBM** = bounding box per item (board: 0.1615 × 0.020 × length_m;
  post: 0.080 × 0.080 × length_m). Real packed CBM will be lower since
  boards bundle tightly.

The CLI always prints "NOT vendor-confirmed — request actual packing
list before booking freight." Don't quote sea freight off this output;
it's for sanity-checking truck loads and order-size feasibility.

For PI GK20260402LJ Type-2 (32 bays × 3.0m):
```
Weight:    3132.0 kg
CBM:          4.768 m^3
```
Comfortably fits in a 40HQ (~76 m³ / ~26 t), consistent with the PI
shipping local-to-Guangzhou rather than containerized.

## What this does NOT do

- **Container counts** (20'/40'/40HQ): out of scope. Ask the freight
  forwarder once you have the real packing list.
- **Custom fence types** (heights other than 2000 / 3000 mm, widths
  other than 2.0 / 2.025 m): rejected at validation. Add to
  `fence_params.json` with a real quote reference before extending.
- **Retail/markup pricing**: outputs FOB Guangzhou cost only. Apply
  markup in the configurator UI or quoting layer.
