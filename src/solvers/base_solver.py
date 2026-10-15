import time
import tracemalloc
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
from src.core.board import Board
from src.core.state import BloxorzState

class SearchResult:
    def __init__(self, actions: Optional[List[str]], time_taken: float, peak_memory: float, expanded_nodes: int):
        self.actions = actions
        self.success = actions is not None
        self.solution_length = len(actions) if actions else 0
        self.time_taken = time_taken          # giây
        self.peak_memory = peak_memory        # KB
        self.expanded_nodes = expanded_nodes  # Số node đã lấy ra khỏi frontier

    def __repr__(self):
        return (f"--- Result ---\n"
                f"Success: {self.success}\n"
                f"Moves ({self.solution_length}): {' -> '.join(self.actions) if self.actions else 'None'}\n"
                f"Expanded Nodes: {self.expanded_nodes}\n"
                f"Search Time: {self.time_taken:.4f} s\n"
                f"Peak RAM: {self.peak_memory:.2f} KB\n")

class BaseSolver(ABC):
    def __init__(self, board: Board):
        self.board = board
        self.expanded_nodes = 0

    def solve(self) -> SearchResult:
        """Hàm wrapper tự động đo đạc tài nguyên."""
        self.expanded_nodes = 0
        tracemalloc.start()
        start_time = time.perf_counter()

        actions = self._search()

        end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        return SearchResult(
            actions=actions,
            time_taken=end_time - start_time,
            peak_memory=peak / 1024.0,  # Convert byte -> KB
            expanded_nodes=self.expanded_nodes
        )

    @abstractmethod
    def _search(self) -> Optional[List[str]]:
        """Hàm trừu tượng mà mỗi thành viên cần viết code logic."""
        pass