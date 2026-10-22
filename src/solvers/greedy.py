import heapq
from typing import List, Optional
from src.solvers.base_solver import BaseSolver
from src.core.board import ACTIONS
from src.core.state import BloxorzState


class GreedySolver(BaseSolver):
    """Greedy Best-First Search (GBFS) solver for Bloxorz.

    Prioritizes nodes purely by an admissible-inspired relaxed Manhattan distance
    heuristic h(n) towards the target goal coordinates.
    """

    def heuristic(self, state: BloxorzState) -> float:
        """Ham Heuristic Manhattan chia doi (relaxed point) uoc luong toi dich.

        - Do moi buoc lan cua khoi di chuyen toi da 2 o tren luoi, khoang cach
          Manhattan chia doi la mot can duoi hop ly (relaxed point).
        - Dich yeu cau khoi phai o tu the STANDING. Neu khoi dang nam (HORIZONTAL
          hoac VERTICAL), bat buoc phai ton them it nhat 1 buoc xoay lat de dung
          dung vao o Goal.
        """
        dist = (abs(state.r - self.board.goal_r) + abs(state.c - self.board.goal_c)) / 2.0
        if not state.is_standing():
            dist += 1.0
        return dist

    def _search(self) -> Optional[List[str]]:
        initial_state = self.board.get_initial_state()
        if self.board.is_goal(initial_state):
            return []

        # Priority Queue luu tuple: (h_cost, tie_breaker_counter, state, path)
        counter = 0
        h_init = self.heuristic(initial_state)
        heap = [(h_init, counter, initial_state, [])]
        visited = {initial_state}

        while heap:
            _, _, current_state, path = heapq.heappop(heap)
            self.expanded_nodes += 1

            if self.board.is_goal(current_state):
                return path

            for action in ACTIONS:
                next_state = self.board.transition(current_state, action)
                if next_state is not None and next_state not in visited:
                    visited.add(next_state)
                    counter += 1
                    h_next = self.heuristic(next_state)
                    heapq.heappush(heap, (h_next, counter, next_state, path + [action]))

        return None
