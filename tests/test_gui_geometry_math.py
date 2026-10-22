"""Gate A: engine-independent coordinates and canonical block poses."""

import subprocess
import sys
import unittest
from pathlib import Path

from src.gui.contracts import BasicOrientation as O
from src.gui.geometry_math import block_pose, cell_to_world, logical_board_bounds


class GeometryMathTests(unittest.TestCase):
    def pose(self, orientation, **kwargs):
        return block_pose(1, 1, orientation, rows=4, cols=7, **kwargs)

    def test_t01_cell_to_world(self):
        self.assertEqual(cell_to_world(0, 0, rows=4, cols=7), (-3.0, 1.5))
        self.assertEqual(cell_to_world(3, 6, rows=4, cols=7), (3.0, -1.5))

    def test_t02_even_and_odd_boards_are_centered(self):
        for rows, cols in ((4, 7), (3, 5), (2, 2), (1, 1)):
            with self.subTest(rows=rows, cols=cols):
                first = cell_to_world(0, 0, rows=rows, cols=cols)
                last = cell_to_world(rows - 1, cols - 1, rows=rows, cols=cols)
                self.assertEqual(tuple(a + b for a, b in zip(first, last)), (0, 0))
                self.assertEqual(logical_board_bounds(rows, cols),
                                 ((-cols / 2, -rows / 2), (cols / 2, rows / 2)))

    def test_t03_non_square_board_axes_are_not_swapped(self):
        self.assertEqual(cell_to_world(0, 4, rows=2, cols=5), (2, 0.5))
        self.assertEqual(cell_to_world(4, 0, rows=5, cols=2), (-0.5, -2))

    def test_t04_standing_center(self):
        self.assertEqual(self.pose(O.STANDING).center, (-2.0, 0.5, 1.0))

    def test_t05_horizontal_center(self):
        self.assertEqual(self.pose(O.HORIZONTAL).center, (-1.5, 0.5, 0.5))

    def test_t06_vertical_center(self):
        self.assertEqual(self.pose(O.VERTICAL).center, (-2.0, 0.0, 0.5))

    def test_t07_standing_dimensions(self):
        self.assertEqual(self.pose(O.STANDING).dimensions, (1, 1, 2))

    def test_t08_horizontal_dimensions(self):
        self.assertEqual(self.pose(O.HORIZONTAL).dimensions, (2, 1, 1))

    def test_t09_vertical_dimensions(self):
        self.assertEqual(self.pose(O.VERTICAL).dimensions, (1, 2, 1))

    def test_t10_all_orientations_have_bottom_zero(self):
        for orientation in O:
            pose = self.pose(orientation)
            self.assertEqual(pose.center[2] - pose.dimensions[2] / 2, 0)

    def test_t11_world_extents_match_occupied_footprint(self):
        for rows, cols in ((3, 5), (4, 4), (7, 3)):
            for orientation, cells in (
                (O.STANDING, ((1, 1),)),
                (O.HORIZONTAL, ((1, 1), (1, 2))),
                (O.VERTICAL, ((1, 1), (2, 1))),
            ):
                with self.subTest(rows=rows, cols=cols, orientation=orientation):
                    pose = block_pose(1, 1, orientation, rows=rows, cols=cols)
                    positions = [cell_to_world(*cell, rows=rows, cols=cols) for cell in cells]
                    for axis in (0, 1):
                        self.assertEqual(pose.center[axis] - pose.dimensions[axis] / 2,
                                         min(p[axis] for p in positions) - 0.5)
                        self.assertEqual(pose.center[axis] + pose.dimensions[axis] / 2,
                                         max(p[axis] for p in positions) + 0.5)

    def test_t12_goal_reference_position(self):
        self.assertEqual(cell_to_world(1, 6, rows=4, cols=7), (3, 0.5))

    def test_t13_pitch_scales_centers_dimensions_and_bounds(self):
        for pitch in (0.5, 2.0):
            for orientation in O:
                scaled, unit = self.pose(orientation, pitch=pitch), self.pose(orientation)
                self.assertEqual(scaled.center, tuple(v * pitch for v in unit.center))
                self.assertEqual(scaled.dimensions, tuple(v * pitch for v in unit.dimensions))
            self.assertEqual(logical_board_bounds(2, 4, pitch=pitch),
                             ((-2 * pitch, -pitch), (2 * pitch, pitch)))

    def test_t14_invalid_inputs_fail_clearly(self):
        for pitch in (0, -1, True, float('nan'), float('inf'), "1"):
            with self.subTest(pitch=pitch):
                with self.assertRaisesRegex(ValueError, "pitch"):
                    self.pose(O.STANDING, pitch=pitch)
        for rows, cols in ((0, 7), (4, -1), (True, 7), (4, 7.0)):
            with self.assertRaisesRegex(ValueError, "rows|cols"):
                logical_board_bounds(rows, cols)
        for row, col in ((-1, 0), (0, 7), (4, 0), (True, 0), (0.5, 0)):
            with self.assertRaisesRegex(ValueError, "row|col"):
                cell_to_world(row, col, rows=4, cols=7)
        with self.assertRaisesRegex(ValueError, "orientation"):
            block_pose(0, 0, "STANDING", rows=2, cols=2)
        for orientation in (O.HORIZONTAL, O.VERTICAL):
            with self.assertRaisesRegex(ValueError, "footprint"):
                block_pose(0, 0, orientation, rows=1, cols=1)

    def test_t15_pure_math_import_has_no_engine_or_core_dependency(self):
        code = """
import sys
from src.gui.geometry_math import cell_to_world
assert cell_to_world(1, 6, rows=4, cols=7) == (3, 0.5)
assert not any(n.split('.')[0] in ('panda3d', 'direct', 'pygame')
               or n == 'src.core' or n.startswith('src.core.') for n in sys.modules)
"""
        result = subprocess.run([sys.executable, '-S', '-B', '-c', code],
                                cwd=Path(__file__).resolve().parents[1],
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
