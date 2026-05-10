"""WPC fence BOM and costing calculator.

Source of truth: scripts/firestore/upload_aolo_fence.py (Anhui Aolo PIs
GK20260402LJ and GK20260410LJ). Formulas derived from those PIs:

  Type 2  : 2.0m W x 3.0m H  -> 20 boards/bay, 32 bays -> 33 posts
  Type 3  : 2.0m W x 2.0m H  -> 13 boards/bay
  boards/bay = floor(H_mm / effective_face_mm)   where effective = 148mm
  posts      = bays + 1
  Each bay : 1 upper clamp, 1 lower cover, 4 L-connectors, 8 screws
  Each post: 1 cap, 1 iron pedestal, 4 expansion screws

Pricing model:
  - Boards/posts at the exact widths/lengths in the PI use the exact PI
    unit prices.
  - Other widths/lengths use $/m rates (board $2.20/m, post $11.80/m,
    consistent across both PI samples).
  - Accessories that have width-keyed prices ($/2.0m vs $/2.025m) fall
    back to the closer key with a `width_substituted` warning.

Weight/CBM are estimates: board uses manufacturer's published spec
(2.2 kg/m), post is computed from physics (80x80x2mm alu hollow), and
accessories are bundled as a 5% buffer. Output always carries a
"NOT vendor-confirmed" caveat.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Optional

PARAMS_PATH = os.path.join(os.path.dirname(__file__), "fence_params.json")

# PI-exact width/length combinations: prices are tested against the PIs.
_PI_WIDTHS = (2.0, 2.025)
_PI_POST_LENGTHS = (2.0, 3.0)


def load_params(path: str = PARAMS_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@dataclass(frozen=True)
class FenceConfig:
    """Bay configuration.

    For PI-exact line items pass:
      bays, bay_width_m=2.0|2.025, bay_height_mm=2000|3000, post_length_m=2.0|3.0

    For configurator/free-form use any of:
      0.5 <= bay_width_m <= 4.0
      600 <= bay_height_mm <= 3000
      post_length_m=None (auto-pick: 2.0 if H<=2000 else 3.0)
    """
    bays: int
    bay_width_m: float
    bay_height_mm: int
    post_length_m: Optional[float] = None
    gates: int = 0

    def __post_init__(self) -> None:
        if self.bays < 1:
            raise ValueError("bays must be >= 1")
        if not (0.5 <= self.bay_width_m <= 4.0):
            raise ValueError("bay_width_m must be in [0.5, 4.0] m")
        if not (600 <= self.bay_height_mm <= 3000):
            raise ValueError("bay_height_mm must be in [600, 3000]")
        if self.post_length_m is None:
            object.__setattr__(self, "post_length_m", 2.0 if self.bay_height_mm <= 2000 else 3.0)
        if not (1.5 <= self.post_length_m <= 4.0):  # type: ignore[operator]
            raise ValueError("post_length_m must be in [1.5, 4.0] m")
        if self.post_length_m * 1000 < self.bay_height_mm:  # type: ignore[operator]
            raise ValueError("post_length_m must be >= bay_height_mm")
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
    shipping_estimate: Optional[ShippingEstimate] = None
    warnings: list[str] = field(default_factory=list)

    def boards_per_bay(self) -> int:
        params = load_params()
        return math.floor(self.config.bay_height_mm / params["board"]["effective_face_mm"])


def _board_unit_price(p: dict, bay_width_m: float, warnings: list[str]) -> float:
    bw_key = f"{bay_width_m:.3f}"
    lengths = p["board"]["lengths"]
    if bw_key in lengths:
        return lengths[bw_key]["unit_price_usd"]
    rate = p["board"]["unit_price_usd_per_m"]
    warnings.append(
        f"Board width {bay_width_m:.3f}m has no PI quote; priced at "
        f"${rate:.2f}/m -> ${rate * bay_width_m:.3f}/board (interpolated)."
    )
    return round(rate * bay_width_m, 4)


def _post_unit_price(p: dict, post_length_m: float, warnings: list[str]) -> float:
    pl_key = f"{post_length_m:.1f}"
    lengths = p["post"]["lengths"]
    if pl_key in lengths:
        return lengths[pl_key]["unit_price_usd"]
    rate = p["post"]["unit_price_usd_per_m"]
    warnings.append(
        f"Post length {post_length_m:.2f}m has no PI quote; priced at "
        f"${rate:.2f}/m -> ${rate * post_length_m:.3f}/post (interpolated)."
    )
    return round(rate * post_length_m, 4)


def _bay_acc_price(acc: dict, bay_width_m: float, warnings: list[str], acc_label: str) -> float:
    """Width-keyed accessory price (clamp strip / lower cover). Falls back
    to the closer of 2.000/2.025 with a substitution warning."""
    bw_key = f"{bay_width_m:.3f}"
    direct = acc.get(f"unit_price_usd_{bw_key}")
    if direct is not None:
        return direct
    nearest = min(_PI_WIDTHS, key=lambda w: abs(w - bay_width_m))
    nearest_key = f"{nearest:.3f}"
    price = acc[f"unit_price_usd_{nearest_key}"]
    warnings.append(
        f"{acc_label}: no PI price at {bay_width_m:.3f}m; using "
        f"{nearest_key}m price (${price:.2f}) as nearest."
    )
    return price


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
    pl_key = f"{cfg.post_length_m:.1f}"

    board_kg = boards * wcm["board"]["kg_per_m"] * cfg.bay_width_m
    post_kg = posts * wcm["post"]["kg_per_m"] * cfg.post_length_m  # type: ignore[operator]
    base_kg = board_kg + post_kg
    buffer_kg = base_kg * (wcm["accessories_buffer_pct"] / 100.0)
    gate_kg = cfg.gates * p["gate"]["_weight_kg_estimate"]
    total_kg = base_kg + buffer_kg + gate_kg

    # CBM: use exact PI bounding boxes when available, otherwise compute
    # bounding box from raw section dimensions.
    board_cbm_per = wcm["board"].get(f"cbm_per_board_{bw_key}")
    if board_cbm_per is None:
        board_cbm_per = (p["board"]["width_mm"] / 1000.0) * (p["board"]["thickness_mm"] / 1000.0) * cfg.bay_width_m
    board_cbm = boards * board_cbm_per

    post_cbm_per = wcm["post"].get(f"cbm_per_post_{pl_key}")
    if post_cbm_per is None:
        post_cbm_per = 0.080 * 0.080 * cfg.post_length_m  # type: ignore[operator]
    post_cbm = posts * post_cbm_per

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


def calculate(cfg: FenceConfig, include_shipping: bool = True, include_shipping_estimate: bool = False) -> Quote:
    p = load_params()
    warnings: list[str] = []

    boards_per_bay = math.floor(cfg.bay_height_mm / p["board"]["effective_face_mm"])
    posts = cfg.bays + 1
    boards = cfg.bays * boards_per_bay
    post_length_m: float = cfg.post_length_m  # type: ignore[assignment]

    items: list[LineItem] = [
        LineItem(
            f"WPC Co-ex Fence Board {p['board']['sku']} ({cfg.bay_width_m}m)",
            boards,
            _board_unit_price(p, cfg.bay_width_m, warnings),
        ),
        LineItem(
            f"Aluminium Post {p['post']['sku']} ({post_length_m}m)",
            posts,
            _post_unit_price(p, post_length_m, warnings),
        ),
    ]

    bay_acc = p["accessories_per_bay"]
    items.extend([
        LineItem(
            "Aluminium Upper Clamp Strip",
            cfg.bays * bay_acc["upper_clamp_strip"]["qty"],
            _bay_acc_price(bay_acc["upper_clamp_strip"], cfg.bay_width_m, warnings, "Upper clamp"),
        ),
        LineItem(
            "Aluminium Lower Cover",
            cfg.bays * bay_acc["lower_cover"]["qty"],
            _bay_acc_price(bay_acc["lower_cover"], cfg.bay_width_m, warnings, "Lower cover"),
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
        warnings=warnings,
    )
