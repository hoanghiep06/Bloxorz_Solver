import heapq
from typing import List, Optional
from src.solvers.base_solver import BaseSolver
from src.core.board import ACTIONS
from src.core.state import BloxorzState

class AStarSolver(BaseSolver):
    def heuristic(self, state: BloxorzState) -> float:
        # Gợi ý: Manhattan distance chia đôi (relaxed point)
        # Có thể cộng thêm penalty nếu state không standing[cite: 6, 7]
        dist = (abs(state.r - self.board.goal_r) + abs(state.c - self.board.goal_c)) / 2.0
        if not state.is_standing():
            dist += 1.0
        return dist

    def _search(self) -> Optional[List[str]]:
        # TODO [TV5]: Cài đặt Priority Queue (heapq) với f(n) = g(n) + h(n)
        # Tham khảo khung BFS để đếm self.expanded_nodes += 1 khi pop node[cite: 6, 9]
        pass