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
from src.solvers.ucs import UCSSolver
from src.solvers.UCS_Algorithm.cost_functions import UniformCost,TunedWeightCost,INVERSE_ACTIONS


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
        actual = AStarSolver(board,cost_function=UniformCost()).solve()
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

    def assert_weighted_optimum(self, board, root=None):
        astar,ucs=AStarSolver(board),UCSSolver(board)
        ar,ur=astar.solve(start_state=root),ucs.solve(start_state=root)
        self.assertTrue(ar.success and ur.success)
        self.assertIsInstance(astar.cost_function,TunedWeightCost)
        self.assertAlmostEqual(astar.total_cost,ucs.total_cost)
        state=board.get_initial_state() if root is None else root
        self.assertEqual(ar.start_state,state)
        last=None;cost=0.
        for action in ar.actions:
            nxt=board.transition(state,action);self.assertIsNotNone(nxt)
            cost+=astar.cost_function.calculate_cost(state,action,nxt,board,last_action=last)
            last=action if action in INVERSE_ACTIONS else None;state=nxt
        self.assertTrue(board.is_goal(state));self.assertAlmostEqual(cost,astar.total_cost)
        return astar,ar

    def test_weighted_default_matches_ucs_on_laboratory_and_prefers_cost_to_move_count(self):
        board=Board(str(Path(__file__).resolve().parents[1]/'levels/level_19.json'))
        astar,result=self.assert_weighted_optimum(board)
        bfs=BFSSolver(board).solve();state=board.get_initial_state();last=None;bfs_cost=0.
        for action in bfs.actions:
            nxt=board.transition(state,action)
            bfs_cost+=astar.cost_function.calculate_cost(state,action,nxt,board,last_action=last)
            last=action if action in INVERSE_ACTIONS else None;state=nxt
        self.assertLessEqual(astar.total_cost,bfs_cost)
        self.assertGreater(result.solution_length,bfs.solution_length)
        # Shortest-action behavior remains explicitly available through UniformCost.
        uniform=AStarSolver(board,cost_function=UniformCost()).solve()
        self.assertEqual(uniform.solution_length,bfs.solution_length)

    def test_weighted_teleport_guard_holds_before_and_after_split_and_current_cube_selection(self):
        board=self.make_board(split_switch={'cell':[1,3],'split_positions':[[1,24],[1,26]]})
        astar,result=self.assert_weighted_optimum(board)
        self.assertEqual(astar.heuristic(board.get_initial_state()),0)
        self.assertAlmostEqual(astar.total_cost,4.)
        split=board.transition(board.transition(board.get_initial_state(),'R'),'R')
        self.assertTrue(split.is_split());self.assertEqual(astar.heuristic(split),0)
        selected=board.transition(split,'SPACE')
        resumed,_=self.assert_weighted_optimum(board,selected)
        self.assertEqual(resumed.heuristic(selected),0)
        self.assertEqual(resumed.cost_function.calculate_cost(split,'SPACE',selected,board),0)

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
