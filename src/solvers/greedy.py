import heapq
from typing import List, Optional
from src.solvers.base_solver import BaseSolver
from src.core.board import ACTIONS
from src.core.state import BloxorzState

class GreedySolver(BaseSolver):
    """Greedy Best-First Search (GBFS) solver for Bloxorz.

    Prioritizes nodes purely by an admissible-inspired relaxed Manhattan distance
    heuristic h(n) towards the target goal coordinates.
    Supports basic and advanced mechanics (fragile, switches/bridges, split cubes).
    """

    def heuristic(self, state: BloxorzState) -> float:
        """Hàm Heuristic Manhattan chia đôi (relaxed point) ước lượng tới đích.

        - Do mỗi bước lăn của khối di chuyển tối đa 2 ô trên lưới, khoảng cách
          Manhattan chia đôi là một chặn dưới hợp lý (relaxed point).
        - Đích yêu cầu khối phải ở tư thế STANDING. Nếu khối đang nằm (HORIZONTAL
          hoặc VERTICAL), bắt buộc phải tốn thêm ít nhất 1 bước xoay lật để dựng
          đứng vào ô Goal.
        - Khi ở trạng thái tách (SPLIT), 2 khối 1x1x1 cần di chuyển kề nhau để hợp
          nhất và đưa khối hoàn chỉnh về đích đứng thẳng.
        """
        if state.is_split():
            c0, c1 = state.cubes
            inter_dist = abs(c0[0] - c1[0]) + abs(c0[1] - c1[1])
            d0 = abs(c0[0] - self.board.goal_r) + abs(c0[1] - self.board.goal_c)
            d1 = abs(c1[0] - self.board.goal_r) + abs(c1[1] - self.board.goal_c)
            return max(0.0, (inter_dist - 1.0) / 2.0) + min(d0, d1) / 2.0 + 1.0

        dist = (abs(state.r - self.board.goal_r) + abs(state.c - self.board.goal_c)) / 2.0
        if not state.is_standing():
            dist += 1.0
        return dist

    def _search(self) -> Optional[List[str]]:
        initial_state = self.board.get_initial_state()
        if self.board.is_goal(initial_state):
            return []

        # Priority Queue lưu tuple: (h_cost, tie_breaker_counter, state, path)
        counter = 0
        h_init = self.heuristic(initial_state)
        heap = [(h_init, counter, initial_state, [])]
        visited = {initial_state}

        while heap:
            _, _, current_state, path = heapq.heappop(heap)
            self.expanded_nodes += 1

            if self.board.is_goal(current_state):
                return path

            actions = self.board.get_actions(current_state) if hasattr(self.board, 'get_actions') else ACTIONS
            for action in actions:
                next_state = self.board.transition(current_state, action)
                if next_state is not None and next_state not in visited:
                    visited.add(next_state)
                    counter += 1
                    h_next = self.heuristic(next_state)
                    heapq.heappush(heap, (h_next, counter, next_state, path + [action]))

        return None
