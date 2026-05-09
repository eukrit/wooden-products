"""WPC fence BOM and costing calculator.

Source of truth: scripts/firestore/upload_aolo_fence.py (Anhui Aolo PIs
GK20260402LJ and GK20260410LJ). Formulas derived from those PIs:

  Type 2  : 2.0m W x 3.0m H  -> 20 boards/bay, 32 bays -> 33 posts
  Type 3  : 2.0m W x 2.0m H  -> 13 boards/bay
  boards/bay = floor(H_mm / effective_face_mm)   where effective = 148mm
  posts      = bays + 1
  Each bay : 1 upper clamp, 1 lower cover, 4 L-connectors, 8 screws
  Each post: 1 cap, 1 iron pedestal, 4 expansion screws

No weight/CBM output: vendor density data is not in the repo and the
calculator refuses to fabricate it.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from typing import Literal

PARAMS_PATH = os.path.join(os.path.dirname(__file__), "fence_params.json")
BoardLength = Literal["2.000", "2.025"]
PostLength = Literal["2.0", "3.0"]


def load_params(path: str = PARAMS_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@dataclass(frozen=True)
class FenceConfig:
    bays: int
    bay_width_m: float           # 2.0 or 2.025 (= board length)
    bay_height_mm: int           # 2000 (Type 3) or 3000 (Type 2)
    post_length_m: float         # 2.0 (Type 3) or 3.0 (Type 2)
    gates: int = 0

    def __post_init__(self) -> None:
        if self.bays < 1:
            raise ValueError("bays must be >= 1")
        if self.bay_width_m not in (2.0, 2.025):
            raise ValueError("bay_width_m must be 2.0 or 2.025")
        if self.bay_height_mm not in (2000, 3000):
            raise ValueError("bay_height_mm must be 2000 or 3000")
        if self.post_length_m not in (2.0, 3.0):
            raise ValueError("post_length_m must be 2.0 or 3.0")
        if self.gates < 0:
            raise ValueError("gates must be >= 0")


@dataclass(frozen=True)
class LineItem:
    name: str
    qty: int
    unit_price_usd: float

    @property
    def total_usd(self) -> float:
        return round(self.qty * self.unit_price_usd, 2)


@dataclass(frozen=True)
class ShippingEstimate:
    """Estimated weight and bounding-box CBM. NOT vendor-confirmed."""
    weight_kg: float
    cbm_m3: float
    notes: list[str]


@dataclass(frozen=True)
class Quote:
    config: FenceConfig
    items: list[LineItem]
    subtotal_usd: float
    shipping_usd: float
    total_usd: float
    shipping_estimate: ShippingEstimate | None = None

    def boards_per_bay(self) -> int:
        params = load_params()
        return math.floor(self.config.bay_height_mm / params["board"]["effective_face_mm"])


def estimate_shipping(cfg: FenceConfig) -> ShippingEstimate:
    """Compute weight+CBM from board (published spec), post (physics), and a
    5% buffer for accessories. Returns explicit ShippingEstimate so callers
    can show users the assumptions, not just a number."""
    p = load_params()
    wcm = p["weight_cbm_model"]
    boards_per_bay = math.floor(cfg.bay_height_mm / p["board"]["effective_face_mm"])
    posts = cfg.bays + 1
    boards = cfg.bays * boards_per_bay

    bw_key = f"{cfg.bay_width_m:.3f}"
    pl_key = f"{cfg.post_length_m:.1f}".rstrip("0").rstrip(".")
    if cfg.post_length_m == 2.0:
        pl_key = "2.0"
    elif cfg.post_length_m == 3.0:
        pl_key = "3.0"

    board_kg = boards * wcm["board"]["kg_per_m"] * cfg.bay_width_m
    post_kg = posts * wcm["post"]["kg_per_m"] * cfg.post_length_m
    base_kg = board_kg + post_kg
    buffer_kg = base_kg * (wcm["accessories_buffer_pct"] / 100.0)
    gate_kg = cfg.gates * p["gate"]["_weight_kg_estimate"]
    total_kg = base_kg + buffer_kg + gate_kg

    board_cbm = boards * wcm["board"][f"cbm_per_board_{bw_key}"]
    post_cbm = posts * wcm["post"][f"cbm_per_post_{pl_key}"]
    gate_cbm = cfg.gates * p["gate"]["_cbm_estimate"]
    total_cbm = board_cbm + post_cbm + gate_cbm

    notes = [
        "Board weight: published spec 2.2 kg/m (manufacturer)",
        "Post weight: computed from 80x80x2mm alu hollow @ 2700 kg/m^3 (1.685 kg/m)",
        f"Accessories: bundled as +{wcm['accessories_buffer_pct']:.1f}% buffer over board+post weight",
        "CBM: bounding-box per item (board: 0.1615 x 0.020 x len; post: 0.080 x 0.080 x len)",
        "NOT vendor-confirmed — request actual packing list before booking freight.",
    ]
    return ShippingEstimate(
        weight_kg=round(total_kg, 1),
        cbm_m3=round(total_cbm, 3),
        notes=notes,
    )


def _key(width: float) -> BoardLength:
    return "2.000" if width == 2.0 else "2.025"


def calculate(cfg: FenceConfig, include_shipping: bool = True, include_shipping_estimate: bool = False) -> Quote:
    p = load_params()
    bw_key = _key(cfg.bay_width_m)
    pl_key = f"{cfg.post_length_m:.1f}".rstrip("0").rstrip(".")
    if cfg.post_length_m == 2.0:
        pl_key = "2.0"
    elif cfg.post_length_m == 3.0:
        pl_key = "3.0"

    boards_per_bay = math.floor(cfg.bay_height_mm / p["board"]["effective_face_mm"])
    posts = cfg.bays + 1
    boards = cfg.bays * boards_per_bay

    items: list[LineItem] = [
        LineItem(
            f"WPC Co-ex Fence Board {p['board']['sku']} ({cfg.bay_width_m}m)",
            boards,
            p["board"]["lengths"][bw_key]["unit_price_usd"],
        ),
        LineItem(
            f"Aluminium Post {p['post']['sku']} ({cfg.post_length_m}m)",
            posts,
            p["post"]["lengths"][pl_key]["unit_price_usd"],
        ),
    ]

    bay_acc = p["accessories_per_bay"]
    items.extend([
        LineItem(
            "Aluminium Upper Clamp Strip",
            cfg.bays * bay_acc["upper_clamp_strip"]["qty"],
            bay_acc["upper_clamp_strip"][f"unit_price_usd_{bw_key}"],
        ),
        LineItem(
            "Aluminium Lower Cover",
            cfg.bays * bay_acc["lower_cover"]["qty"],
            bay_acc["lower_cover"][f"unit_price_usd_{bw_key}"],
        ),
        LineItem(
            "L-shaped Connector",
            cfg.bays * bay_acc["l_connector"]["qty"],
            bay_acc["l_connector"]["unit_price_usd"],
        ),
        LineItem(
            "Steel Screws",
            cfg.bays * bay_acc["steel_screw"]["qty"],
            bay_acc["steel_screw"]["unit_price_usd"],
        ),
    ])

    post_acc = p["accessories_per_post"]
    items.extend([
        LineItem("Plastic Post Cap", posts * post_acc["post_cap"]["qty"], post_acc["post_cap"]["unit_price_usd"]),
        LineItem(
            f"Iron Pedestal {post_acc['iron_pedestal']['spec']}",
            posts * post_acc["iron_pedestal"]["qty"],
            post_acc["iron_pedestal"]["unit_price_usd"],
        ),
        LineItem(
            "Expansion Screws",
            posts * post_acc["expansion_screw"]["qty"],
            post_acc["expansion_screw"]["unit_price_usd"],
        ),
    ])

    if cfg.gates:
        items.append(LineItem(p["gate"]["sku"], cfg.gates, p["gate"]["unit_price_usd"]))

    subtotal = round(sum(i.total_usd for i in items), 2)
    shipping = p["shipping_local_to_guangzhou_usd"] if include_shipping else 0.0
    est = estimate_shipping(cfg) if include_shipping_estimate else None
    return Quote(
        config=cfg,
        items=items,
        subtotal_usd=subtotal,
        shipping_usd=shipping,
        total_usd=round(subtotal + shipping, 2),
        shipping_estimate=est,
    )
