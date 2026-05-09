"""Anhui Aolo WPC fence shipping calculator.

Compute bill-of-materials, weight, and shipping volume for arbitrary
configurations of GK161.50-20C co-extrusion fence panels.

See README.md for the derivation of the 150 mm effective plank face and
the post-count rule by layout.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

VALID_LAYOUTS = {"I", "L", "U", "detached"}


@dataclass
class FenceParams:
    plank_kg_per_m: float = 1.80
    post_kg_per_m: float = 1.20
    upper_kg_per_m: float = 0.45
    lower_kg_per_m: float = 0.55
    pedestal_kg_per_pc: float = 1.20
    cap_kg_per_pc: float = 0.05
    lconn_kg_per_pc: float = 0.03
    screw_kg_per_pc: float = 0.01
    upper_xsection_m2: float = 0.0015
    lower_xsection_m2: float = 0.0020
    packaging_overhead_pct: float = 0.08
    packing_factor: float = 1.25
    plank_face_mm: int = 150
    corner_extra_posts: int = 1


@dataclass
class BayConfig:
    height_m: float
    width_m: float
    bay_count: int
    gap_cm: float = 0.0
    layout: str = "I"
    runs: int = 1
    label: str = ""

    def __post_init__(self) -> None:
        if self.layout not in VALID_LAYOUTS:
            raise ValueError(
                f"layout must be one of {sorted(VALID_LAYOUTS)}, got {self.layout!r}"
            )
        if self.height_m <= 0 or self.width_m <= 0:
            raise ValueError("height_m and width_m must be positive")
        if self.bay_count <= 0:
            raise ValueError("bay_count must be positive")
        if self.gap_cm < 0:
            raise ValueError("gap_cm must be >= 0")
        if self.layout == "detached" and self.runs < 1:
            raise ValueError("detached layout requires runs >= 1")


def _post_count(cfg: BayConfig, params: FenceParams) -> int:
    N = cfg.bay_count
    if cfg.layout == "I":
        return N + 1
    if cfg.layout == "L":
        return N + 1 + params.corner_extra_posts
    if cfg.layout == "U":
        return N + 1 + 2 * params.corner_extra_posts
    return N + cfg.runs  # detached


def _planks_per_bay(height_m: float, gap_cm: float, plank_face_mm: int) -> int:
    H_mm = height_m * 1000
    G_mm = gap_cm * 10
    return int(math.floor((H_mm + G_mm) / (plank_face_mm + G_mm)))


def calculate_one(cfg: BayConfig, params: FenceParams) -> dict[str, Any]:
    planks_per_bay = _planks_per_bay(cfg.height_m, cfg.gap_cm, params.plank_face_mm)
    N = cfg.bay_count
    n_posts = _post_count(cfg, params)

    bom = {
        "planks_per_bay": planks_per_bay,
        "n_planks": N * planks_per_bay,
        "n_posts": n_posts,
        "n_caps": n_posts,
        "n_pedestals": n_posts,
        "n_upper_clamp": N,
        "n_lower_cover": N,
        "n_lconn": 4 * N,
        "n_screw_connector": 8 * N,
        "n_screw_expansion": 4 * n_posts,
        "n_screw_self_drill": 8 * n_posts,
    }

    linear = {
        "m_plank": bom["n_planks"] * cfg.width_m,
        "m_post": bom["n_posts"] * cfg.height_m,
        "m_upper": bom["n_upper_clamp"] * cfg.width_m,
        "m_lower": bom["n_lower_cover"] * cfg.width_m,
    }

    weight_kg = {
        "kg_plank": linear["m_plank"] * params.plank_kg_per_m,
        "kg_post": linear["m_post"] * params.post_kg_per_m,
        "kg_upper": linear["m_upper"] * params.upper_kg_per_m,
        "kg_lower": linear["m_lower"] * params.lower_kg_per_m,
        "kg_pedestal": bom["n_pedestals"] * params.pedestal_kg_per_pc,
        "kg_cap": bom["n_caps"] * params.cap_kg_per_pc,
        "kg_lconn": bom["n_lconn"] * params.lconn_kg_per_pc,
        "kg_screws": (
            bom["n_screw_connector"]
            + bom["n_screw_expansion"]
            + bom["n_screw_self_drill"]
        )
        * params.screw_kg_per_pc,
    }
    net_kg = sum(weight_kg.values())
    gross_kg = net_kg * (1 + params.packaging_overhead_pct)

    volume_m3 = {
        "v_plank": bom["n_planks"] * cfg.width_m * 0.1615 * 0.020,
        "v_post": bom["n_posts"] * cfg.height_m * 0.080 * 0.080,
        "v_upper": linear["m_upper"] * params.upper_xsection_m2,
        "v_lower": linear["m_lower"] * params.lower_xsection_m2,
        "v_pedestal": bom["n_pedestals"] * 0.035 * 0.035 * 0.5,
        "v_cap": bom["n_caps"] * 0.00008,
        "v_lconn": bom["n_lconn"] * 0.00005,
    }
    raw_cbm = sum(volume_m3.values())
    shipping_cbm = raw_cbm * params.packing_factor

    return {
        "config": asdict(cfg),
        "bom": bom,
        "linear_m": linear,
        "weight_kg": weight_kg,
        "net_kg": net_kg,
        "gross_kg": gross_kg,
        "volume_m3": volume_m3,
        "raw_cbm": raw_cbm,
        "shipping_cbm": shipping_cbm,
    }


def calculate(configs: list[BayConfig], params: FenceParams) -> dict[str, Any]:
    line_items = [calculate_one(c, params) for c in configs]
    totals = {
        "net_kg": sum(item["net_kg"] for item in line_items),
        "gross_kg": sum(item["gross_kg"] for item in line_items),
        "raw_cbm": sum(item["raw_cbm"] for item in line_items),
        "shipping_cbm": sum(item["shipping_cbm"] for item in line_items),
        "n_planks": sum(item["bom"]["n_planks"] for item in line_items),
        "n_posts": sum(item["bom"]["n_posts"] for item in line_items),
    }
    return {"line_items": line_items, "totals": totals}


def load_params(path: Path | None) -> tuple[FenceParams, list[str]]:
    """Load params from JSON. Returns (params, list_of_placeholder_notes_present)."""
    if path is None:
        path = Path(__file__).parent / "fence_params.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    placeholder_notes = [k for k in data if k.startswith("_") and k.endswith("_note")]
    clean = {k: v for k, v in data.items() if not k.startswith("_")}
    valid_fields = set(FenceParams.__dataclass_fields__)
    filtered = {k: v for k, v in clean.items() if k in valid_fields}
    return FenceParams(**filtered), placeholder_notes


def load_configs(path: Path) -> list[BayConfig]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = [data]
    return [BayConfig(**row) for row in data]


def _format_table(result: dict[str, Any]) -> str:
    lines = []
    for i, item in enumerate(result["line_items"], 1):
        cfg = item["config"]
        label = cfg.get("label") or f"line {i}"
        lines.append(f"--- {label} ---")
        lines.append(
            f"  config: H={cfg['height_m']}m  W={cfg['width_m']}m  "
            f"gap={cfg['gap_cm']}cm  bays={cfg['bay_count']}  "
            f"layout={cfg['layout']}  runs={cfg['runs']}"
        )
        bom = item["bom"]
        lin = item["linear_m"]
        lines.append(f"  planks_per_bay = {bom['planks_per_bay']}")
        lines.append(f"  n_planks = {bom['n_planks']}   n_posts = {bom['n_posts']}")
        lines.append(f"  n_upper_clamp = {bom['n_upper_clamp']}   n_lower_cover = {bom['n_lower_cover']}")
        lines.append(
            f"  n_pedestals = {bom['n_pedestals']}   n_caps = {bom['n_caps']}   "
            f"n_lconn = {bom['n_lconn']}"
        )
        lines.append(
            f"  screws: connector={bom['n_screw_connector']}  "
            f"expansion={bom['n_screw_expansion']}  self_drill={bom['n_screw_self_drill']}"
        )
        lines.append(
            f"  linear: m_plank={lin['m_plank']:.3f} m   m_post={lin['m_post']:.3f} m   "
            f"m_upper={lin['m_upper']:.3f} m   m_lower={lin['m_lower']:.3f} m"
        )
        lines.append(f"  net_kg = {item['net_kg']:.2f}   gross_kg = {item['gross_kg']:.2f}")
        lines.append(f"  raw_cbm = {item['raw_cbm']:.4f}   shipping_cbm = {item['shipping_cbm']:.4f}")
    t = result["totals"]
    lines.append("=== TOTALS ===")
    lines.append(f"  n_planks = {t['n_planks']}   n_posts = {t['n_posts']}")
    lines.append(f"  net_kg = {t['net_kg']:.2f}   gross_kg = {t['gross_kg']:.2f}")
    lines.append(f"  raw_cbm = {t['raw_cbm']:.4f}   shipping_cbm = {t['shipping_cbm']:.4f}")
    return "\n".join(lines)


def _sweep(params: FenceParams) -> list[dict[str, Any]]:
    heights = [1.5, 2.0, 2.5, 3.0]
    widths = [1.5, 1.8, 2.0, 2.9]
    gaps = [1, 5, 10, 15]
    rows = []
    for H, W, g in itertools.product(heights, widths, gaps):
        cfg = BayConfig(height_m=H, width_m=W, gap_cm=g, bay_count=1, layout="I")
        res = calculate_one(cfg, params)
        rows.append({
            "height_m": H, "width_m": W, "gap_cm": g,
            "planks_per_bay": res["bom"]["planks_per_bay"],
            "n_posts": res["bom"]["n_posts"],
            "m_plank": round(res["linear_m"]["m_plank"], 3),
            "m_post": round(res["linear_m"]["m_post"], 3),
            "net_kg": round(res["net_kg"], 2),
            "gross_kg": round(res["gross_kg"], 2),
            "raw_cbm": round(res["raw_cbm"], 4),
            "shipping_cbm": round(res["shipping_cbm"], 4),
        })
    return rows


def _assert_sweep_monotonicity(rows: list[dict[str, Any]]) -> None:
    by_key: dict[tuple, list[dict]] = {}
    for r in rows:
        assert r["planks_per_bay"] > 0, f"no planks at {r}"
        assert r["shipping_cbm"] > 0, f"no CBM at {r}"
        by_key.setdefault((r["width_m"], r["gap_cm"]), []).append(r)
    for _, items in by_key.items():
        items.sort(key=lambda x: x["height_m"])
        planks = [i["planks_per_bay"] for i in items]
        assert planks == sorted(planks), f"planks not monotonic in H: {items}"

    by_key = {}
    for r in rows:
        by_key.setdefault((r["height_m"], r["width_m"]), []).append(r)
    for _, items in by_key.items():
        items.sort(key=lambda x: x["gap_cm"])
        planks = [i["planks_per_bay"] for i in items]
        assert planks == sorted(planks, reverse=True), f"planks not monotonic in gap: {items}"


def _write_sweep_csv(rows: list[dict[str, Any]], out: Path) -> None:
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Anhui Aolo WPC fence shipping calculator")
    parser.add_argument("--config", type=Path, help="JSON file with BayConfig list")
    parser.add_argument("--params", type=Path, help="JSON params file (default: fence_params.json)")
    parser.add_argument("--allow-placeholders", action="store_true",
                        help="Allow computation even if fence_params.json still has _note fields")
    parser.add_argument("--json", action="store_true",
                        help="Emit full result as JSON instead of table")
    parser.add_argument("--sweep-csv", type=Path,
                        help="Write 64-row H/W/gap parameter sweep to this CSV and exit")
    args = parser.parse_args(argv)

    params, placeholders = load_params(args.params)

    if args.sweep_csv:
        rows = _sweep(params)
        _assert_sweep_monotonicity(rows)
        _write_sweep_csv(rows, args.sweep_csv)
        print(f"wrote {len(rows)} rows to {args.sweep_csv}")
        return 0

    if not args.config:
        parser.error("--config is required (or use --sweep-csv)")

    if placeholders and not args.allow_placeholders:
        print(
            "ERROR: fence_params.json contains placeholder TODO notes; "
            "real vendor densities not yet confirmed.\n"
            f"  Unresolved: {', '.join(placeholders)}\n"
            "Pass --allow-placeholders to compute anyway (for dev/testing only).",
            file=sys.stderr,
        )
        return 2

    configs = load_configs(args.config)
    result = calculate(configs, params)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(_format_table(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
