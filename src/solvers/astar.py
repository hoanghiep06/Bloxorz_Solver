import heapq
from itertools import count
from typing import Any, List, Optional
from src.core.board import ACTIONS
from src.core.state import BloxorzState
from src.solvers.base_solver import BaseSolver
from src.solvers.UCS_Algorithm.cost_functions import (
    BaseCostFunction,
    TunedWeightCost,
    INVERSE_ACTIONS,
)


class AStarSolver(BaseSolver):
    """A* Search solver with admissible heuristic for Bloxorz.

    Supports basic boards as well as advanced mechanics (fragile tiles,
    bridges/switches, and split cubes via 'SPACE' cube switching).
    Uses the tuned UCS multi-objective cost model for path costs while
    preserving the admissible distance heuristic.
    """

    def __init__(self, board, cost_function: Optional[BaseCostFunction] = None):
        super().__init__(board)
        # Mặc định sử dụng hàm chi phí trọng số tối ưu từ UCS (TunedWeightCost)
        self.cost_function = cost_function or TunedWeightCost()
        self.total_cost = 0.0
        self.solution: Optional[List[str]] = None

    def manhattan_dist(self, r: int, c: int) -> float:
        return float(abs(r - self.board.goal_r) + abs(c - self.board.goal_c))

    def heuristic(self, state: BloxorzState) -> float:
        """Admissible and consistent heuristic estimating remaining distance to goal.

        - For whole blocks: min Manhattan distance of occupied cells to goal divided by 2
          (since a roll moves up to 2 cells), plus 0.5 penalty if not standing (at least
          one roll is required to stand up on the goal).
        - For split blocks: accounts for steps needed for cubes to become adjacent plus
          distance to goal.
        """
        if state.is_split():
            c0, c1 = state.cubes
            inter_dist = float(abs(c0[0] - c1[0]) + abs(c0[1] - c1[1]))
            d0 = self.manhattan_dist(c0[0], c0[1])
            d1 = self.manhattan_dist(c1[0], c1[1])
            return max(0.0, (inter_dist - 1.0) / 2.0) + min(d0, d1) / 2.0 + 1.0

        occupied = state.get_occupied_cells()
        min_d = min(self.manhattan_dist(r, c) for r, c in occupied) / 2.0
        if not state.is_standing():
            min_d += 0.5
        return min_d

    def calculate_step_cost(
        self,
        current_state: BloxorzState,
        action: str,
        next_state: BloxorzState,
        last_action: Optional[str] = None,
    ) -> float:
        """Tính chi phí bước đi sử dụng mô hình chi phí của UCS."""
        if isinstance(self.cost_function, BaseCostFunction) or hasattr(self.cost_function, 'calculate_cost'):
            try:
                return self.cost_function.calculate_cost(
                    current_state, action, next_state, self.board, last_action=last_action
                )
            except TypeError:
                return self.cost_function.calculate_cost(
                    current_state, action, next_state, self.board
                )
        if callable(self.cost_function):
            try:
                return self.cost_function(current_state, action, next_state, self.board)
            except TypeError:
                return self.cost_function(next_state)
        return 1.0

    def _search(self) -> Optional[List[str]]:
        initial_state = self.board.get_initial_state()
        self.total_cost = 0.0
        self.solution = None
        if self.board.is_goal(initial_state):
            self.solution = []
            return []

        use_last_action = getattr(self.cost_function, 'depends_on_last_action', False)
        start_node = (initial_state, None) if use_last_action else initial_state

        counter = count()
        g_score = {start_node: 0.0}
        h_init = self.heuristic(initial_state)

        # heap: (f_score, g_score, tie_breaker, node, path)
        pq = [(h_init, 0.0, next(counter), start_node, [])]

        while pq:
            f_curr, g_curr, _, current_node, current_path = heapq.heappop(pq)

            # Skip if a cheaper path to this node was already processed
            if g_curr > g_score.get(current_node, float('inf')):
                continue

            self.expanded_nodes += 1

            current_state = current_node[0] if use_last_action else current_node
            last_action = (
                current_node[1]
                if use_last_action
                else (current_path[-1] if (current_path and current_path[-1] in INVERSE_ACTIONS) else None)
            )

            if self.board.is_goal(current_state):
                self.total_cost = g_curr
                self.solution = current_path
                return current_path

            actions = self.board.get_actions(current_state) if hasattr(self.board, 'get_actions') else ACTIONS
            for action in actions:
                next_state = self.board.transition(current_state, action)
                if next_state is None:
                    continue

                c_n = self.calculate_step_cost(
                    current_state, action, next_state, last_action=last_action
                )
                new_g = g_curr + c_n

                next_last_action = action if action in INVERSE_ACTIONS else None
                next_node = (next_state, next_last_action) if use_last_action else next_state

                if new_g < g_score.get(next_node, float('inf')):
                    g_score[next_node] = new_g
                    f_next = new_g + self.heuristic(next_state)
                    heapq.heappush(pq, (f_next, new_g, next(counter), next_node, current_path + [action]))

        self.total_cost = float('inf')
        self.solution = None
        return None
