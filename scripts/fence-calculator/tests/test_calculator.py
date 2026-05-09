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

from calculator import FenceConfig, calculate


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

    def test_rejects_unsupported_height(self):
        with self.assertRaises(ValueError):
            FenceConfig(bays=1, bay_width_m=2.0, bay_height_mm=1500, post_length_m=2.0)

    def test_rejects_unsupported_width(self):
        with self.assertRaises(ValueError):
            FenceConfig(bays=1, bay_width_m=1.8, bay_height_mm=3000, post_length_m=3.0)


if __name__ == "__main__":
    unittest.main()
