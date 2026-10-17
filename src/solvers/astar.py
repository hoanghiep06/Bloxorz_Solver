import heapq
from collections import defaultdict
from typing import List, Optional
from src.solvers.base_solver import BaseSolver
from src.core.board import ACTIONS
from src.core.state import BloxorzState

class AStarSolver(BaseSolver):
    def manhattan_dist(self, r, c):
        return (abs(r - self.board.goal_r) + abs(c - self.board.goal_c))
    
    def heuristic(self, state: BloxorzState) -> float:
        # Heuristic: min Manhattan distance of occupied block / 2
        # Added penalty of 0.5 if not state.is_standing
        occupied = state.get_occupied_cells()
        dist = float('inf')
        
        for block in occupied:
            curr = self.manhattan_dist(block[0], block[1]) / 2
            if dist > curr: dist = curr
            
        if not state.is_standing: dist += 0.5
        return dist
        # Prove tính nhất quán (consistent): Với giả sử cost_function(n) >= 1
        # Đpcm: h(N) <= h(P) + c(N, P) với N là node ban đầu và P là node hàng xóm
        # Viết lại: h(N) - h(P) <= c(N, P) <= 1, gọi d(n) là min Manhattan distance tới đích, ta có 2 TH
        # TH1: state.is_standing = 1 => d(N) - d(P) <= 2 (Đi tối đa 2 bước)=> h(N) - h(P) <= 2/2 = 1 (Consistent)
        # TH2: state.is_standing = 0 => d(N) - d(P) <= 1 (Khi đi 2 bước phải đi cùng orientation của block, do đó min_d chỉ cách nhau tối đa 1)
        # => h(N) - h(P) <= 1/2 + 0.5 = 1 (Consistent)
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
    