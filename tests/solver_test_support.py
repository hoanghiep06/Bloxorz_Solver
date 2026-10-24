import time
from src.solvers.base_solver import BaseSolver

class SlowSolver(BaseSolver):
    def _search(self):
        time.sleep(2)
        return []

class FailingSolver(BaseSolver):
    def _search(self):
        raise ValueError('deliberate worker failure')
