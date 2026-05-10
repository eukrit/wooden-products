"""CLI for the WPC fence calculator.

Examples:
  python -m scripts.fence-calculator.cli --bays 32 --type 2
  python -m scripts.fence-calculator.cli --bays 4 --type 3 --gates 1
  python -m scripts.fence-calculator.cli --bays 32 --type 2 --width 2.025
"""
from __future__ import annotations

import argparse
import sys

from calculator import FenceConfig, calculate


TYPE_MAP = {
    "2": {"bay_height_mm": 3000, "post_length_m": 3.0},
    "3": {"bay_height_mm": 2000, "post_length_m": 2.0},
}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="WPC fence BOM and FOB Guangzhou costing")
    p.add_argument("--bays", type=int, required=True, help="Number of fence bays/sets")
    p.add_argument("--type", choices=["2", "3"], required=True, help="Aolo Type 2 (3m H) or Type 3 (2m H)")
    p.add_argument("--width", choices=["2.0", "2.025"], default="2.0", help="Board/bay width in metres")
    p.add_argument("--gates", type=int, default=0, help="Number of 1.2m x 2.0m WPC gates")
    p.add_argument("--no-shipping", action="store_true", help="Exclude $515 local-to-Guangzhou shipping")
    p.add_argument("--ship-est", action="store_true", help="Also print estimated weight and bounding-box CBM")
    args = p.parse_args(argv)

    spec = TYPE_MAP[args.type]
    cfg = FenceConfig(
        bays=args.bays,
        bay_width_m=float(args.width),
        bay_height_mm=spec["bay_height_mm"],
        post_length_m=spec["post_length_m"],
        gates=args.gates,
    )
    quote = calculate(cfg, include_shipping=not args.no_shipping, include_shipping_estimate=args.ship_est)

    print(f"Type {args.type}: {args.bays} bays @ {args.width}m W x {spec['bay_height_mm']/1000}m H, {args.gates} gate(s)")
    print(f"Boards per bay: {quote.boards_per_bay()}  |  Posts: {cfg.bays + 1}")
    print()
    print(f"{'Item':<55} {'Qty':>6} {'Unit':>8} {'Total':>10}")
    print("-" * 81)
    for it in quote.items:
        print(f"{it.name:<55} {it.qty:>6} {it.unit_price_usd:>8.3f} {it.total_usd:>10.2f}")
    print("-" * 81)
    print(f"{'Subtotal (FOB Guangzhou)':<70} {quote.subtotal_usd:>10.2f}")
    if quote.shipping_usd:
        print(f"{'Local-to-Guangzhou shipping':<70} {quote.shipping_usd:>10.2f}")
    print(f"{'Total USD':<70} {quote.total_usd:>10.2f}")

    if quote.shipping_estimate:
        e = quote.shipping_estimate
        print()
        print("--- Estimated weight & CBM (NOT vendor-confirmed) ---")
        print(f"  Weight:    {e.weight_kg:>8.1f} kg")
        print(f"  CBM:       {e.cbm_m3:>8.3f} m^3")
        for n in e.notes:
            print(f"    - {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
