from collections import deque
from typing import List, Optional
from src.solvers.base_solver import BaseSolver
from src.core.board import ACTIONS

class BFSSolver(BaseSolver):
    def _search(self) -> Optional[List[str]]:
        initial_state = self.board.get_initial_state()
        if self.board.is_goal(initial_state):
            return []

        # queue lưu: (state_hien_tai, danh_sach_action_da_di)
        queue = deque([(initial_state, [])])
        visited = {initial_state}

        while queue:
            current_state, path = queue.popleft()
            self.expanded_nodes += 1

            if self.board.is_goal(current_state):
                return path

            for action in ACTIONS:
                next_state = self.board.transition(current_state, action)
                if next_state is not None and next_state not in visited:
                    visited.add(next_state)
                    queue.append((next_state, path + [action]))

        return None