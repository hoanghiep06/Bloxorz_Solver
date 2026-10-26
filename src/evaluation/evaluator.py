"""
Module TrajectoryEvaluator: Barem danh gia chat luong duong di Bloxorz.
Cung cap he quy chieu da tieu chi (Multi-criteria Scoring) cham diem cac loi giai tu 0 den 100.
"""

from typing import List, Dict, Any, Optional
from src.core.board import Board
from src.core.state import BloxorzState, Orientation

OPPOSITE_MOVES = {
    'U': 'D',
    'D': 'U',
    'L': 'R',
    'R': 'L'
}

class TrajectoryReport:
    def __init__(
        self,
        actions: List[str],
        success: bool,
        steps: int,
        backtracks: int,
        void_exposure: int,
        fragile_hesitations: int,
        switch_inefficiencies: int,
        bridge_crossings: int,
        penalty_cost: float,
        score: float,
        rating: str
    ):
        self.actions = actions
        self.success = success
        self.steps = steps
        self.backtracks = backtracks
        self.void_exposure = void_exposure
        self.fragile_hesitations = fragile_hesitations
        self.switch_inefficiencies = switch_inefficiencies
        self.bridge_crossings = bridge_crossings
        self.penalty_cost = penalty_cost
        self.score = score
        self.rating = rating

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actions": self.actions,
            "success": self.success,
            "steps": self.steps,
            "backtracks": self.backtracks,
            "void_exposure": self.void_exposure,
            "fragile_hesitations": self.fragile_hesitations,
            "switch_inefficiencies": self.switch_inefficiencies,
            "bridge_crossings": self.bridge_crossings,
            "penalty_cost": round(self.penalty_cost, 2),
            "score": round(self.score, 1),
            "rating": self.rating
        }


class TrajectoryEvaluator:
    def __init__(
        self,
        w_step: float = 1.0,
        w_backtrack: float = 3.0,
        w_void: float = 2.0,
        w_switch: float = 2.5,
        w_fragile: float = 4.0,
        w_bridge: float = 3.0,
        scale_k: float = 2.5
    ):
        self.w_step = w_step
        self.w_backtrack = w_backtrack
        self.w_void = w_void
        self.w_switch = w_switch
        self.w_fragile = w_fragile
        self.w_bridge = w_bridge
        self.scale_k = scale_k

    def _is_near_void(self, board: Board, r: int, c: int) -> bool:
        void_count = 0
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < board.rows and 0 <= nc < board.cols) or board.grid[nr][nc] == 0:
                void_count += 1
        return void_count >= 2

    def evaluate(
        self,
        board: Board,
        actions: List[str],
        optimal_penalty: Optional[float] = None,
        level_data: Optional[Dict[str, Any]] = None
    ) -> TrajectoryReport:
        if not actions:
            return TrajectoryReport(
                actions=[], success=False, steps=0, backtracks=0,
                void_exposure=0, fragile_hesitations=0, switch_inefficiencies=0,
                bridge_crossings=0, penalty_cost=999.0, score=0.0, rating="That bai (Rong)"
            )

        # 1. Dem buoc di
        steps = len(actions)

        # 2. Dem so lan di lui / quay xe
        backtracks = 0
        for i in range(len(actions) - 1):
            if actions[i + 1] == OPPOSITE_MOVES.get(actions[i]):
                backtracks += 1

        # 3. Mo phong duong di tren Board de tinh cac chi so vat ly
        state = board.get_initial_state()
        void_exposure = 0
        fragile_hesitations = 0
        switch_activations = {}
        switch_misses = 0
        bridge_traversals = {}
        visited_states = set()
        success = False

        # Doc thong tin switch & bridge tu JSON neu co
        switches = []
        bridges = []
        if level_data:
            switches = level_data.get('switches', [])
            bridges = level_data.get('bridges', [])

        for idx, act in enumerate(actions):
            next_state = board.transition(state, act)
            if next_state is None:
                # Roi xuong vuc
                return TrajectoryReport(
                    actions=actions, success=False, steps=steps, backtracks=backtracks,
                    void_exposure=void_exposure, fragile_hesitations=fragile_hesitations,
                    switch_inefficiencies=switch_misses, bridge_crossings=0,
                    penalty_cost=999.0, score=0.0, rating="Roi vuc (Invalid)"
                )

            occupied = next_state.get_occupied_cells()

            # Kiem tra mep vuc
            for cr, cc in occupied:
                if self._is_near_void(board, cr, cc):
                    void_exposure += 1
                    break

            # Kiem tra o cam fragile
            for cr, cc in occupied:
                if board.grid[cr][cc] == 3:
                    if next_state.is_standing():
                        # Sap san!
                        return TrajectoryReport(
                            actions=actions, success=False, steps=steps, backtracks=backtracks,
                            void_exposure=void_exposure, fragile_hesitations=fragile_hesitations + 1,
                            switch_inefficiencies=switch_misses, bridge_crossings=0,
                            penalty_cost=999.0, score=0.0, rating="Sap o cam (Death)"
                        )

            # Kiem tra do du truoc o cam: neu lui xe khi dung sat o cam
            for cr, cc in occupied:
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    adj_r, adj_c = cr + dr, cc + dc
                    if 0 <= adj_r < board.rows and 0 <= adj_c < board.cols and board.grid[adj_r][adj_c] == 3:
                        if idx < len(actions) - 1 and actions[idx + 1] == OPPOSITE_MOVES.get(act):
                            fragile_hesitations += 1

            # Kiem tra switch
            for sw in switches:
                sw_pos = (sw['r'], sw['c'])
                if sw_pos in occupied:
                    sw_id = sw['id']
                    sw_type = sw.get('type', 'soft')
                    if sw_type == 'heavy' and not next_state.is_standing():
                        switch_misses += 1  # Cham nut chu X o the nam -> Miss!
                    else:
                        switch_activations[sw_id] = switch_activations.get(sw_id, 0) + 1

            # Kiem tra bridge
            for br in bridges:
                br_id = br['id']
                br_cells = set(tuple(c) for c in br['cells'])
                if any(cell in br_cells for cell in occupied):
                    bridge_traversals[br_id] = bridge_traversals.get(br_id, 0) + 1

            state = next_state

        if board.is_goal(state):
            success = True

        # Tinh loi thao tac switch va cau
        redundant_switches = sum(max(0, count - 1) for count in switch_activations.values())
        total_switch_errors = redundant_switches + switch_misses

        redundant_bridges = sum(max(0, count - 2) for count in bridge_traversals.values())

        # Tinh Penalty Cost
        penalty = (
            self.w_step * steps
            + self.w_backtrack * backtracks
            + self.w_void * void_exposure
            + self.w_switch * total_switch_errors
            + self.w_fragile * fragile_hesitations
            + self.w_bridge * redundant_bridges
        )

        if not success:
            penalty += 100.0
            score = 0.0
            rating = "That bai (Chua ve dich)"
        else:
            # Quy doi ve thang diem 100
            if optimal_penalty is None or optimal_penalty <= 0:
                optimal_penalty = penalty

            score = max(0.0, min(100.0, 100.0 - (penalty - optimal_penalty) * self.scale_k))

            # Xep loai
            if score >= 95:
                rating = "Xuat sac (Toi uu)"
            elif score >= 80:
                rating = "Tot (An toan)"
            elif score >= 65:
                rating = "Kha (Trung binh kha)"
            elif score >= 45:
                rating = "Trung binh (Co loi thua)"
            elif score >= 20:
                rating = "Kem (Long vong)"
            else:
                rating = "Rat kem (Di lac)"

        return TrajectoryReport(
            actions=actions,
            success=success,
            steps=steps,
            backtracks=backtracks,
            void_exposure=void_exposure,
            fragile_hesitations=fragile_hesitations,
            switch_inefficiencies=total_switch_errors,
            bridge_crossings=redundant_bridges,
            penalty_cost=penalty,
            score=score,
            rating=rating
        )
