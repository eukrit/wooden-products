"""Regression tests against the three reference Proforma Invoices."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fence_shipping_calculator import (  # noqa: E402
    BayConfig,
    FenceParams,
    _planks_per_bay,
    calculate_one,
)


@pytest.fixture
def params() -> FenceParams:
    return FenceParams()


def test_planks_per_bay_formula_matches_pis(params):
    assert _planks_per_bay(1.5, 0.0, params.plank_face_mm) == 10
    assert _planks_per_bay(3.0, 0.0, params.plank_face_mm) == 20
    assert _planks_per_bay(2.0, 0.0, params.plank_face_mm) == 13


def test_gap_reduces_plank_count(params):
    assert _planks_per_bay(2.0, 15.0, params.plank_face_mm) < _planks_per_bay(
        2.0, 1.0, params.plank_face_mm
    )


def test_type2_32sets_matches_pi(params):
    cfg = BayConfig(height_m=3.0, width_m=2.0, gap_cm=0, bay_count=32, layout="I")
    r = calculate_one(cfg, params)
    assert r["bom"]["planks_per_bay"] == 20
    assert r["bom"]["n_planks"] == 640
    assert r["bom"]["n_posts"] == 33
    assert r["bom"]["n_upper_clamp"] == 32
    assert r["bom"]["n_lower_cover"] == 32
    assert r["bom"]["n_pedestals"] == 33
    assert r["bom"]["n_lconn"] == 32 * 4
    assert r["bom"]["n_screw_connector"] == 32 * 4 * 2
    assert r["bom"]["n_screw_expansion"] == 33 * 4
    assert r["linear_m"]["m_plank"] == pytest.approx(1280.0)
    assert r["linear_m"]["m_post"] == pytest.approx(99.0)


def test_type3_6sets_matches_pi(params):
    cfg = BayConfig(height_m=2.0, width_m=2.0, gap_cm=0, bay_count=6, layout="I")
    r = calculate_one(cfg, params)
    assert r["bom"]["planks_per_bay"] == 13
    assert r["bom"]["n_planks"] == 78
    assert r["bom"]["n_posts"] == 7
    assert r["bom"]["n_upper_clamp"] == 6
    assert r["bom"]["n_pedestals"] == 7
    assert r["linear_m"]["m_plank"] == pytest.approx(156.0)
    assert r["linear_m"]["m_post"] == pytest.approx(14.0)


def test_low_41sets_matches_pi(params):
    cfg = BayConfig(height_m=1.5, width_m=2.0, gap_cm=0, bay_count=41, layout="I")
    r = calculate_one(cfg, params)
    assert r["bom"]["planks_per_bay"] == 10
    assert r["bom"]["n_planks"] == 410
    assert r["bom"]["n_posts"] == 42
    assert r["linear_m"]["m_plank"] == pytest.approx(820.0)
    assert r["linear_m"]["m_post"] == pytest.approx(63.0)


def test_layouts_shift_post_count(params):
    N = 10
    base = BayConfig(height_m=2.0, width_m=2.0, gap_cm=0, bay_count=N, layout="I")
    L = BayConfig(height_m=2.0, width_m=2.0, gap_cm=0, bay_count=N, layout="L")
    U = BayConfig(height_m=2.0, width_m=2.0, gap_cm=0, bay_count=N, layout="U")
    detached = BayConfig(
        height_m=2.0, width_m=2.0, gap_cm=0, bay_count=N, layout="detached", runs=3
    )
    assert calculate_one(base, params)["bom"]["n_posts"] == N + 1
    assert calculate_one(L, params)["bom"]["n_posts"] == N + 1 + params.corner_extra_posts
    assert calculate_one(U, params)["bom"]["n_posts"] == N + 1 + 2 * params.corner_extra_posts
    assert calculate_one(detached, params)["bom"]["n_posts"] == N + 3


def test_invalid_layout_rejected():
    with pytest.raises(ValueError):
        BayConfig(height_m=2.0, width_m=2.0, bay_count=1, layout="Z")


def test_weight_scales_with_density():
    cfg = BayConfig(height_m=2.0, width_m=2.0, gap_cm=0, bay_count=6, layout="I")
    p1 = FenceParams()
    p2 = FenceParams(plank_kg_per_m=p1.plank_kg_per_m * 2)
    r1 = calculate_one(cfg, p1)
    r2 = calculate_one(cfg, p2)
    assert r2["weight_kg"]["kg_plank"] == pytest.approx(r1["weight_kg"]["kg_plank"] * 2)
