from __future__ import annotations

import heapq
from itertools import count 
from typing import List, Optional, Sequence, Tuple

from src.core.board import ACTIONS
from src.core.state import BloxorzState

from src.solvers.base_solver import BaseSolver
from src.solvers.UCS_Algorithm.cost_functions import BaseCostFunction, PhysicsBasedCost, RiskSafetyCost, UniformCost


class UCSSolver(BaseSolver):
    def __init__(self, board, cost_function: Optional[BaseCostFunction] = None):
        super().__init__(board)
        # Mặc định dùng hàm chi phí vật lý
        self.cost_function = cost_function or PhysicsBasedCost()
        self.total_cost = 0.0 # Tổng chi phí từ trạng thái bắt đầu đến trạng thái hiện tại
        self.solution: Optional[List[str]] = None
        self.solution_state: List[BloxorzState] = []
        self.solution_costs: List[float] = []

    @property
    def solution_states(self) -> List[BloxorzState]:
        return self.solution_state

    def _search(self) -> Optional[List[str]]:
        start = self.board.get_initial_state()
        self.total_cost = 0.0
        self.solution = None
        self.solution_state = [start]
        self.solution_costs = [0.0]

        # Priority Queue lưu tuple (g_score, insertion_order, current_state)
        sequence = count()

        frontier: List[Tuple[float, int, BloxorzState]] = [(0.0, next(sequence), start)]

        # best_g lưu chi phí đường đi nhỏ nhất từng biết để tới được state
        best_g = {start: 0.0}
        parent = {}    # state --> (previous_state, action)

        while frontier:
            # 1. Lấy trạng thái có chi phí tích lũy g nhỏ nhất
            current_g, _, current_state = heapq.heappop(frontier)

            # 2. Bỏ qua nếu thấy đường khác tốt hơn tới current_state
            if current_g > best_g.get(current_state, float('inf')):
                continue

            self.expanded_nodes += 1

            # 3. Kiểm tra nếu đã tới trạng thái đích
            if self.board.is_goal(current_state):
                actions = []
                states = [current_state]
                cursor = current_state
                while cursor != start:
                    previous, action = parent[cursor]
                    actions.append(action)
                    cursor = previous
                    states.append(cursor)

                actions.reverse()
                states.reverse()

                self.total_cost = current_g
                self.solution = list(actions)
                self.solution_state = states
                self.solution_costs = self._calculate_path_costs(states, actions)

                return actions

            # 4. Duyệt các nhánh kế tiếp
            actions = self.board.get_actions(current_state) if hasattr(self.board, 'get_actions') else ACTIONS
            for action in actions:
                successor = self.board.transition(current_state, action)
                if successor is None:
                    continue

                step_cost = self.cost_function.calculate_cost(
                    current_state, action, successor, self.board
                )
                step_cost = BaseCostFunction._validate_cost(step_cost)

                new_g = current_g + step_cost
            
                if new_g < best_g.get(successor, float("inf")):
                    best_g[successor] = new_g
                    parent[successor] = (current_state, action)

                    heapq.heappush(frontier, (new_g, next(sequence), successor))

        self.total_cost = float("inf")
        self.solution = None
        self.solution_state = []
        self.solution_costs = []
        # Nếu không tìm thấy đường đi
        return None

    def _calculate_path_costs(
        self, states: Sequence[BloxorzState], actions: Sequence[str]
    ) -> List[float]:
        cumulative = [0.0]
        total = 0.0
        for i, action in enumerate(actions):
            total += self.cost_function.calculate_cost(
                states[i], action, states[i + 1], self.board
            )
            cumulative.append(total)

        return cumulative

    def get_solution_states(
        self, solution: Optional[Sequence[str]] = None
    ) -> List[BloxorzState]:
        # Reconstruct states dựa trên action path
        if solution is None and self.solution_state:
            return list(self.solution_state)

        actions = list(solution or [])
        states = [self.board.get_initial_state()]
        current = states[0]

        for action in actions:
            current = self.board.transition(current, action)
            if current is None:
                raise ValueError(
                    f"[INVALID SOLUTION]: hành động {action!r} dẫn tới trạng thái không hợp lệ"
                )
            states.append(current)

        return states


def reconstruct_path(parent, start, goal) -> List[str]:
    actions = []
    current = goal
    while current != start:
        if current not in parent:
            return []

        previous, action = parent[current]
        actions.append(action)
        current = previous

    actions.reverse()
    return actions

def _state_label(state: BloxorzState) -> str:
    if state.is_split():
        return f"SPLIT(cubes={state.cubes}, active={state.active_cube})"
    return f"({state.r}, {state.c}, {state.orientation.name})"

def visualize_ucs_solution(
    board, 
    solution: Optional[Sequence[str]],
    cost_function: Optional[BaseCostFunction] = None,
) -> None:
    
    if solution is None:
        print("[UCS] Không tìm thấy đường đi tới đích")
        return 

    model = cost_function or PhysicsBasedCost()
    actions = list(solution)
    states = [board.get_initial_state()]
    current = states[0]
    cumulative = [0.0]

    for action in actions:
        nxt = board.transition(current, action)
        if nxt is None:
            raise ValueError(
                f"Đường đi không hợp lệ: Hành động {action!r} tại {_state_label(current)}"
            )

        step_cost = BaseCostFunction._validate_cost(
            model.calculate_cost(current, action, nxt, board)
        )

        cumulative.append(cumulative[-1] + step_cost)
        states.append(nxt)
        current = nxt

    print(f"\n[UCS VISUALISATION]: Cost model = {model.name}")
    print(f"Actions: {' -> '.join(actions) if actions else '(đã ở đích)'}")
    print(f"Số bước: {len(actions)} | Tổng chi phí: {cumulative[-1]:.2f}")

    for i, state in enumerate(states):
        occupied = set(state.get_occupied_cells())
        print(
            f"\nBước {i}: state={_state_label(state)}"
            + (f" | action={actions[i - 1]}" if i > 0 else " | START")
            + f" | g={cumulative[i]:.2f}"
        )

        for r in range(board.rows):
            row = []
            for c in range(board.cols):
                if (r, c) in occupied:
                    row.append(" B ")
                elif r == board.goal_r and c == board.goal_c:
                    row.append(" G ")
                elif board.grid[r][c] == 0:
                    row.append(" · ")
                elif board.grid[r][c] == 3:
                    row.append(" F ")
                else:
                    row.append(" . ")
            print("".join(row))

    print("\nKý hiệu: B = khối, G = đích, F = ô dễ vỡ, · = vực, . = sàn.")
