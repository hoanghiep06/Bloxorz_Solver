from typing import List, Optional
from src.solvers.base_solver import BaseSolver
from src.core.board import ACTIONS

class IDSSolver(BaseSolver):
    """Iterative Deepening Search (IDS) solver for Bloxorz.

    Supports basic boards as well as advanced mechanics (fragile tiles,
    bridges/switches, and split cubes via 'SPACE' cube switching).
    """

    def _search(self) -> Optional[List[str]]:
        initial_state = self.get_start_state()
        limit = 0
        prev_visited_count = -1

        while True:
            result, visited_count = self._depth_limited(initial_state, limit)
            if result is not None:
                return result

            # Số state chạm tới không tăng khi nới limit => đã duyệt hết
            # không gian trạng thái, map vô nghiệm.
            if visited_count == prev_visited_count:
                return None
            prev_visited_count = visited_count
            limit += 1

    def _depth_limited(self, initial_state, limit):
        """DFS giới hạn độ sâu. Trả về (path hoặc None, số state đã chạm tới)."""
        best_depth = {}
        parent = {}
        stack = [(initial_state, 0, None, None)]

        while stack:
            state, depth, prev_state, action_in = stack.pop()

            if state in best_depth and best_depth[state] <= depth:
                continue
            best_depth[state] = depth
            parent[state] = (prev_state, action_in)
            self.expanded_nodes += 1

            if self.board.is_goal(state):
                return self._build_path(parent, state), len(best_depth)

            if depth == limit:
                continue

            actions = self.board.get_actions(state) if hasattr(self.board, 'get_actions') else ACTIONS
            for action in reversed(actions):
                next_state = self.board.transition(state, action)
                if next_state is None:
                    continue
                if next_state in best_depth and best_depth[next_state] <= depth + 1:
                    continue
                stack.append((next_state, depth + 1, state, action))

        return None, len(best_depth)

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
