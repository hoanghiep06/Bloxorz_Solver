import math
import tracemalloc
import unittest
from pathlib import Path
from unittest.mock import patch

from src.core.board import Board
from src.solvers.base_solver import BaseSolver, SearchResult


class DummySolver(BaseSolver):
    """Configured outcome and counter updates; no search algorithm."""

    def __init__(self, board, actions=None, error=None):
        super().__init__(board)
        self.actions = actions
        self.error = error
        self.entry_counts = []
        self.tracing_during_search = []

    def _search(self):
        self.entry_counts.append(self.expanded_nodes)
        self.tracing_during_search.append(tracemalloc.is_tracing())
        self.expanded_nodes += 3
        if self.error is not None:
            raise self.error
        return self.actions


class BaseSolverTests(unittest.TestCase):
    def setUp(self):
        self.assertFalse(tracemalloc.is_tracing(), 'Run tests without external tracemalloc tracing.')
        self.addCleanup(self.stop_tracing)
        level = Path(__file__).resolve().parents[1] / 'levels' / 'level_01.json'
        self.board = Board(str(level))

    @staticmethod
    def stop_tracing():
        if tracemalloc.is_tracing():
            tracemalloc.stop()

    def test_abstract_solver_requires_search_implementation(self):
        with self.assertRaises(TypeError):
            BaseSolver(self.board)

    def test_board_reference_is_preserved(self):
        self.assertIs(DummySolver(self.board).board, self.board)

    def test_action_list_reports_success_and_length(self):
        result = DummySolver(self.board, actions=['R', 'D']).solve()
        self.assertIsInstance(result, SearchResult)
        self.assertEqual(result.actions, ['R', 'D'])
        self.assertTrue(result.success)
        self.assertEqual(result.solution_length, 2)
        self.assertEqual(result.expanded_nodes, 3)

    def test_empty_list_is_successful_zero_length_solution(self):
        result = DummySolver(self.board, actions=[]).solve()
        self.assertEqual(result.actions, [])
        self.assertTrue(result.success)
        self.assertEqual(result.solution_length, 0)
        self.assertIn('Moves (0): (empty)', repr(result))
        self.assertNotIn('Moves (0): None', repr(result))

    def test_none_is_failure(self):
        result = DummySolver(self.board, actions=None).solve()
        self.assertIsNone(result.actions)
        self.assertFalse(result.success)
        self.assertEqual(result.solution_length, 0)
        self.assertIn('Moves (0): None', repr(result))

    def test_expanded_nodes_reset_before_each_search(self):
        solver = DummySolver(self.board, actions=[])
        solver.expanded_nodes = 999
        first, second = solver.solve(), solver.solve()
        self.assertEqual(solver.entry_counts, [0, 0])
        self.assertEqual((first.expanded_nodes, second.expanded_nodes), (3, 3))

    def test_elapsed_time_uses_perf_counter_in_seconds(self):
        with patch('src.solvers.base_solver.time.perf_counter', side_effect=[10.0, 10.25]) as counter:
            result = DummySolver(self.board, actions=[]).solve()
        self.assertEqual(counter.call_count, 2)
        self.assertEqual(result.time_taken, 0.25)

    def test_memory_uses_peak_not_current_and_converts_bytes_to_kib(self):
        with patch('src.solvers.base_solver.tracemalloc.get_traced_memory', return_value=(512, 4096)):
            result = DummySolver(self.board, actions=[]).solve()
        self.assertEqual(result.peak_memory, 4.0)
        self.assertIn('Peak Python Memory: 4.00 KiB', repr(result))

    def test_real_metrics_are_finite_and_nonnegative(self):
        result = DummySolver(self.board, actions=[]).solve()
        for metric in (result.time_taken, result.peak_memory):
            self.assertTrue(math.isfinite(metric))
            self.assertGreaterEqual(metric, 0)

    def test_allocations_inside_search_contribute_to_peak(self):
        solver = DummySolver(self.board)

        def allocate_and_return():
            allocation = bytearray(256 * 1024)
            self.assertEqual(len(allocation), 256 * 1024)
            return []

        with patch.object(solver, '_search', side_effect=allocate_and_return):
            result = solver.solve()
        self.assertGreaterEqual(result.peak_memory, 256.0)

    def test_tracing_active_inside_search_and_stopped_on_success(self):
        solver = DummySolver(self.board, actions=[])
        solver.solve()
        self.assertEqual(solver.tracing_during_search, [True])
        self.assertFalse(tracemalloc.is_tracing())

    def test_search_exception_is_preserved_and_tracing_is_stopped(self):
        error = ValueError('search failed')
        solver = DummySolver(self.board, error=error)
        with self.assertRaises(ValueError) as caught:
            solver.solve()
        self.assertIs(caught.exception, error)
        self.assertEqual(solver.tracing_during_search, [True])
        self.assertFalse(tracemalloc.is_tracing())

    def test_solver_can_be_reused_after_failed_search(self):
        solver = DummySolver(self.board, error=RuntimeError('failed'))
        with self.assertRaises(RuntimeError):
            solver.solve()
        solver.error = None
        solver.actions = []
        result = solver.solve()
        self.assertTrue(result.success)
        self.assertEqual(solver.entry_counts, [0, 0])
        self.assertFalse(tracemalloc.is_tracing())

    def test_tracing_is_cleaned_up_on_base_exception(self):
        solver = DummySolver(self.board, error=KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):
            solver.solve()
        self.assertFalse(tracemalloc.is_tracing())

    def test_clock_error_also_cleans_up_tracing(self):
        with patch('src.solvers.base_solver.time.perf_counter', side_effect=RuntimeError('clock failed')):
            with self.assertRaisesRegex(RuntimeError, 'clock failed'):
                DummySolver(self.board, actions=[]).solve()
        self.assertFalse(tracemalloc.is_tracing())

    def test_memory_read_error_also_cleans_up_tracing(self):
        with patch('src.solvers.base_solver.tracemalloc.get_traced_memory', side_effect=RuntimeError('memory failed')):
            with self.assertRaisesRegex(RuntimeError, 'memory failed'):
                DummySolver(self.board, actions=[]).solve()
        self.assertFalse(tracemalloc.is_tracing())

    def test_external_tracing_is_rejected_without_stopping_or_resetting_it(self):
        solver = DummySolver(self.board, actions=[])
        tracemalloc.start()
        allocation = bytearray(128 * 1024)
        del allocation
        peak_before = tracemalloc.get_traced_memory()[1]
        with patch('src.solvers.base_solver.tracemalloc.stop', wraps=tracemalloc.stop) as stop:
            with self.assertRaisesRegex(RuntimeError, 'already active'):
                solver.solve()
            stop.assert_not_called()
        self.assertTrue(tracemalloc.is_tracing())
        self.assertGreaterEqual(tracemalloc.get_traced_memory()[1], peak_before)
        self.assertEqual(solver.entry_counts, [])

    def test_nested_solve_is_rejected_and_outer_measurement_is_cleaned_up(self):
        outer, inner = DummySolver(self.board), DummySolver(self.board)
        with patch.object(outer, '_search', side_effect=inner.solve):
            with self.assertRaisesRegex(RuntimeError, 'nested'):
                outer.solve()
        self.assertEqual(inner.entry_counts, [])
        self.assertFalse(tracemalloc.is_tracing())


if __name__ == '__main__':
    unittest.main()
