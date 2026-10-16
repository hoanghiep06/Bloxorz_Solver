import heapq
from collections import defaultdict
from typing import List, Optional
from src.solvers.base_solver import BaseSolver
from src.core.board import ACTIONS
from src.core.state import BloxorzState

class AStarSolver(BaseSolver):
    def heuristic(self, state: BloxorzState) -> float:
        # Gợi ý: Manhattan distance chia đôi (relaxed point)
        # Có thể cộng thêm penalty nếu state không standing[cite: 6, 7] // Cộng thêm penalty làm mất consistency!!!
        dist = (abs(state.r - self.board.goal_r) + abs(state.c - self.board.goal_c)) / 2.0
        return dist
        # Prove tính nhất quán (consistent): Khi giả sử cost_function(n) >= 1, tính nhất quán hiển nhiên, vì tối đa block chỉ có thể di chuyển 2 bước
        # => Manhattan distance / 2 <= 1 <= cost_function(n) (chứng minh tính nhất quán)

    def cost_function(self, state: BloxorzState) -> float:
        # Design later
        return 1
    
    def _search(self) -> Optional[List[str]]:
        # TODO [TV5]: Cài đặt Priority Queue (heapq) với f(n) = g(n) + h(n)
        # Tham khảo khung BFS để đếm self.expanded_nodes += 1 khi pop node[cite: 6, 9]
        f_n = defaultdict(lambda: float('inf'))
        path = defaultdict(list)
        initial_state = self.board.get_initial_state()
        if self.board.is_goal(initial_state):
            return []
        pq = []
        heapq.heappush(pq, (0, initial_state, []))
        visited = set()
        while pq:
            weight, current_state, current_path = heapq.heappop(pq)
            self.expanded_nodes += 1
            visited.add(current_state)
            if self.board.is_goal(current_state):
                return current_path
            if f_n[current_state] >= weight:
                f_n[current_state] = weight
                path[current_state] = current_path
            for action in ACTIONS:
                next_state = self.board.transition(current_state, action)
                if next_state and next_state not in visited:
                    heapq.heappush(pq, (self.heuristic(next_state) + self.cost_function(next_state), next_state, current_path + [action]))
                    
        return None
    