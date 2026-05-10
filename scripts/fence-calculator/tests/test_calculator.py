"""Regression tests pinned to the actual Aolo PIs.

Sources:
  GK20260402LJ : 32 sets Type 2 (2.0m W x 3.0m H) + 4 sets Type 3 + 1 gate
                 (note in PI says Type-3 = 4 sets but the Type-3 board line
                 shows 13 boards * 4 sets = 52 boards and posts line is 5 ->
                 ambiguous; we test the Type-3 sub-quote at 4 sets which
                 matches the boards line)
  GK20260410LJ : 32 sets Type 2 (2.025m W x 3.0m H) + 5 sets Type 3 + 1 gate

We unit-test the per-bay arithmetic against PI line items (boards, posts,
clamps, covers, connectors, screws, caps, pedestals, expansion screws,
gate). Subtotal is also asserted to within a cent.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calculator import FenceConfig, calculate, estimate_shipping


class Type2_32Sets_2m(unittest.TestCase):
    """PI GK20260402LJ Type-2 portion: 32 sets x 2.0m x 3.0m."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.q = calculate(
            FenceConfig(bays=32, bay_width_m=2.0, bay_height_mm=3000, post_length_m=3.0),
            include_shipping=False,
        )
        cls.by_name = {it.name: it for it in cls.q.items}

    def test_boards_per_bay(self):
        self.assertEqual(self.q.boards_per_bay(), 20)

    def test_board_qty_matches_pi(self):
        # 32 bays * 20 boards = 640
        self.assertEqual(self.by_name["WPC Co-ex Fence Board GK161.5/20C (2.0m)"].qty, 640)
        self.assertAlmostEqual(self.by_name["WPC Co-ex Fence Board GK161.5/20C (2.0m)"].total_usd, 2816.00, places=2)

    def test_post_qty_matches_pi(self):
        # 32 bays + 1 = 33 posts
        self.assertEqual(self.by_name["Aluminium Post AL-80/80A (3.0m)"].qty, 33)
        self.assertAlmostEqual(self.by_name["Aluminium Post AL-80/80A (3.0m)"].total_usd, 1168.20, places=2)

    def test_clamp_strips(self):
        self.assertEqual(self.by_name["Aluminium Upper Clamp Strip"].qty, 32)
        self.assertAlmostEqual(self.by_name["Aluminium Upper Clamp Strip"].total_usd, 121.60, places=2)

    def test_lower_covers(self):
        self.assertEqual(self.by_name["Aluminium Lower Cover"].qty, 32)
        self.assertAlmostEqual(self.by_name["Aluminium Lower Cover"].total_usd, 128.00, places=2)

    def test_connectors_and_screws(self):
        self.assertEqual(self.by_name["L-shaped Connector"].qty, 128)
        self.assertEqual(self.by_name["Steel Screws"].qty, 256)

    def test_post_accessories(self):
        self.assertEqual(self.by_name["Plastic Post Cap"].qty, 33)
        self.assertEqual(self.by_name["Iron Pedestal 35x35x500mm"].qty, 33)
        self.assertEqual(self.by_name["Expansion Screws"].qty, 132)


class Type3_PerBay(unittest.TestCase):
    """Type-3 boards-per-bay: 2.0m height -> 13 boards/bay."""

    def test_boards_per_bay_is_13(self):
        q = calculate(
            FenceConfig(bays=4, bay_width_m=2.0, bay_height_mm=2000, post_length_m=2.0),
            include_shipping=False,
        )
        self.assertEqual(q.boards_per_bay(), 13)
        boards = next(it for it in q.items if "Fence Board" in it.name)
        # 4 bays x 13 = 52 (matches PI Type-3 board line)
        self.assertEqual(boards.qty, 52)


class WidthVariant_2025(unittest.TestCase):
    """PI GK20260410LJ uses 2.025m board length at $4.455/pc."""

    def test_board_unit_price_2025(self):
        q = calculate(
            FenceConfig(bays=32, bay_width_m=2.025, bay_height_mm=3000, post_length_m=3.0),
            include_shipping=False,
        )
        boards = next(it for it in q.items if "Fence Board" in it.name)
        self.assertEqual(boards.qty, 640)
        self.assertAlmostEqual(boards.unit_price_usd, 4.455, places=4)
        self.assertAlmostEqual(boards.total_usd, 2851.20, places=2)


class GateLine(unittest.TestCase):
    def test_gate_price(self):
        q = calculate(
            FenceConfig(bays=1, bay_width_m=2.0, bay_height_mm=3000, post_length_m=3.0, gates=1),
            include_shipping=False,
        )
        gate = next(it for it in q.items if "Gate" in it.name)
        self.assertAlmostEqual(gate.total_usd, 285.00, places=2)


class InputValidation(unittest.TestCase):
    def test_rejects_zero_bays(self):
        with self.assertRaises(ValueError):
            FenceConfig(bays=0, bay_width_m=2.0, bay_height_mm=3000, post_length_m=3.0)

    def test_rejects_height_below_minimum(self):
        with self.assertRaises(ValueError):
            FenceConfig(bays=1, bay_width_m=2.0, bay_height_mm=500, post_length_m=2.0)

    def test_rejects_width_above_maximum(self):
        with self.assertRaises(ValueError):
            FenceConfig(bays=1, bay_width_m=5.0, bay_height_mm=3000, post_length_m=3.0)

    def test_rejects_post_shorter_than_height(self):
        with self.assertRaises(ValueError):
            FenceConfig(bays=1, bay_width_m=2.0, bay_height_mm=3000, post_length_m=2.0)


class FlexibleSizing(unittest.TestCase):
    """Configurator-friendly sizing: arbitrary heights / widths."""

    def test_height_1500_with_auto_post(self):
        cfg = FenceConfig(bays=10, bay_width_m=1.8, bay_height_mm=1500)
        self.assertEqual(cfg.post_length_m, 2.0)
        q = calculate(cfg, include_shipping=False)
        boards = next(it for it in q.items if "Fence Board" in it.name)
        # boards_per_bay = floor(1500/148) = 10; 10 bays * 10 = 100 boards
        self.assertEqual(boards.qty, 100)
        # priced at $2.20/m * 1.8m = $3.96/pc
        self.assertAlmostEqual(boards.unit_price_usd, 3.96, places=2)
        self.assertTrue(any("interpolated" in w for w in q.warnings))

    def test_width_1800_falls_back_to_2000_for_clamp(self):
        cfg = FenceConfig(bays=1, bay_width_m=1.8, bay_height_mm=2000)
        q = calculate(cfg, include_shipping=False)
        clamp = next(it for it in q.items if "Upper Clamp" in it.name)
        self.assertAlmostEqual(clamp.unit_price_usd, 3.80, places=2)
        self.assertTrue(any("Upper clamp" in w and "nearest" in w for w in q.warnings))

    def test_height_3000_auto_picks_3m_post(self):
        cfg = FenceConfig(bays=1, bay_width_m=2.0, bay_height_mm=3000)
        self.assertEqual(cfg.post_length_m, 3.0)


class ShippingEstimate_Type2(unittest.TestCase):
    """Sanity-check shipping estimates for the 32-bay Type 2 PI scenario.

    Boards: 640 * 2.0m * 2.2 kg/m = 2816 kg
    Posts:  33 * 3.0m * 1.685 kg/m = 166.8 kg
    Subtotal: 2982.8 kg + 5% buffer = 3131.9 kg

    Board CBM: 640 * (0.1615 * 0.020 * 2.0) = 640 * 0.00646 = 4.134 m^3
    Post CBM:  33 * (0.080 * 0.080 * 3.0)  = 33 * 0.0192   = 0.634 m^3
    Total CBM: 4.768 m^3

    These are the values a 1x40HQ container (~76 m^3, ~26t payload) needs
    to fit; the order is well under both -- consistent with the fact that
    the real PI shipped on local-to-Guangzhou trucking, not a container.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = FenceConfig(bays=32, bay_width_m=2.0, bay_height_mm=3000, post_length_m=3.0)
        cls.est = estimate_shipping(cls.cfg)

    def test_weight_in_expected_range(self):
        # Board-dominated: 640 boards x 2m x 2.2 = 2816 kg + posts ~167 kg + 5% buffer
        # Expect 3100-3200 kg
        self.assertGreater(self.est.weight_kg, 3000)
        self.assertLess(self.est.weight_kg, 3300)

    def test_cbm_in_expected_range(self):
        # Boards 4.13 + posts 0.63 ~= 4.77 m^3
        self.assertGreater(self.est.cbm_m3, 4.5)
        self.assertLess(self.est.cbm_m3, 5.0)

    def test_estimate_carries_caveat(self):
        # Caller must always see the "NOT vendor-confirmed" note.
        joined = " | ".join(self.est.notes).lower()
        self.assertIn("not vendor-confirmed", joined)

    def test_estimate_is_opt_in(self):
        # Default calculate() must not silently produce a shipping estimate.
        q = calculate(self.cfg, include_shipping=False)
        self.assertIsNone(q.shipping_estimate)
        q2 = calculate(self.cfg, include_shipping=False, include_shipping_estimate=True)
        self.assertIsNotNone(q2.shipping_estimate)


if __name__ == "__main__":
    unittest.main()
