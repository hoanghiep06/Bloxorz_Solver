"""A* optimality regressions across split teleport transitions."""
import json
import tempfile
import unittest
from collections import deque
from pathlib import Path

from src.core.board import Board
from src.core.state import BloxorzState, Orientation
from src.solvers.astar import AStarSolver
from src.solvers.bfs import BFSSolver


class AStarRegressionTests(unittest.TestCase):
    def make_board(self, **updates):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'level.json'
        data = {'grid': [[1] * 30 for _ in range(3)],
                'start': [1, 0], 'goal': [1, 27]}
        data.update(updates)
        path.write_text(json.dumps(data), encoding='utf-8')
        return Board(str(path))

    def assert_same_optimum(self, board):
        expected = BFSSolver(board).solve()
        actual = AStarSolver(board).solve()
        self.assertEqual(actual.success, expected.success)
        self.assertEqual(actual.solution_length, expected.solution_length)
        if actual.success:
            state = board.get_initial_state()
            for action in actual.actions:
                state = board.transition(state, action)
                self.assertIsNotNone(state)
            self.assertTrue(board.is_goal(state))
        return actual

    def test_teleport_heuristic_does_not_exceed_four_move_solution(self):
        board = self.make_board(split_switch={
            'cell': [1, 3], 'split_positions': [[1, 24], [1, 26]],
        })
        result = self.assert_same_optimum(board)
        self.assertEqual(result.solution_length, 4)
        self.assertLessEqual(AStarSolver(board).heuristic(board.get_initial_state()), 4)

    def test_split_switch_in_switch_list_is_also_supported(self):
        board = self.make_board(switches=[{
            'cell': [1, 3], 'type': 'split',
            'split_positions': [[1, 24], [1, 26]],
        }])
        self.assertEqual(self.assert_same_optimum(board).solution_length, 4)
        self.assertLessEqual(AStarSolver(board).heuristic(board.get_initial_state()), 4)

    def test_all_reachable_heuristics_are_admissible_and_consistent(self):
        board = self.make_board(
            grid=[[1] * 9 for _ in range(2)], start=[0, 0], goal=[0, 7],
            split_switch={'cell': [0, 3], 'split_positions': [[0, 4], [0, 6]]},
        )
        initial = board.get_initial_state()
        seen, pending, edges, reverse = {initial}, deque([initial]), [], {}
        while pending:
            state = pending.popleft()
            for action in board.get_actions(state):
                target = board.transition(state, action)
                if target is None:
                    continue
                edges.append((state, target))
                reverse.setdefault(target, []).append(state)
                if target not in seen:
                    seen.add(target)
                    pending.append(target)
        distance = {state: 0 for state in seen if board.is_goal(state)}
        self.assertTrue(distance)
        self.assertTrue(any(state.is_split() for state in seen))
        pending = deque(distance)
        while pending:
            target = pending.popleft()
            for state in reverse.get(target, ()):
                if state not in distance:
                    distance[state] = distance[target] + 1
                    pending.append(state)
        solver = AStarSolver(board)
        for state, remaining in distance.items():
            self.assertGreaterEqual(solver.heuristic(state), 0)
            self.assertLessEqual(solver.heuristic(state), remaining)
        for source, target in edges:
            self.assertLessEqual(solver.heuristic(source), 1 + solver.heuristic(target))

    def test_unsolvable_split_board_reports_no_solution(self):
        board = self.make_board(
            grid=[[1, 1, 1, 1, 0, 1]], start=[0, 0], goal=[0, 5],
            split_switch={'cell': [0, 3], 'split_positions': [[0, 0], [0, 2]]},
        )
        self.assertFalse(self.assert_same_optimum(board).success)

    def test_basic_board_keeps_nonzero_heuristic_and_optimal_solution(self):
        path = Path(__file__).resolve().parents[1] / 'levels' / 'level_01.json'
        board = Board(str(path))
        solver = AStarSolver(board)
        self.assertGreater(solver.heuristic(board.get_initial_state()), 0)
        self.assertEqual(solver.heuristic(BloxorzState(
            board.goal_r, board.goal_c, Orientation.STANDING)), 0)
        self.assertEqual(self.assert_same_optimum(board).solution_length, 7)


if __name__ == '__main__':
    unittest.main()
