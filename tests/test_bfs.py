import itertools
import json
import math
import tempfile
import tracemalloc
import unittest
from collections import Counter, deque
from pathlib import Path
from unittest.mock import patch

from src.core.board import ACTIONS, Board
from src.core.state import BloxorzState, Orientation
from src.solvers.bfs import BFSSolver


class RecordingDeque(deque):
    """Observe queue operations; a finite-state bound prevents a hanging test."""

    def __init__(self, values, pop_limit):
        values = list(values)
        super().__init__(values)
        self.enqueued = list(values)
        self.popped = []
        self.pop_limit = pop_limit

    def append(self, value):
        self.enqueued.append(value)
        super().append(value)

    def popleft(self):
        if len(self.popped) >= self.pop_limit:
            raise AssertionError('BFS exceeded the finite basic-board state bound.')
        value = super().popleft()
        self.popped.append(value)
        return value


def walks_ending_at_goal(board, depth):
    """Independent bounded exhaustive enumeration: no BFS, visited or parents."""
    solutions = []
    for actions in itertools.product(ACTIONS, repeat=depth):
        state = board.get_initial_state()
        for action in actions:
            state = board.transition(state, action)
            if state is None:
                break
        if state is not None and board.is_goal(state):
            solutions.append(list(actions))
    return solutions


def all_pairs_shortest_distances(board):
    """Floyd-Warshall oracle on all valid basic states, independent of BFSSolver."""
    states = []
    for r in range(board.rows):
        for c in range(board.cols):
            for orientation in Orientation:
                state = BloxorzState(r, c, orientation)
                if board.is_valid_state(state):
                    states.append(state)
    distances = {(source, target): (0 if source == target else math.inf)
                 for source in states for target in states}
    for source in states:
        for action in ACTIONS:
            target = board.transition(source, action)
            if target is not None:
                distances[source, target] = 1
    for via in states:
        for source in states:
            for target in states:
                distances[source, target] = min(
                    distances[source, target],
                    distances[source, via] + distances[via, target],
                )
    return distances


class BFSTests(unittest.TestCase):
    def make_board(self, grid, start, goal):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'level.json'
        path.write_text(json.dumps({'grid': grid, 'start': start, 'goal': goal}),
                        encoding='utf-8')
        return Board(str(path))

    def demo_board(self):
        path = Path(__file__).resolve().parents[1] / 'levels' / 'level_01.json'
        return Board(str(path))

    def cycle_board(self):
        # A reachable 3x3 region with reversible moves; the goal is isolated.
        return self.make_board([
            [1, 1, 1, 0, 0],
            [1, 1, 1, 0, 0],
            [1, 1, 1, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 1],
        ], [0, 0], [4, 4])

    def assert_replay(self, board, actions):
        state = board.get_initial_state()
        for index, action in enumerate(actions):
            self.assertIn(action, ACTIONS)
            state = board.transition(state, action)
            self.assertIsNotNone(state, f'Invalid replay move at index {index}')
        self.assertTrue(board.is_goal(state))

    def solve_with_queue_trace(self, board):
        queues = []

        def make_queue(values):
            queue = RecordingDeque(values, 3 * board.rows * board.cols)
            queues.append(queue)
            return queue

        with patch('src.solvers.bfs.deque', side_effect=make_queue):
            result = BFSSolver(board).solve()
        self.assertEqual(len(queues), 1)
        return result, queues[0]

    def test_demo_regression_replay_and_no_shorter_action_sequence(self):
        board = self.demo_board()
        self.assertEqual(board.get_initial_state(), BloxorzState(1, 1, Orientation.STANDING))
        self.assertEqual((board.goal_r, board.goal_c), (1, 6))
        result = BFSSolver(board).solve()
        self.assertTrue(result.success)
        self.assertEqual(result.actions, ['R', 'R', 'D', 'L', 'U', 'R', 'R'])
        self.assertEqual(result.solution_length, 7)
        self.assertEqual(result.expanded_nodes, 35)
        for depth in range(7):
            with self.subTest(shorter_depth=depth):
                self.assertEqual(walks_ending_at_goal(board, depth), [])
        self.assert_replay(board, result.actions)

    def test_start_already_goal_does_not_create_a_queue(self):
        board = self.make_board([[1]], [0, 0], [0, 0])
        with patch('src.solvers.bfs.deque') as queue:
            result = BFSSolver(board).solve()
        queue.assert_not_called()
        self.assertEqual(result.actions, [])
        self.assertTrue(result.success)
        self.assertEqual(result.solution_length, 0)
        self.assertEqual(result.expanded_nodes, 0)

    def test_isolated_start_reports_unsolvable_and_processes_only_the_start(self):
        board = self.make_board([[1, 0, 1]], [0, 0], [0, 2])
        result = BFSSolver(board).solve()
        self.assertIsNone(result.actions)
        self.assertFalse(result.success)
        self.assertEqual(result.solution_length, 0)
        self.assertEqual(result.expanded_nodes, 1)

    def test_cycle_exhausts_reachable_states_without_duplicate_enqueue(self):
        board = self.cycle_board()
        result, queue = self.solve_with_queue_trace(board)
        self.assertFalse(result.success)
        self.assertEqual(result.expanded_nodes, 20)
        self.assertEqual(len(queue.popped), result.expanded_nodes)
        self.assertEqual(len(queue.enqueued), len(set(queue.enqueued)))
        self.assertEqual(len(queue.popped), len(set(queue.popped)))
        self.assertEqual(set(queue.enqueued), set(queue.popped))
        # An explicit cycle exists: R from start, then L returns to start.
        start = board.get_initial_state()
        right = board.transition(start, 'R')
        self.assertIsNotNone(right)
        self.assertEqual(board.transition(right, 'L'), start)

    def test_duplicate_incoming_paths_do_not_overwrite_first_discovery(self):
        board = self.make_board([[1] * 4 for _ in range(4)], [0, 0], [3, 3])
        with patch.object(board, 'transition', wraps=board.transition) as transition:
            result, queue = self.solve_with_queue_trace(board)
        targets = Counter()
        for call in transition.call_args_list:
            source, action = call.args
            target = Board.transition(board, source, action)
            if target is not None:
                targets[target] += 1
        self.assertTrue(any(count > 1 for count in targets.values()))
        self.assertEqual(len(queue.enqueued), len(set(queue.enqueued)))
        self.assertEqual(result.actions, ['D', 'D', 'R', 'R'])
        self.assertEqual(result.solution_length, 4)
        self.assert_replay(board, result.actions)

    def test_multiple_shortest_solutions_follow_action_order(self):
        board = self.make_board([[1] * 4 for _ in range(4)], [0, 0], [3, 3])
        for depth in range(4):
            self.assertEqual(walks_ending_at_goal(board, depth), [])
        solutions = walks_ending_at_goal(board, 4)
        self.assertEqual(solutions, [['D', 'D', 'R', 'R'], ['R', 'R', 'D', 'D']])
        result = BFSSolver(board).solve()
        self.assertEqual(result.actions, solutions[0])
        self.assert_replay(board, result.actions)

    def test_all_81_start_goal_pairs_match_independent_floyd_warshall(self):
        grid = [[1] * 3 for _ in range(3)]
        oracle_board = self.make_board(grid, [0, 0], [2, 2])
        distances = all_pairs_shortest_distances(oracle_board)
        cells = list(itertools.product(range(3), repeat=2))
        for start, goal in itertools.product(cells, repeat=2):
            with self.subTest(start=start, goal=goal):
                board = self.make_board(grid, list(start), list(goal))
                result = BFSSolver(board).solve()
                expected = distances[
                    BloxorzState(*start, Orientation.STANDING),
                    BloxorzState(*goal, Orientation.STANDING),
                ]
                self.assertEqual(result.success, expected != math.inf)
                if result.success:
                    self.assertEqual(result.solution_length, expected)
                    self.assert_replay(board, result.actions)
                else:
                    self.assertIsNone(result.actions)

    def test_long_parent_chain_reconstructs_every_action_in_order(self):
        board = self.make_board([[1] * 301], [0, 0], [0, 300])
        result = BFSSolver(board).solve()
        self.assertTrue(result.success)
        self.assertEqual(result.actions, ['R'] * 200)
        self.assertEqual(result.solution_length, 200)
        self.assertEqual(result.expanded_nodes, 201)
        self.assert_replay(board, result.actions)

    def test_orientation_is_part_of_visited_identity(self):
        result, queue = self.solve_with_queue_trace(self.cycle_board())
        orientations_by_position = {}
        for state in queue.popped:
            orientations_by_position.setdefault((state.r, state.c), set()).add(state.orientation)
        self.assertTrue(any(len(values) > 1 for values in orientations_by_position.values()))
        self.assertEqual(result.expanded_nodes, 20)

    def test_existing_bridge_flags_are_preserved_without_claiming_bridge_effects(self):
        board = self.make_board([[1] * 4], [0, 0], [0, 3])
        initial = BloxorzState(0, 0, Orientation.STANDING, (True, False))
        with patch.object(board, 'get_initial_state', return_value=initial):
            result, queue = self.solve_with_queue_trace(board)
            self.assert_replay(board, result.actions)
        self.assertEqual(result.actions, ['R', 'R'])
        self.assertTrue(all(state.bridges_state == (True, False) for state in queue.enqueued))

    def test_search_does_not_mutate_any_observed_state_or_the_board(self):
        board = self.demo_board()
        grid_before = json.dumps(board.grid)
        placement_before = (board.start_r, board.start_c, board.goal_r, board.goal_c)
        observed = {}
        transition = board.transition

        def record(state):
            observed.setdefault(id(state), (
                state, (state.r, state.c, state.orientation, state.bridges_state), hash(state),
            ))

        def checked_transition(state, action):
            record(state)
            next_state = transition(state, action)
            if next_state is not None:
                record(next_state)
            return next_state

        with patch.object(board, 'transition', side_effect=checked_transition):
            result = BFSSolver(board).solve()
        self.assertTrue(result.success)
        for state, identity, original_hash in observed.values():
            self.assertEqual((state.r, state.c, state.orientation, state.bridges_state), identity)
            self.assertEqual(hash(state), original_hash)
        self.assertEqual(json.dumps(board.grid), grid_before)
        self.assertEqual((board.start_r, board.start_c, board.goal_r, board.goal_c), placement_before)

    def test_all_successors_and_goal_checks_are_delegated_to_board(self):
        board = self.demo_board()
        with patch.object(board, 'transition', wraps=board.transition) as transition:
            with patch.object(board, 'is_goal', wraps=board.is_goal) as goal:
                result = BFSSolver(board).solve()
        self.assertEqual(goal.call_count, result.expanded_nodes + 1)
        actions = [call.args[1] for call in transition.call_args_list]
        self.assertEqual(actions, ACTIONS * (result.expanded_nodes - 1))

    def test_fifo_processes_goal_and_does_not_count_queued_but_unprocessed_states(self):
        result, queue = self.solve_with_queue_trace(self.demo_board())
        self.assertEqual(result.expanded_nodes, len(queue.popped))
        self.assertGreater(len(queue.enqueued), len(queue.popped))
        self.assertEqual(queue.popped, queue.enqueued[:len(queue.popped)])
        self.assertEqual(queue.popped[-1], BloxorzState(1, 6, Orientation.STANDING))

    def test_metrics_are_finite_nonnegative_and_match_the_solution(self):
        result = BFSSolver(self.demo_board()).solve()
        for metric in (result.time_taken, result.peak_memory):
            self.assertTrue(math.isfinite(metric))
            self.assertGreaterEqual(metric, 0)
        self.assertEqual(result.solution_length, len(result.actions))
        self.assertEqual(result.expanded_nodes, 35)
        self.assertFalse(tracemalloc.is_tracing())

    def test_repeated_solves_reset_counter_and_reconstruct_fresh_paths(self):
        solver = BFSSolver(self.demo_board())
        first = solver.solve()
        second = solver.solve()
        self.assertEqual(first.actions, second.actions)
        self.assertIsNot(first.actions, second.actions)
        self.assertEqual(first.expanded_nodes, 35)
        self.assertEqual(second.expanded_nodes, 35)

    def test_raw_search_keeps_list_empty_list_and_none_contract(self):
        cases = [
            (self.make_board([[1] * 4], [0, 0], [0, 3]), ['R', 'R']),
            (self.make_board([[1]], [0, 0], [0, 0]), []),
            (self.make_board([[1, 0, 1]], [0, 0], [0, 2]), None),
        ]
        for board, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(BFSSolver(board)._search(), expected)
        self.assertFalse(tracemalloc.is_tracing())

    def test_core_exception_propagates_and_base_solver_cleans_up_measurement(self):
        board = self.demo_board()
        error = ValueError('transition failed')
        with patch.object(board, 'transition', side_effect=error):
            with self.assertRaises(ValueError) as caught:
                BFSSolver(board).solve()
        self.assertIs(caught.exception, error)
        self.assertFalse(tracemalloc.is_tracing())


if __name__ == '__main__':
    unittest.main()
