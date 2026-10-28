"""Spawned solvers return metrics, errors and can be cancelled independently of UI."""
import time
import unittest
from pathlib import Path
from src.core.board import Board
from src.gui.solver_worker import SolverJob

class SolverWorkerTests(unittest.TestCase):
    def setUp(self):
        self.board=Board(str(Path(__file__).resolve().parents[1]/'levels/level_01.json'))
    def wait(self,job):
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            outcome=job.poll()
            if outcome is not None:return outcome
            time.sleep(.01)
        self.fail('Worker did not finish.')
    def test_real_solver_returns_complete_search_result(self):
        job=SolverJob(self.board,'src.solvers.bfs','BFSSolver');self.addCleanup(job.cancel)
        ok,result=self.wait(job)
        self.assertTrue(ok);self.assertTrue(result.success)
        self.assertEqual(result.solution_length,7)
        self.assertGreater(result.expanded_nodes,0)
        self.assertGreaterEqual(result.peak_memory,0)
    def test_all_six_spawned_workers_receive_current_split_cube_identity(self):
        import importlib
        from src.gui.controller import SOLVER_SPECS
        board=Board(str(Path(__file__).parent/'fixtures/mechanics/level_05_split.json'))
        root=board.get_initial_state()
        for action in ('R','R','SPACE'):root=board.transition(root,action)
        for name,(module,cls) in SOLVER_SPECS.items():
            with self.subTest(solver=name):
                job=SolverJob(board,module,cls,root);self.addCleanup(job.cancel)
                ok,result=self.wait(job)
                self.assertTrue(ok,result);self.assertEqual(result.start_state,root)
                self.assertEqual(result.start_state.active_cube,1)
                end=root
                for action in result.actions:end=board.transition(end,action)
                self.assertTrue(board.is_goal(end))

    def test_worker_exception_is_returned_as_error(self):
        job=SolverJob(self.board,'solver_test_support','FailingSolver');self.addCleanup(job.cancel)
        ok,error=self.wait(job)
        self.assertFalse(ok);self.assertIn('deliberate worker failure',error)
    def test_slow_solver_does_not_block_poll_and_is_cancellable(self):
        start=time.monotonic()
        job=SolverJob(self.board,'solver_test_support','SlowSolver');self.addCleanup(job.cancel)
        self.assertIsNone(job.poll())
        self.assertLess(time.monotonic()-start,1)
        job.cancel();job.cancel()
        self.assertTrue(job._closed);self.assertIsNone(job.poll())

if __name__=='__main__':unittest.main()
