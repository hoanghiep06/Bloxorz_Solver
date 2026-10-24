from collections import deque
from typing import List, Optional
from src.solvers.base_solver import BaseSolver
from src.core.board import ACTIONS

class BFSSolver(BaseSolver):
    """FIFO graph search with unit action costs and first-discovery parents.

    Supports basic boards as well as advanced mechanics (fragile tiles,
    bridges/switches, and split cubes via 'SPACE' cube switching).
    """

    def _search(self) -> Optional[List[str]]:
        initial_state = self.board.get_initial_state()
        if self.board.is_goal(initial_state):
            return []

        # Only states enter the queue; each discovered state records one parent.
        queue = deque([initial_state])
        visited = {initial_state}
        parent = {}

        while queue:
            current_state = queue.popleft()
            self.expanded_nodes += 1

            if self.board.is_goal(current_state):
                path = []
                # The root has no parent. Each link leads to an earlier layer.
                while current_state != initial_state:
                    current_state, action = parent[current_state]
                    path.append(action)
                path.reverse()
                return path

            actions = self.board.get_actions(current_state) if hasattr(self.board, 'get_actions') else ACTIONS
            for action in actions:
                next_state = self.board.transition(current_state, action)
                if next_state is not None and next_state not in visited:
                    parent[next_state] = (current_state, action)
                    visited.add(next_state)
                    queue.append(next_state)

        return None
