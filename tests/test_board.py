import json
import tempfile
import unittest
from pathlib import Path

from src.core.board import ACTIONS, Board
from src.core.state import BloxorzState, Orientation
from src.solvers.bfs import BFSSolver


class BoardFixture(unittest.TestCase):
    """Create temporary levels without changing the production levels directory."""

    def load_level(self, data):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'level.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        return Board(str(path))

    def make_board(self, grid=None, start=None, goal=None):
        if grid is None:
            grid = [[1] * 9 for _ in range(9)]
        if start is None:
            start = [0, 0]
        if goal is None:
            goal = [len(grid) - 1, len(grid[0]) - 1]
        return self.load_level({'grid': grid, 'start': start, 'goal': goal})


class BoardTests(BoardFixture):
    def test_action_order(self):
        self.assertEqual(ACTIONS, ['U', 'D', 'L', 'R'])

    def test_all_twelve_orientation_transitions(self):
        board = self.make_board()
        s, h, v = Orientation.STANDING, Orientation.HORIZONTAL, Orientation.VERTICAL
        # Independent expected coordinates AND occupied cells, from anchor (4, 4).
        cases = [
            (s, 'U', (2, 4), v, [(2, 4), (3, 4)]),
            (s, 'D', (5, 4), v, [(5, 4), (6, 4)]),
            (s, 'L', (4, 2), h, [(4, 2), (4, 3)]),
            (s, 'R', (4, 5), h, [(4, 5), (4, 6)]),
            (h, 'U', (3, 4), h, [(3, 4), (3, 5)]),
            (h, 'D', (5, 4), h, [(5, 4), (5, 5)]),
            (h, 'L', (4, 3), s, [(4, 3)]),
            (h, 'R', (4, 6), s, [(4, 6)]),
            (v, 'U', (3, 4), s, [(3, 4)]),
            (v, 'D', (6, 4), s, [(6, 4)]),
            (v, 'L', (4, 3), v, [(4, 3), (5, 3)]),
            (v, 'R', (4, 5), v, [(4, 5), (5, 5)]),
        ]
        for orientation, action, position, expected_o, cells in cases:
            with self.subTest(orientation=orientation.name, action=action):
                source = BloxorzState(4, 4, orientation, (True, False))
                visited = {source}
                result = board.transition(source, action)
                self.assertIsNotNone(result)
                self.assertIsNot(result, source)
                self.assertEqual((result.r, result.c), position)
                self.assertEqual(result.orientation, expected_o)
                self.assertEqual(result.get_occupied_cells(), cells)
                self.assertEqual(result.bridges_state, (True, False))
                self.assertEqual(source, BloxorzState(4, 4, orientation, (True, False)))
                self.assertIn(source, visited)

    def test_moves_crossing_each_boundary_are_rejected(self):
        board = self.make_board()
        for r, c, action in ((0, 4, 'U'), (8, 4, 'D'), (4, 0, 'L'), (4, 8, 'R')):
            with self.subTest(action=action):
                source = BloxorzState(r, c, Orientation.STANDING)
                self.assertIsNone(board.transition(source, action))
                self.assertEqual((source.r, source.c, source.orientation),
                                 (r, c, Orientation.STANDING))

    def test_move_with_only_one_cell_outside_board_is_rejected(self):
        board = self.make_board()
        for source, action in (
            (BloxorzState(1, 4, Orientation.STANDING), 'U'),
            (BloxorzState(7, 4, Orientation.STANDING), 'D'),
            (BloxorzState(4, 1, Orientation.STANDING), 'L'),
            (BloxorzState(4, 7, Orientation.STANDING), 'R'),
        ):
            with self.subTest(action=action):
                self.assertIsNone(board.transition(source, action))

    def test_each_or_both_destination_cells_on_void_are_rejected(self):
        for voids in ([(4, 5)], [(4, 6)], [(4, 5), (4, 6)]):
            with self.subTest(voids=voids):
                grid = [[1] * 9 for _ in range(9)]
                for r, c in voids:
                    grid[r][c] = 0
                board = self.make_board(grid)
                source = BloxorzState(4, 4, Orientation.STANDING, (True,))
                before = repr(source), hash(source), source.get_occupied_cells()
                self.assertIsNone(board.transition(source, 'R'))
                self.assertEqual((repr(source), hash(source), source.get_occupied_cells()), before)

    def test_invalid_actions_raise_value_error_without_mutating_source(self):
        board = self.make_board()
        source = BloxorzState(4, 4, Orientation.STANDING)
        for action in ('X', 'up', 'u', '', None, 1, []):
            with self.subTest(action=action):
                with self.assertRaisesRegex(ValueError, 'Unsupported action'):
                    board.transition(source, action)
                self.assertEqual(source, BloxorzState(4, 4, Orientation.STANDING))

    def test_is_valid_cell_checks_boundaries_and_void(self):
        board = self.make_board([[1, 0, 1], [1, 1, 2]])
        self.assertTrue(board.is_valid_cell(0, 0))
        self.assertTrue(board.is_valid_cell(1, 2))
        for r, c in ((0, 1), (-1, 0), (0, -1), (2, 0), (0, 3)):
            with self.subTest(r=r, c=c):
                self.assertFalse(board.is_valid_cell(r, c))

    def test_invalid_cell_coordinate_types_have_clear_errors(self):
        board = self.make_board()
        for r, c in ((1.5, 0), (0, '1'), (True, 0)):
            with self.subTest(r=r, c=c):
                with self.assertRaisesRegex(TypeError, 'coordinates'):
                    board.is_valid_cell(r, c)

    def test_is_valid_state_checks_every_occupied_cell(self):
        board = self.make_board([[1, 1, 0], [1, 1, 1], [1, 1, 2]])
        cases = [
            (BloxorzState(0, 0, Orientation.STANDING), True),
            (BloxorzState(0, 1, Orientation.HORIZONTAL), False),
            (BloxorzState(0, 2, Orientation.VERTICAL), False),
            (BloxorzState(1, 1, Orientation.VERTICAL), True),
            (BloxorzState(2, 1, Orientation.VERTICAL), False),
            (BloxorzState(1, 2, Orientation.HORIZONTAL), False),
            (BloxorzState(-1, 0, Orientation.STANDING), False),
        ]
        for state, expected in cases:
            with self.subTest(state=state):
                self.assertEqual(board.is_valid_state(state), expected)

    def test_goal_requires_standing_at_goal_coordinate(self):
        board = self.make_board(goal=[4, 4])
        cases = [
            (BloxorzState(4, 4, Orientation.STANDING), True),
            (BloxorzState(4, 4, Orientation.HORIZONTAL), False),
            (BloxorzState(4, 3, Orientation.HORIZONTAL), False),
            (BloxorzState(4, 4, Orientation.VERTICAL), False),
            (BloxorzState(3, 4, Orientation.VERTICAL), False),
            (BloxorzState(4, 3, Orientation.STANDING), False),
        ]
        for state, expected in cases:
            with self.subTest(state=state):
                self.assertEqual(board.is_goal(state), expected)

    def test_goal_field_is_authoritative_and_nonzero_tiles_remain_floor(self):
        board = self.make_board([[1, 2, 3], [1, 1, 1]], goal=[1, 2])
        self.assertTrue(board.is_valid_cell(0, 2))
        self.assertFalse(board.is_goal(BloxorzState(0, 1, Orientation.STANDING)))
        self.assertTrue(board.is_goal(BloxorzState(1, 2, Orientation.STANDING)))
        self.assertEqual(board.transition(BloxorzState(0, 0, Orientation.STANDING), 'R'),
                         BloxorzState(0, 1, Orientation.HORIZONTAL))

    def test_initial_state_is_standing_with_empty_bridge_configuration(self):
        board = self.make_board(start=[2, 3])
        first = board.get_initial_state()
        self.assertEqual(first, BloxorzState(2, 3, Orientation.STANDING))
        self.assertIsNot(first, board.get_initial_state())


class BoardInputTests(BoardFixture):
    def test_non_object_json_is_rejected(self):
        for data in ([], None, 'level', 42):
            with self.subTest(data=data):
                with self.assertRaisesRegex(ValueError, 'JSON object'):
                    self.load_level(data)

    def test_missing_required_fields_are_reported(self):
        for key in ('grid', 'start', 'goal'):
            data = {'grid': [[1]], 'start': [0, 0], 'goal': [0, 0]}
            del data[key]
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, key):
                    self.load_level(data)

    def test_empty_or_malformed_grids_are_rejected(self):
        for grid in ([], [[]], [[], []], 'grid', None, [1], [[1], []], [[1], [1, 1]], [[1], '1']):
            with self.subTest(grid=grid):
                with self.assertRaisesRegex(ValueError, 'grid'):
                    self.load_level({'grid': grid, 'start': [0, 0], 'goal': [0, 0]})

    def test_non_integer_tile_codes_are_rejected(self):
        for tile in ('1', 1.0, True, None, []):
            with self.subTest(tile=tile):
                with self.assertRaisesRegex(ValueError, 'integer tile codes'):
                    self.load_level({'grid': [[tile]], 'start': [0, 0], 'goal': [0, 0]})

    def test_malformed_start_and_goal_coordinates_are_rejected(self):
        for key in ('start', 'goal'):
            for position in ([], [0], [0, 0, 0], '0,0', None, [True, 0], [0.0, 0], ['0', 0]):
                with self.subTest(key=key, position=position):
                    data = {'grid': [[1]], 'start': [0, 0], 'goal': [0, 0]}
                    data[key] = position
                    with self.assertRaisesRegex(ValueError, key):
                        self.load_level(data)

    def test_start_and_goal_outside_grid_are_rejected(self):
        for key in ('start', 'goal'):
            for position in ([-1, 0], [0, -1], [1, 0], [0, 1]):
                with self.subTest(key=key, position=position):
                    data = {'grid': [[1]], 'start': [0, 0], 'goal': [0, 0]}
                    data[key] = position
                    with self.assertRaisesRegex(ValueError, key + '.*outside'):
                        self.load_level(data)

    def test_start_and_goal_on_void_are_rejected(self):
        for key in ('start', 'goal'):
            with self.subTest(key=key):
                data = {'grid': [[1, 0]], 'start': [0, 0], 'goal': [0, 0]}
                data[key] = [0, 1]
                with self.assertRaisesRegex(ValueError, key + '.*void'):
                    self.load_level(data)

    def test_invalid_json_has_location_and_preserves_cause(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'broken.json'
            path.write_text('{"grid":', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Invalid level JSON.*line') as caught:
                Board(str(path))
            self.assertIsInstance(caught.exception.__cause__, json.JSONDecodeError)

    def test_missing_file_keeps_native_file_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                Board(str(Path(directory) / 'missing.json'))

    def test_name_is_optional_and_extra_metadata_is_accepted(self):
        board = self.load_level({
            'grid': [[1]], 'start': [0, 0], 'goal': [0, 0],
            'metadata': {'difficulty': 'demo'},
        })
        self.assertTrue(board.is_goal(board.get_initial_state()))


class BFSCompatibilityTests(BoardFixture):
    def test_demo_bfs_regression_and_replay(self):
        level = Path(__file__).resolve().parents[1] / 'levels' / 'level_01.json'
        board = Board(str(level))
        self.assertEqual((board.start_r, board.start_c), (1, 1))
        self.assertEqual((board.goal_r, board.goal_c), (1, 6))
        result = BFSSolver(board).solve()
        self.assertTrue(result.success)
        self.assertEqual(result.actions, ['R', 'R', 'D', 'L', 'U', 'R', 'R'])
        self.assertEqual(result.solution_length, 7)
        self.assertEqual(result.expanded_nodes, 35)
        state = board.get_initial_state()
        for action in result.actions:
            state = board.transition(state, action)
            self.assertIsNotNone(state)
        self.assertTrue(board.is_goal(state))

    def test_bfs_initial_goal_is_a_successful_empty_solution(self):
        board = self.make_board([[1]], start=[0, 0], goal=[0, 0])
        result = BFSSolver(board).solve()
        self.assertEqual(result.actions, [])
        self.assertTrue(result.success)
        self.assertEqual(result.solution_length, 0)
        self.assertEqual(result.expanded_nodes, 0)

    def test_bfs_unsolvable_board_reports_failure(self):
        board = self.make_board([[1, 0, 1]], start=[0, 0], goal=[0, 2])
        result = BFSSolver(board).solve()
        self.assertIsNone(result.actions)
        self.assertFalse(result.success)
        self.assertEqual(result.expanded_nodes, 1)


if __name__ == '__main__':
    unittest.main()
