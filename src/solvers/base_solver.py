import time
import tracemalloc
from abc import ABC, abstractmethod
from typing import List, Optional
from src.core.board import Board

class SearchResult:
    def __init__(self, actions: Optional[List[str]], time_taken: float, peak_memory: float, expanded_nodes: int):
        self.actions = actions
        self.success = actions is not None
        self.solution_length = len(actions) if actions is not None else 0
        self.time_taken = time_taken          # giây
        self.peak_memory = peak_memory        # KiB, traced Python allocations, not RSS
        self.expanded_nodes = expanded_nodes  # Processed pops, excluding discarded stale entries

    def __repr__(self):
        moves = 'None' if self.actions is None else (' -> '.join(self.actions) or '(empty)')
        return (f"--- Result ---\n"
                f"Success: {self.success}\n"
                f"Moves ({self.solution_length}): {moves}\n"
                f"Expanded Nodes: {self.expanded_nodes}\n"
                f"Search Time: {self.time_taken:.4f} s\n"
                f"Peak Python Memory: {self.peak_memory:.2f} KiB\n")

class BaseSolver(ABC):
    def __init__(self, board: Board):
        self.board = board
        self.expanded_nodes = 0

    def solve(self) -> SearchResult:
        """Measure _search in seconds and peak traced Python allocations (KiB).

        Existing external/nested tracing is rejected without changing it: an
        independent peak cannot be measured while preserving that tracing session.
        Search exceptions propagate after the owned tracing session is stopped.
        Solver classes own node counting; discarded stale entries do not count.
        """
        self.expanded_nodes = 0
        if tracemalloc.is_tracing():
            raise RuntimeError(
                "BaseSolver.solve() requires tracemalloc to be stopped; "
                "an external or nested tracing session is already active."
            )
        tracemalloc.start()
        try:
            start_time = time.perf_counter()
            actions = self._search()
            end_time = time.perf_counter()
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        return SearchResult(
            actions=actions,
            time_taken=end_time - start_time,
            peak_memory=peak / 1024.0,  # Convert bytes -> KiB
            expanded_nodes=self.expanded_nodes
        )

    @abstractmethod
    def _search(self) -> Optional[List[str]]:
        """Hàm trừu tượng mà mỗi thành viên cần viết code logic."""
        pass
