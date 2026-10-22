"""Engine-independent layout and supported-window contract checks."""
import ast
from dataclasses import FrozenInstanceError
from itertools import combinations
from pathlib import Path
import unittest

from src.gui.layout import Rect, calculate_layout, normalized_region, panel_controls


class LayoutTests(unittest.TestCase):
    def test_exact_reference(self):
        layout = calculate_layout(1280, 720)
        self.assertEqual(layout.header, Rect(24, 24, 1232, 56))
        self.assertEqual(layout.viewport, Rect(24, 92, 934, 530))
        self.assertEqual(layout.panel, Rect(974, 92, 282, 530))
        self.assertEqual(layout.status, Rect(24, 634, 1232, 62))

    def test_supported_windows_containment_and_separation(self):
        for width, height in ((1280, 720), (1366, 768), (1920, 1080),
                              (1024, 768), (1024, 720)):
            with self.subTest(size=(width, height)):
                layout = calculate_layout(width, height)
                self.assertTrue(layout.supported)
                regions = (layout.header, layout.viewport, layout.panel, layout.status)
                for region in regions:
                    self.assertLessEqual(region.right, width)
                    self.assertLessEqual(region.bottom, height)
                for a, b in combinations(regions, 2):
                    self.assertFalse(a.intersects(b))
                self.assertEqual(layout.viewport.width, width - 346)
                self.assertEqual(layout.viewport.height, height - 190)

    def test_display_region_reference_and_y_flip(self):
        values = normalized_region(calculate_layout(1280, 720).viewport, 1280, 720)
        for actual, expected in zip(values, (.01875, .7484375, .1361111111, .8722222222)):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(normalized_region(Rect(0, 0, 50, 20), 100, 100), (0, .5, .8, 1))

    def test_bad_dimensions_and_outside_rectangles(self):
        for value in (0, -1, True, 1.5, '1280', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                calculate_layout(value, 720)
        with self.assertRaises(ValueError):
            normalized_region(Rect(90, 0, 20, 10), 100, 100)
        with self.assertRaises(ValueError):
            Rect(0, 0, 0, 1)

    def test_small_window_fallback(self):
        layout = calculate_layout(320, 200)
        self.assertFalse(layout.supported)
        self.assertIsNone(layout.header)
        self.assertEqual(layout.viewport, Rect(0, 0, 320, 200))

    def test_deterministic_immutable(self):
        layout = calculate_layout(1280, 720)
        self.assertEqual(layout, calculate_layout(1280, 720))
        with self.assertRaises(FrozenInstanceError):
            layout.width = 100

    def test_panel_controls_fit_and_do_not_overlap(self):
        controls = panel_controls()
        self.assertEqual(len(controls), 13)
        for rect in controls.values():
            self.assertGreaterEqual(rect.x, 16)
            self.assertLessEqual(rect.right, 266)
            self.assertLessEqual(rect.bottom, 530)
        for a, b in combinations(controls.values(), 2):
            self.assertFalse(a.intersects(b))

    def test_layout_has_only_standard_library_imports(self):
        tree = ast.parse(Path(__file__).resolve().parents[1].joinpath('src/gui/layout.py').read_text())
        self.assertEqual([node.module for node in ast.walk(tree)
                          if isinstance(node, ast.ImportFrom)], ['dataclasses'])
