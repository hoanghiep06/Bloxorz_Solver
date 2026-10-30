from itertools import count
import heapq
from typing import List, Optional, Tuple

from src.core.board import ACTIONS, Board
from src.core.state import BloxorzState
from src.solvers.base_solver import BaseSolver
from src.solvers.UCS_Algorithm.cost_functions import near_void_cell

# Bộ trọng số mặc định đã được tìm thấy qua quá trình thực nghiệm Grid Search & Cross-Validation:
# (w_orientation=1.0, w_split=1.0, w_edge=0.0, w_fragile=0.0)
DEFAULT_GBFS_WEIGHTS = (1.0, 1.0, 0.0, 0.0)


class GreedySolver(BaseSolver):
    """Greedy Best-First Search (GBFS) solver for Bloxorz.

    Prioritizes nodes purely by a weighted relaxed Manhattan distance
    heuristic h(n) towards the target goal coordinates.
    Supports basic and advanced mechanics (fragile, switches/bridges, split cubes).

    Heuristic formula:
        h(s) = distance + w_orientation * orient_term + w_split * split_term
               + w_edge * edge_term + w_fragile * fragile_term

    Tuned parameter defaults (from 4x4x4x4 grid search & grouped cross-validation):
        w_orientation = 1.0 (phạt khi khối chưa đứng thẳng trên đích)
        w_split = 1.0       (phạt khi 2 khối đang phân tách cần hợp nhất)
        w_edge = 0.0        (phạt mỗi ô đang đứng nằm sát mép vực)
        w_fragile = 0.0     (phạt mỗi ô mong manh đang chiếm đóng)
    """

    def __init__(
        self,
        board: Board,
        w_orientation: float = 1.0,
        w_split: float = 1.0,
        w_edge: float = 0.0,
        w_fragile: float = 0.0,
        heuristic_weights: Optional[Tuple[float, float, float, float]] = None,
    ):
        super().__init__(board)
        if heuristic_weights is not None:
            self.w_orientation, self.w_split, self.w_edge, self.w_fragile = (
                float(x) for x in heuristic_weights
            )
        else:
            self.w_orientation = float(w_orientation)
            self.w_split = float(w_split)
            self.w_edge = float(w_edge)
            self.w_fragile = float(w_fragile)
        self.solution: Optional[List[str]] = None

    def heuristic(self, state: BloxorzState) -> float:
        """Hàm Heuristic đa tiêu chí có trọng số ước lượng khoảng cách tới đích.

        - Do mỗi bước lăn của khối di chuyển tối đa 2 ô trên lưới, khoảng cách
          Manhattan chia đôi là một chặn dưới hợp lý (relaxed point).
        - Đích yêu cầu khối phải ở tư thế STANDING. Nếu khối đang nằm (HORIZONTAL
          hoặc VERTICAL), bắt buộc phải tốn thêm ít nhất 1 bước xoay lật để dựng
          đứng vào ô Goal (phạt với trọng số w_orientation).
        - Khi ở trạng thái tách (SPLIT), 2 khối 1x1x1 cần di chuyển kề nhau để hợp
          nhất và đưa khối hoàn chỉnh về đích đứng thẳng (phạt với trọng số w_split).
        - Các yếu tố rủi ro địa hình (mép vực w_edge, ô mong manh w_fragile) được
          bổ sung theo mô hình trọng số điều chỉnh.
        """
        occ = state.get_occupied_cells()
        if state.is_split():
            c0, c1 = state.cubes
            inter_dist = abs(c0[0] - c1[0]) + abs(c0[1] - c1[1])
            d0 = abs(c0[0] - self.board.goal_r) + abs(c0[1] - self.board.goal_c)
            d1 = abs(c1[0] - self.board.goal_r) + abs(c1[1] - self.board.goal_c)
            distance = max(0.0, (inter_dist - 1.0) / 2.0) + min(d0, d1) / 2.0
            split_term = 1.0
            orient_term = 0.0
        else:
            distance = (abs(state.r - self.board.goal_r) + abs(state.c - self.board.goal_c)) / 2.0
            split_term = 0.0
            orient_term = 0.0 if state.is_standing() else 1.0

        h_val = distance + self.w_orientation * orient_term + self.w_split * split_term

        if self.w_edge > 0:
            edge_term = sum(1.0 for cell in occ if near_void_cell(self.board, state, cell))
            h_val += self.w_edge * edge_term

        if self.w_fragile > 0:
            fragile_count = 0
            for r, c in occ:
                if (hasattr(self.board, 'is_fragile_tile') and self.board.is_fragile_tile(r, c)) or self.board.grid[r][c] in (3, '3'):
                    fragile_count += 1
            h_val += self.w_fragile * fragile_count

        return h_val

    def _search(self) -> Optional[List[str]]:
        initial_state = self.get_start_state()
        self.solution = None
        if self.board.is_goal(initial_state):
            self.solution = []
            return []

        # Priority Queue lưu tuple: (h_cost, tie_breaker_counter, state, path)
        counter = count()
        h_init = self.heuristic(initial_state)
        heap = [(h_init, next(counter), initial_state, [])]
        visited = {initial_state}

        while heap:
            _, _, current_state, path = heapq.heappop(heap)
            self.expanded_nodes += 1

            if self.board.is_goal(current_state):
                self.solution = path
                return path

            actions = self.board.get_actions(current_state) if hasattr(self.board, 'get_actions') else ACTIONS
            for action in actions:
                next_state = self.board.transition(current_state, action)
                if next_state is not None and next_state not in visited:
                    visited.add(next_state)
                    h_next = self.heuristic(next_state)
                    heapq.heappush(heap, (h_next, next(counter), next_state, path + [action]))

        self.solution = None
        return None
