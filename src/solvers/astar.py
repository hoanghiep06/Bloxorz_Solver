import heapq
from itertools import count
from typing import List, Optional
from src.solvers.base_solver import BaseSolver
from src.core.board import ACTIONS
from src.core.state import BloxorzState

class AStarSolver(BaseSolver):
    """A* Search solver with admissible heuristic for Bloxorz.

    Supports basic boards as well as advanced mechanics (fragile tiles,
    bridges/switches, and split cubes via 'SPACE' cube switching).
    """

    def manhattan_dist(self, r: int, c: int) -> float:
        return float(abs(r - self.board.goal_r) + abs(c - self.board.goal_c))

    def heuristic(self, state: BloxorzState) -> float:
        """Estimate remaining unit-cost rolls without overestimating.

        Without split switches, use the existing relaxed Manhattan bound and
        orientation penalty. Split switches can teleport cubes arbitrarily far,
        invalidating spatial bounds even BEFORE the block reaches the switch.
        Use h=0 for every state on such boards (Dijkstra ordering), and for any
        supplied split state. This preserves optimality with nonnegative costs
        at the expense of expanding more states on split boards.
        """
        if state.is_split() or getattr(self.board, 'split_switches', None):
            return 0.0

        occupied = state.get_occupied_cells()
        min_d = min(self.manhattan_dist(r, c) for r, c in occupied) / 2.0
        if not state.is_standing():
            min_d += 0.5
        return min_d

    def cost_function(self, state: BloxorzState) -> float:
        """Step cost function; defaults to 1.0."""
        return 1.0

    def _search(self) -> Optional[List[str]]:
        initial_state = self.board.get_initial_state()
        if self.board.is_goal(initial_state):
            return []

        counter = count()
        g_score = {initial_state: 0.0}
        h_init = self.heuristic(initial_state)

        # heap: (f_score, g_score, tie_breaker, state, path)
        pq = [(h_init, 0.0, next(counter), initial_state, [])]

        while pq:
            f_curr, g_curr, _, current_state, current_path = heapq.heappop(pq)

            # Skip if a cheaper path to this state was already processed
            if g_curr > g_score.get(current_state, float('inf')):
                continue

            self.expanded_nodes += 1

            if self.board.is_goal(current_state):
                return current_path

            actions = self.board.get_actions(current_state) if hasattr(self.board, 'get_actions') else ACTIONS
            for action in actions:
                next_state = self.board.transition(current_state, action)
                if next_state is None:
                    continue

                c_n = self.cost_function(next_state)
                new_g = g_curr + c_n

                if new_g < g_score.get(next_state, float('inf')):
                    g_score[next_state] = new_g
                    f_next = new_g + self.heuristic(next_state)
                    heapq.heappush(pq, (f_next, new_g, next(counter), next_state, current_path + [action]))

        return None
