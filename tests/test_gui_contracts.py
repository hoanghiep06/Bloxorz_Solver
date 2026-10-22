"""Structural/immutability tests for the engine-independent render DTOs."""

import unittest
from dataclasses import FrozenInstanceError, replace

from src.gui.contracts import (
    BasicOrientation,
    BasicTileKind,
    GameSnapshot,
    StaticBoardData,
)


class RenderContractTests(unittest.TestCase):
    def setUp(self):
        self.board = StaticBoardData(
            1, "fixture", "revision", 2, 3,
            ((BasicTileKind.FLOOR, BasicTileKind.VOID, BasicTileKind.FLOOR),
             (BasicTileKind.FLOOR,) * 3), ((1, 2),),
        )
        self.snapshot = GameSnapshot(
            1, "session-phuoc", 7, "revision", "WHOLE",
            BasicOrientation.HORIZONTAL, (1, 0), ((1, 0), (1, 1)),
        )

    def test_t01_valid_static_board(self):
        self.assertEqual((self.board.rows, self.board.cols), (2, 3))
        self.assertEqual(self.board.goal_cells, ((1, 2),))
        self.assertIs(self.board.tiles[0][1], BasicTileKind.VOID)

    def test_t02_dimensions_reject_invalid_values_and_booleans(self):
        for field in ("rows", "cols"):
            for value in (0, -1, True, 2.0, "2", None):
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex((ValueError, TypeError), field):
                        replace(self.board, **{field: value})

    def test_t03_grid_rejects_missing_or_extra_rows_and_columns(self):
        for tiles in (self.board.tiles[:1], self.board.tiles * 2,
                      (self.board.tiles[0][:-1], self.board.tiles[1]),
                      (self.board.tiles[0] + (BasicTileKind.FLOOR,), self.board.tiles[1])):
            with self.subTest(tiles=tiles):
                with self.assertRaisesRegex(ValueError, "tiles"):
                    replace(self.board, tiles=tiles)

    def test_t04_goals_must_have_integer_coordinates_within_bounds(self):
        for cell in ((2, 0), (0, 3), (-1, 0), (0, -1), (True, 0), (0.0, 0), (0,)):
            with self.subTest(cell=cell):
                with self.assertRaisesRegex((TypeError, ValueError), "goal_cells"):
                    replace(self.board, goal_cells=(cell,))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            replace(self.board, goal_cells=((1, 2), (1, 2)))

    def test_t05_tiles_and_goals_are_deeply_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            self.board.rows = 10
        with self.assertRaises(TypeError):
            self.board.tiles[0][0] = BasicTileKind.VOID
        with self.assertRaises(TypeError):
            self.board.goal_cells[0][0] = 0
        self.assertIsInstance(hash(self.board), int)

    def test_t06_snapshot_keeps_caller_identity_and_revision(self):
        self.assertEqual(self.snapshot.session_id, "session-phuoc")
        self.assertEqual(self.snapshot.state_revision, 7)
        self.assertEqual(self.snapshot.board_revision, "revision")
        self.assertEqual(self.snapshot.block_mode, "WHOLE")
        self.assertEqual(replace(self.snapshot, state_revision=0).state_revision, 0)

    def test_t07_unknown_orientation_is_never_defaulted(self):
        for orientation in ("STANDING", 0, None, BasicTileKind.FLOOR):
            with self.subTest(orientation=orientation):
                with self.assertRaisesRegex(TypeError, "orientation"):
                    replace(self.snapshot, orientation=orientation)

    def test_t08_session_and_revision_reject_invalid_values(self):
        for value in ("", "  ", None, 1, True):
            with self.subTest(session=value):
                with self.assertRaisesRegex((ValueError, TypeError), "session_id"):
                    replace(self.snapshot, session_id=value)
        for value in (-1, True, 1.0, "1", None):
            with self.subTest(revision=value):
                with self.assertRaisesRegex((ValueError, TypeError), "state_revision"):
                    replace(self.snapshot, state_revision=value)

    def test_direct_constructors_reject_mutable_containers(self):
        for field, value in (
            ("tiles", list(self.board.tiles)),
            ("tiles", (list(self.board.tiles[0]), self.board.tiles[1])),
            ("goal_cells", [[1, 2]]), ("goal_cells", ([1, 2],)),
        ):
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(TypeError, field):
                    replace(self.board, **{field: value})
        for field, value in (
            ("anchor_cell", [1, 0]),
            ("occupied_cells", [[1, 0], [1, 1]]),
            ("occupied_cells", ([1, 0], (1, 1))),
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(TypeError, field):
                    replace(self.snapshot, **{field: value})

    def test_schema_identity_and_tile_members_are_validated(self):
        for dto in (self.board, self.snapshot):
            for version in (0, 2, True, "1"):
                with self.subTest(dto=type(dto).__name__, version=version):
                    with self.assertRaisesRegex((TypeError, ValueError), "schema_version"):
                        replace(dto, schema_version=version)
            for revision in ("", " ", None, 123):
                with self.subTest(revision=revision):
                    with self.assertRaisesRegex((TypeError, ValueError), "board_revision"):
                        replace(dto, board_revision=revision)
        for level_id in ("", " ", None, 1):
            with self.subTest(level_id=level_id):
                with self.assertRaisesRegex((TypeError, ValueError), "level_id"):
                    replace(self.board, level_id=level_id)
        for tile in ("FLOOR", 1, True, None):
            with self.subTest(tile=tile):
                with self.assertRaisesRegex(TypeError, r"tiles\[0\]\[0\]"):
                    replace(self.board, tiles=((tile,) * 3, self.board.tiles[1]))

    def test_snapshot_rejects_bad_footprints_and_coordinate_types(self):
        for cells in ((), ((1, 0),), ((1, 0), (1, 0)), ((1, 1), (1, 0)),
                      ((1, 0), (2, 0)), ((1, 0), (1, 1), (1, 2))):
            with self.subTest(cells=cells):
                with self.assertRaisesRegex(ValueError, "occupied_cells"):
                    replace(self.snapshot, occupied_cells=cells)
        for anchor in ((-1, 0), (0, -1), (True, 0), (1.0, 0), (0,)):
            with self.subTest(anchor=anchor):
                with self.assertRaisesRegex((ValueError, TypeError), "anchor_cell"):
                    replace(self.snapshot, anchor_cell=anchor)
        with self.assertRaisesRegex(TypeError, "occupied_cells"):
            replace(self.snapshot, occupied_cells=((1, 0), (True, 1)))

    def test_snapshot_is_deeply_immutable_and_split_is_unsupported(self):
        with self.assertRaises(FrozenInstanceError):
            self.snapshot.state_revision = 8
        with self.assertRaises(TypeError):
            self.snapshot.occupied_cells[0][0] = 0
        with self.assertRaises(TypeError):
            self.snapshot.anchor_cell[0] = 0
        for mode in ("SPLIT", "whole", None):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(ValueError, "block_mode"):
                    replace(self.snapshot, block_mode=mode)

    def test_validation_does_not_impose_tile_support_or_goal_rules(self):
        # No rule that a logical goal must be FLOOR is added by a DTO.
        board = replace(self.board, goal_cells=((0, 1),))
        self.assertIs(board.tiles[0][1], BasicTileKind.VOID)
        # Board dimensions are absent here; bounds belong to the adapter.
        snapshot = replace(self.snapshot, orientation=BasicOrientation.STANDING,
                           anchor_cell=(99, 99), occupied_cells=((99, 99),))
        self.assertEqual(snapshot.anchor_cell, (99, 99))


if __name__ == "__main__":
    unittest.main()
