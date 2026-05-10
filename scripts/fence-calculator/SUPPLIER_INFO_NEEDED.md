# What we need from each supplier to add their fence to the calculator

Use this checklist when sourcing pricing from a new vendor (Jackson for Heritage,
or any non-Aolo supplier). The calculator will only emit numbers it can defend
against vendor data — anything missing turns into an explicit "interpolated"
warning, or blocks output entirely if it's a hard requirement.

---

## 1. Hard requirements (cost will not compute without these)

### a. A real Proforma Invoice (or two) with line items

For each board / post / gate / accessory line we need:
- SKU / vendor code
- Length or unit (m or piece)
- Quantity ordered
- Unit price (USD preferred; if CNY/THB, give us the FX date and rate)
- Line total

One PI with 30+ bays exercises every line item. Two PIs at different bay sizes
let us derive per-meter rates — if the per-meter price is consistent across
both, we can extrapolate to non-quoted sizes.

> *Aolo example*: PIs `GK20260402LJ` (32 sets × 2.0m × 3.0m) and `GK20260410LJ`
> (32 sets × 2.025m × 3.0m). Board $4.40/2.0m and $4.455/2.025m → both equal
> $2.20/m, so we use $2.20/m for any other width.

### b. Effective board face (mm)

The width that one board *covers* on the fence — width minus tongue overlap.
Used for `boards_per_bay = floor(height_mm / effective_face_mm)`.

> *Aolo*: 161.5 mm board − 13.5 mm overlap = 148 mm effective face.
> Confirmed against 20 boards / 3.0 m bay = 150 mm/board ≈ 148 mm + tolerance.

### c. Post selection rule

Which post lengths are standard, and how the post gets picked from fence
height. (We currently auto-pick 2.0 m post for H ≤ 2000 mm, 3.0 m otherwise.)
If your supplier offers 2.5 m or 3.5 m posts too, tell us.

### d. Per-bay and per-post accessory counts

Anhui Aolo uses:
- Per bay: 1 upper clamp strip, 1 lower cover, 4 L-connectors, 8 steel screws
- Per post: 1 cap, 1 iron pedestal, 4 expansion screws

If the new system installs differently (e.g. snap-fit instead of screws, no
pedestal because it's surface-mount), say so and give the new counts.

---

## 2. Soft requirements (the calculator will work without these but ship
estimates will be stamped "NOT vendor-confirmed" until they land)

### a. Board weight in kg/m

Either a manufacturer-published spec (best) or sample weighing of one full
board with length and weight. We'd use: `kg_per_m = weight / length`.

> *Aolo*: 2.2 kg/m (published in the catalog `website/PROMPT.md`).

### b. Post wall thickness (if hollow) OR post weight in kg/m

For hollow aluminium posts we currently compute `kg/m = (outer² − inner²) ×
density`. If your supplier publishes a weight directly, use that — beats
our 80 × 80 × 2 mm wall assumption.

> *Aolo*: 1.685 kg/m computed (80x80 hollow, 2 mm wall, 2700 kg/m³).

### c. Gate weight (kg) and bounding-box dimensions

We currently estimate the 1.2 m × 2.0 m gate at 35 kg / 0.06 m³. Vendor
spec sheet would replace both.

### d. Accessory weights (only if you want sub-5% accuracy)

We bundle clamps + covers + connectors + screws + caps + pedestals + expansion
screws into a flat 5% buffer over board+post weight. That's accurate within
maybe ±2 kg on a typical kit. If you want exact, we need each accessory's
weight in kg/piece. Otherwise leave it.

---

## 3. Nice-to-have (would unlock new features)

### a. Standard packaging — boards per crate / pallet

Lets us output container counts (20 ft / 40 ft / 40 HQ) instead of just CBM.

### b. Real-vehicle CBM per packaged unit

Bounding-box CBM overestimates because boards bundle tighter than their
section dictates. A vendor "1 crate = X boards = Y kg = Z m³" line would
let us swap from bounding-box to packed CBM.

### c. Local-to-port trucking cost

Aolo charges $515 from their factory to FOB Guangzhou. New vendors may
have a different number, or it may already be folded into the FOB price.

### d. FOB port

Aolo ships FOB Guangzhou. Other suppliers may use Shanghai, Ningbo, etc.
Affects sea-freight quotes downstream but not the calculator itself.

### e. Vendor identity for the params file

- Vendor name + slug (e.g. `jackson`, `anhui-aolo`)
- Slack channel for PI delivery (e.g. `#vendor-anhui-aolo-wpc`)
- Account contact / sales rep

---

## 4. The fastest path to "Heritage in the calculator"

Send a **single PI for any Heritage fence configuration** that includes:
- 1 board line (qty, unit price, length)
- 1 post line (qty, unit price, length)
- 1 line each for clamp, cover, connector, screw, cap, pedestal, expansion
  screw — even if some are bundled into the board price, list them for clarity
- (Optional) gate line

Plus the spec sheet showing **board face width in mm** and **post wall
thickness or kg/m**. From that one PI we can pin every line item the same
way we did for Aolo, and you'll see a Heritage option in the configurator
the same week the PI lands.

---

## 5. What we will NOT do without vendor data

- Make up densities to produce weight numbers.
- Extrapolate prices from "similar" SKUs across vendors.
- Quote container counts off bounding-box CBM (always understates packing).
- Compute Thai retail prices without an FX rate timestamp.

The calculator already refuses to print weight when called with placeholder
densities; we'll keep that behavior for any new vendor.
