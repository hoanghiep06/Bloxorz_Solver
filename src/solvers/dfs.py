from typing import List, Optional
from src.solvers.base_solver import BaseSolver
from src.core.board import ACTIONS


class DFSSolver(BaseSolver):
    def _search(self) -> Optional[List[str]]:
        initial_state = self.board.get_initial_state()

        # stack lưu: (state, state_cha, action_tu_cha_sang_state)
        stack = [(initial_state, None, None)]
        # parent đồng thời là tập visited: state -> (state_cha, action)
        parent = {}

        while stack:
            current_state, prev_state, action_in = stack.pop()

            # Entry cũ (state đã được mở qua nhánh khác): bỏ, không đếm
            if current_state in parent:
                continue
            parent[current_state] = (prev_state, action_in)
            self.expanded_nodes += 1

            if self.board.is_goal(current_state):
                return self._build_path(parent, current_state)

            # Đảo ngược để U được duyệt trước (stack LIFO)
            for action in reversed(ACTIONS):
                next_state = self.board.transition(current_state, action)
                if next_state is not None and next_state not in parent:
                    stack.append((next_state, current_state, action))

        return None

    @staticmethod
    def _build_path(parent, state) -> List[str]:
        path = []
        prev_state, action = parent[state]
        while prev_state is not None:
            path.append(action)
            state = prev_state
            prev_state, action = parent[state]
        path.reverse()
        return path