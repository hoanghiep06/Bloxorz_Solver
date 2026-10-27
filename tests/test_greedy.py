import json
import tempfile
import unittest
from pathlib import Path

from src.core.board import Board
from src.core.state import BloxorzState, Orientation
from src.solvers.greedy import GreedySolver, DEFAULT_GBFS_WEIGHTS


class GreedySolverTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        level = Path(__file__).resolve().parents[1] / 'levels' / 'level_01.json'
        self.board = Board(str(level))

    def make_board(self, grid, start, goal):
        data = {
            'name': 'TestBoard',
            'grid': grid,
            'start': start,
            'goal': goal,
        }
        path = Path(self.temp_dir.name) / 'custom_level.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        return Board(str(path))

    def test_heuristic_at_goal_standing_is_zero(self):
        solver = GreedySolver(self.board)
        goal_state = BloxorzState(self.board.goal_r, self.board.goal_c, Orientation.STANDING)
        self.assertEqual(solver.heuristic(goal_state), 0.0)

    def test_heuristic_standing_non_goal(self):
        solver = GreedySolver(self.board)
        state = BloxorzState(1, 1, Orientation.STANDING)
        # goal is at (1, 6). |1-1| + |1-6| = 5 -> 5 / 2.0 = 2.5
        self.assertEqual(solver.heuristic(state), 2.5)

    def test_heuristic_orientation_penalty(self):
        solver = GreedySolver(self.board)
        # Goal is (1, 6). State at (1, 6) but HORIZONTAL
        horizontal_state = BloxorzState(1, 6, Orientation.HORIZONTAL)
        # dist = 0 / 2.0 + 1.0 penalty = 1.0
        self.assertEqual(solver.heuristic(horizontal_state), 1.0)

        vertical_state = BloxorzState(1, 6, Orientation.VERTICAL)
        self.assertEqual(solver.heuristic(vertical_state), 1.0)

    def test_custom_heuristic_weights_init(self):
        # Default weights
        s1 = GreedySolver(self.board)
        self.assertEqual(
            (s1.w_orientation, s1.w_split, s1.w_edge, s1.w_fragile),
            DEFAULT_GBFS_WEIGHTS
        )

        # Keyword arguments
        s2 = GreedySolver(self.board, w_orientation=0.5, w_split=2.0, w_edge=1.0, w_fragile=3.0)
        self.assertEqual((s2.w_orientation, s2.w_split, s2.w_edge, s2.w_fragile), (0.5, 2.0, 1.0, 3.0))

        # Tuple argument
        s3 = GreedySolver(self.board, heuristic_weights=(1.5, 0.0, 2.0, 4.0))
        self.assertEqual((s3.w_orientation, s3.w_split, s3.w_edge, s3.w_fragile), (1.5, 0.0, 2.0, 4.0))

    def test_heuristic_edge_and_fragile_penalties(self):
        # Grid with fragile tile (3) and void edges
        # 1 3 1
        board = self.make_board([[1, 3, 1]], start=[0, 0], goal=[0, 2])
        # Standing on fragile cell (0, 1): dist = |0-0| + |1-2| / 2 = 0.5
        state_fragile = BloxorzState(0, 1, Orientation.STANDING)

        # Without penalties:
        s_base = GreedySolver(board, w_orientation=1.0, w_split=1.0, w_edge=0.0, w_fragile=0.0)
        self.assertEqual(s_base.heuristic(state_fragile), 0.5)

        # With fragile penalty = 2.0:
        s_frag = GreedySolver(board, w_orientation=1.0, w_split=1.0, w_edge=0.0, w_fragile=2.0)
        self.assertEqual(s_frag.heuristic(state_fragile), 0.5 + 2.0)

        # With edge penalty = 1.5 (cell (0, 1) has out-of-board neighbors top and bottom -> >= 2 unavailable neighbors):
        s_edge = GreedySolver(board, w_orientation=1.0, w_split=1.0, w_edge=1.5, w_fragile=0.0)
        self.assertEqual(s_edge.heuristic(state_fragile), 0.5 + 1.5)

    def test_solve_demo_level_01_success_and_replay(self):
        solver = GreedySolver(self.board)
        result = solver.solve()
        self.assertTrue(result.success)
        self.assertIsNotNone(result.actions)
        self.assertEqual(result.solution_length, len(result.actions))
        self.assertGreater(result.expanded_nodes, 0)

        # Replay each action to guarantee correctness
        state = self.board.get_initial_state()
        for action in result.actions:
            state = self.board.transition(state, action)
            self.assertIsNotNone(state)
        self.assertTrue(self.board.is_goal(state))

    def test_initial_state_is_goal(self):
        board = self.make_board([[1]], start=[0, 0], goal=[0, 0])
        solver = GreedySolver(board)
        result = solver.solve()
        self.assertTrue(result.success)
        self.assertEqual(result.actions, [])
        self.assertEqual(result.solution_length, 0)
        self.assertEqual(result.expanded_nodes, 0)

    def test_unsolvable_board_reports_none(self):
        board = self.make_board([[1, 0, 1]], start=[0, 0], goal=[0, 2])
        solver = GreedySolver(board)
        result = solver.solve()
        self.assertFalse(result.success)
        self.assertIsNone(result.actions)
        self.assertEqual(result.expanded_nodes, 1)

    def test_expanded_nodes_reset_on_consecutive_solves(self):
        solver = GreedySolver(self.board)
        res1 = solver.solve()
        res2 = solver.solve()
        self.assertEqual(res1.expanded_nodes, res2.expanded_nodes)
        self.assertEqual(res1.actions, res2.actions)


if __name__ == '__main__':
    unittest.main()
