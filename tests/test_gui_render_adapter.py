"""Core integration, deterministic revisions and graphics-free adapter tests."""

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src.core.board import Board
from src.core.state import BloxorzState, Orientation
from src.gui.contracts import BasicOrientation, BasicTileKind, StaticBoardData
from src.gui.render_adapter import build_board_data, build_game_snapshot


ROOT = Path(__file__).resolve().parents[1]
LEVEL = ROOT / "levels" / "level_01.json"


class RenderAdapterTests(unittest.TestCase):
    def setUp(self):
        self.board = Board(str(LEVEL))
        self.data = build_board_data(self.board, level_id="level_01")

    def make_board(self, grid, goal):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps({"grid": grid, "start": [0, 0], "goal": goal}),
                            encoding="utf-8")
            return Board(str(path))

    def snapshot(self, state, **context):
        return build_game_snapshot(state, board_data=self.data,
                                   session_id=context.get("session_id", "preview-1"),
                                   state_revision=context.get("state_revision", 0))

    def test_t09_real_level_load(self):
        self.assertEqual((self.data.rows, self.data.cols), (4, 7))
        self.assertEqual(self.data.level_id, "level_01")
        self.assertEqual(len(self.data.tiles), 4)
        self.assertTrue(all(len(row) == 7 for row in self.data.tiles))
        self.assertEqual(self.data.schema_version, 1)

    def test_t10_zero_tiles_are_void(self):
        self.assertIs(self.data.tiles[0][3], BasicTileKind.VOID)
        self.assertIs(self.data.tiles[3][6], BasicTileKind.VOID)

    def test_t11_one_and_two_are_floor_even_outside_goal(self):
        board = self.make_board([[1, 2, 1]], [0, 2])
        data = build_board_data(board, level_id="fixture")
        self.assertEqual(data.tiles, ((BasicTileKind.FLOOR,) * 3,))
        self.assertEqual(data.goal_cells, ((0, 2),))

    def test_t12_goal_comes_from_authoritative_board_fields(self):
        board = self.make_board([[1, 2, 1]], [0, 0])
        data = build_board_data(board, level_id="fixture")
        self.assertEqual(data.goal_cells, ((0, 0),))
        self.assertNotIn((0, 1), data.goal_cells)
        self.assertEqual(self.data.goal_cells, ((1, 6),))

    def test_t13_standing_pose(self):
        result = self.snapshot(self.board.get_initial_state())
        self.assertIs(result.orientation, BasicOrientation.STANDING)
        self.assertEqual(result.anchor_cell, (1, 1))
        self.assertEqual(result.occupied_cells, ((1, 1),))

    def test_t14_horizontal_pose(self):
        result = self.snapshot(BloxorzState(1, 4, Orientation.HORIZONTAL))
        self.assertIs(result.orientation, BasicOrientation.HORIZONTAL)
        self.assertEqual(result.anchor_cell, (1, 4))
        self.assertEqual(result.occupied_cells, ((1, 4), (1, 5)))

    def test_t15_vertical_pose(self):
        result = self.snapshot(BloxorzState(1, 4, Orientation.VERTICAL))
        self.assertIs(result.orientation, BasicOrientation.VERTICAL)
        self.assertEqual(result.anchor_cell, (1, 4))
        self.assertEqual(result.occupied_cells, ((1, 4), (2, 4)))

    def test_t16_board_is_not_mutated_on_success_or_failure(self):
        before = copy.deepcopy(vars(self.board))
        grid_identity = id(self.board.grid)
        row_identities = [id(row) for row in self.board.grid]
        build_board_data(self.board, level_id="another-id")
        with self.assertRaises(ValueError):
            build_board_data(self.board, level_id=" ")
        self.assertEqual(vars(self.board), before)
        self.assertEqual(id(self.board.grid), grid_identity)
        self.assertEqual([id(row) for row in self.board.grid], row_identities)
        self.board.grid[0][1] = 3
        before = copy.deepcopy(vars(self.board))
        with self.assertRaises(ValueError):
            build_board_data(self.board, level_id="unsupported")
        self.assertEqual(vars(self.board), before)

    def test_t17_state_is_not_mutated_or_removed_from_search_keys(self):
        for flags in ((), (True,), (False,)):
            with self.subTest(flags=flags):
                state = BloxorzState(1, 1, Orientation.HORIZONTAL, flags)
                before = copy.deepcopy(vars(state))
                state_hash = hash(state)
                visited = {state}
                if flags:
                    with self.assertRaisesRegex(ValueError, "bridges_state"):
                        self.snapshot(state)
                else:
                    self.snapshot(state)
                self.assertEqual(vars(state), before)
                self.assertEqual(hash(state), state_hash)
                self.assertIn(state, visited)

    def test_t18_dto_detaches_grid_goal_and_occupied_containers(self):
        revision = self.data.board_revision
        self.board.grid[0][0] = 0
        self.board.grid[1].clear()
        self.board.goal_r = 0
        self.assertIs(self.data.tiles[0][0], BasicTileKind.FLOOR)
        self.assertEqual(len(self.data.tiles[1]), 7)
        self.assertEqual(self.data.goal_cells, ((1, 6),))
        self.assertEqual(self.data.board_revision, revision)
        cells = [[1, 4], [1, 5]]
        with patch.object(BloxorzState, "get_occupied_cells", return_value=cells):
            result = self.snapshot(BloxorzState(1, 4, Orientation.HORIZONTAL))
        cells[0][0] = 99
        cells.clear()
        self.assertEqual(result.occupied_cells, ((1, 4), (1, 5)))

    def test_t19_revision_is_stable_across_objects_processes_and_hash_seeds(self):
        duplicate = build_board_data(Board(str(LEVEL)), level_id="level_01")
        self.assertEqual(duplicate, self.data)
        code = (
            "from src.core.board import Board; "
            "from src.gui.render_adapter import build_board_data; "
            "print(build_board_data(Board('levels/level_01.json'), "
            "level_id='level_01').board_revision)"
        )
        for seed in ("1", "991"):
            with self.subTest(seed=seed):
                env = dict(os.environ, PYTHONHASHSEED=seed)
                result = subprocess.run([sys.executable, "-S", "-B", "-c", code],
                                        cwd=ROOT, env=env, capture_output=True,
                                        text=True, timeout=10, check=True)
                self.assertEqual(result.stdout.strip(), self.data.board_revision)

    def test_t20_raw_code_change_changes_revision_even_with_same_visuals(self):
        self.board.grid[0][0] = 2
        changed = build_board_data(self.board, level_id="level_01")
        self.assertEqual(changed.tiles, self.data.tiles)
        self.assertEqual(changed.goal_cells, self.data.goal_cells)
        self.assertNotEqual(changed.board_revision, self.data.board_revision)

    def test_t21_goal_change_changes_revision(self):
        self.board.goal_r, self.board.goal_c = 2, 6
        changed = build_board_data(self.board, level_id="level_01")
        self.assertEqual(changed.tiles, self.data.tiles)
        self.assertNotEqual(changed.board_revision, self.data.board_revision)

    def test_t22_unsupported_tiles_states_and_bridge_flags_are_rejected(self):
        for tile in (3, 99, -1, True, "1", 1.0):
            with self.subTest(tile=tile):
                self.board.grid[0][1] = tile
                with self.assertRaisesRegex((TypeError, ValueError), r"board.grid\[0\]\[1\]"):
                    build_board_data(self.board, level_id="unsupported")
        for flags in ((False,), (True,), (False, True)):
            with self.subTest(flags=flags):
                with self.assertRaisesRegex(ValueError, "unsupported Basic bridge"):
                    self.snapshot(BloxorzState(1, 1, Orientation.STANDING, flags))
        class ExtendedState(BloxorzState):
            pass
        class ExtendedBoard(Board):
            pass
        with self.assertRaisesRegex(TypeError, "schema"):
            self.snapshot(ExtendedState(1, 1, Orientation.STANDING))
        with self.assertRaisesRegex(TypeError, "schema"):
            build_board_data(ExtendedBoard(str(LEVEL)), level_id="new-schema")
        state = BloxorzState(1, 1, Orientation.STANDING)
        object.__setattr__(state, "orientation", "STANDING")
        with self.assertRaisesRegex(ValueError, "orientation"):
            self.snapshot(state)

    def test_t23_import_and_conversion_work_without_site_packages(self):
        code = """
import sys
from src.gui.contracts import BasicTileKind
assert 'src.core.board' not in sys.modules
assert 'src.core.state' not in sys.modules
from src.gui.render_adapter import build_board_data, build_game_snapshot
from src.core.board import Board
board = Board('levels/level_01.json')
data = build_board_data(board, level_id='demo')
snapshot = build_game_snapshot(board.get_initial_state(), board_data=data,
                               session_id='pure-python', state_revision=0)
assert snapshot.occupied_cells == ((1, 1),)
assert data.tiles[0][3] is BasicTileKind.VOID
assert not any(name.split('.')[0] in ('panda3d', 'direct', 'pygame')
               for name in sys.modules)
print('pure-python OK')
"""
        result = subprocess.run([sys.executable, "-S", "-B", "-c", code], cwd=ROOT,
                                capture_output=True, text=True, timeout=10, check=True)
        self.assertEqual(result.stdout.strip(), "pure-python OK")

    def test_t24_import_never_reaches_graphics_host_controller_or_solvers(self):
        code = """
import importlib.abc
import sys
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        forbidden = ('panda3d', 'direct', 'pygame', 'src.gui.app',
                     'src.gui.controller', 'src.gui.renderer', 'src.solvers')
        if any(fullname == name or fullname.startswith(name + '.') for name in forbidden):
            raise AssertionError('Unexpected import: ' + fullname)
sys.meta_path.insert(0, Guard())
import src.gui.contracts
import src.gui.render_adapter
print('no-graphics OK')
"""
        result = subprocess.run([sys.executable, "-S", "-B", "-c", code], cwd=ROOT,
                                capture_output=True, text=True, timeout=10, check=True)
        self.assertEqual(result.stdout.strip(), "no-graphics OK")

    def test_t25_non_square_board_retains_logical_row_column_coordinates(self):
        result = self.snapshot(BloxorzState(2, 5, Orientation.HORIZONTAL),
                               session_id="tai-session", state_revision=19)
        self.assertEqual(result.anchor_cell, (2, 5))
        self.assertEqual(result.occupied_cells, ((2, 5), (2, 6)))
        self.assertEqual(result.session_id, "tai-session")
        self.assertEqual(result.state_revision, 19)
        self.assertEqual(result.board_revision, self.data.board_revision)

    def test_t26_no_transition_or_rule_validation_is_called(self):
        with patch.object(Board, "transition", side_effect=AssertionError("transition")), \
             patch.object(Board, "is_valid_state", side_effect=AssertionError("valid_state")), \
             patch.object(Board, "is_valid_cell", side_effect=AssertionError("valid_cell")), \
             patch.object(Board, "is_goal", side_effect=AssertionError("goal")), \
             patch.object(BloxorzState, "is_standing", side_effect=AssertionError("standing")):
            data = build_board_data(self.board, level_id="no-rules")
            # This is on VOID: structurally valid, gameplay support is Core's job.
            result = build_game_snapshot(BloxorzState(0, 3, Orientation.STANDING),
                                         board_data=data, session_id="no-rules",
                                         state_revision=0)
        self.assertEqual(result.occupied_cells, ((0, 3),))

    def test_invalid_board_structure_and_goals_report_their_field(self):
        for field, value in (("rows", 0), ("cols", True), ("grid", []),
                             ("grid", [[1]] * 4), ("goal_r", 4),
                             ("goal_c", 7), ("goal_r", -1), ("goal_c", True)):
            with self.subTest(field=field, value=value):
                board = Board(str(LEVEL))
                setattr(board, field, value)
                with self.assertRaisesRegex((TypeError, ValueError), "board[.]"):
                    build_board_data(board, level_id="bad")

    def test_snapshot_rejects_out_of_bounds_anchor_and_secondary_cell(self):
        for state in (BloxorzState(-1, 0, Orientation.STANDING),
                      BloxorzState(4, 0, Orientation.STANDING),
                      BloxorzState(0, 7, Orientation.STANDING),
                      BloxorzState(2, 6, Orientation.HORIZONTAL),
                      BloxorzState(3, 2, Orientation.VERTICAL)):
            with self.subTest(state=state):
                with self.assertRaisesRegex(ValueError, "anchor_cell|occupied_cells"):
                    self.snapshot(state)

    def test_occupied_cells_are_canonicalized_without_hiding_duplicates(self):
        state = BloxorzState(1, 4, Orientation.HORIZONTAL)
        for cells in ([(1, 5), (1, 4)], {(1, 5), (1, 4)}):
            with self.subTest(cells=cells):
                with patch.object(BloxorzState, "get_occupied_cells", return_value=cells):
                    result = self.snapshot(state)
                self.assertEqual(result.occupied_cells, ((1, 4), (1, 5)))
        for cells in ([(1, 4), (1, 4)], [(1, 4)], [(1, 4), (2, 4)],
                      [], [(1, 4), (1, 5), (1, 6)], None,
                      [(1, 4), (True, 5)], [(1, 4), "1,5"]):
            with self.subTest(cells=cells):
                with patch.object(BloxorzState, "get_occupied_cells", return_value=cells):
                    with self.assertRaisesRegex((TypeError, ValueError), "occupied_cells"):
                        self.snapshot(state)

    def test_revision_includes_level_id_dimensions_and_matches_canonical_json(self):
        board = self.make_board([[1, 2]], [0, 1])
        data = build_board_data(board, level_id="fixture")
        canonical = (b'{"cols":2,"goal_cells":[[0,1]],"grid":[[1,2]],'
                     b'"level_id":"fixture","rows":1}')
        self.assertEqual(data.board_revision, hashlib.sha256(canonical).hexdigest())
        other_id = build_board_data(board, level_id="different-id")
        self.assertNotEqual(data.board_revision, other_id.board_revision)
        other_shape = build_board_data(self.make_board([[1], [2]], [0, 0]),
                                      level_id="fixture")
        self.assertNotEqual(data.board_revision, other_shape.board_revision)

    def test_snapshot_never_copies_or_hashes_the_static_board(self):
        accessed = []
        original = StaticBoardData.__getattribute__
        def track_access(data, name):
            accessed.append(name)
            return original(data, name)
        with patch.object(StaticBoardData, "__getattribute__", track_access), \
             patch("src.gui.render_adapter.hashlib.sha256", side_effect=AssertionError("rehash")), \
             patch("src.gui.render_adapter.json.dumps", side_effect=AssertionError("serialize")), \
             patch("src.gui.render_adapter.build_board_data", side_effect=AssertionError("rebuild")):
            result = self.snapshot(self.board.get_initial_state())
        self.assertEqual(result.board_revision, self.data.board_revision)
        self.assertNotIn("tiles", accessed)
        self.assertNotIn("goal_cells", accessed)
        self.assertTrue(set(accessed) <= {"__class__", "board_revision", "rows", "cols"})

    def test_caller_context_is_validated_without_defaults(self):
        state = self.board.get_initial_state()
        for context in ({"session_id": ""}, {"session_id": 1},
                        {"state_revision": -1}, {"state_revision": True}):
            with self.subTest(context=context):
                with self.assertRaises((TypeError, ValueError)):
                    self.snapshot(state, **context)
        with self.assertRaisesRegex(TypeError, "board_data"):
            build_game_snapshot(state, board_data=self.board, session_id="s", state_revision=0)
        with self.assertRaises(TypeError):
            build_game_snapshot(state, board_data=self.data, state_revision=0)


if __name__ == "__main__":
    unittest.main()
