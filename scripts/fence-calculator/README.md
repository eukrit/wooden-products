# Fence Shipping Calculator — Anhui Aolo WPC (profile `GK161.50-20C`)

Estimates bill-of-materials, weight, and shipping volume for arbitrary
configurations of Anhui Aolo co-extrusion WPC fence panels. Single
pure-Python module, no external dependencies.

## Inputs

Per bay configuration:

| Field         | Type    | Notes                                                |
| ------------- | ------- | ---------------------------------------------------- |
| `height_m`    | float   | Fence height (typ. 1.5 / 2.0 / 2.5 / 3.0)            |
| `width_m`     | float   | Bay width = plank length (typ. 1.5 / 1.8 / 2.0 / 2.9)|
| `bay_count`   | int     | Number of bays of this config                        |
| `gap_cm`      | float   | Inter-plank gap in cm (1–15; 0 = tongue-and-groove)  |
| `layout`      | str     | `"I"`, `"L"`, `"U"`, or `"detached"`                 |
| `runs`        | int     | Only for `detached`: number of disconnected runs     |
| `label`       | str     | Free text for table output                           |

Parameters live in `fence_params.json`. All `_*_note` keys are placeholder
guards — the CLI refuses to print weights/CBM while any are present
unless `--allow-placeholders` is passed.

## Formula derivation

### Planks per bay
```
planks_per_bay = floor((H_mm + G_mm) / (plank_face_mm + G_mm))
```
Effective plank face = 150 mm (nominal 161.5 mm − 11.5 mm tongue overlap).
Verified against three Proforma Invoices.

### Posts by layout
| Layout       | Formula                                    |
| ------------ | ------------------------------------------ |
| `I`          | `bays + 1`                                 |
| `L`          | `bays + 1 + corner_extra_posts`            |
| `U`          | `bays + 1 + 2 * corner_extra_posts`        |
| `detached`   | `bays + runs`                              |

## Usage

```bash
# Single config
python fence_shipping_calculator.py \
  --config tests/fixtures/type2_32sets.json --allow-placeholders

# 64-case sweep
python fence_shipping_calculator.py \
  --sweep-csv sample_matrix.csv --allow-placeholders

# Tests
pytest tests/
```

## Replacing placeholder densities

1. Get unit weights from Anhui Aolo (Jackson).
2. Update numeric values in `fence_params.json`.
3. **Delete the matching `_*_note` keys** so the CLI stops blocking.
4. Commit numeric change + note removal in the same commit.
