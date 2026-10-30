from abc import ABC, abstractmethod
from math import isfinite
from typing import Optional, Tuple
from src.core.state import BloxorzState, Orientation
from src.core.board import Board

INVERSE_ACTIONS = {'U': 'D', 'D': 'U', 'L': 'R', 'R': 'L'}
CONTROL_ACTIONS = {'SPACE', 'SWITCH'}


def near_void_cell(board: Board, state: BloxorzState, cell: Tuple[int, int]) -> bool:
    """Kiểm tra ô có sát bờ vực hoặc ô ngoài biên (>= 2 hướng kề không đi được)."""
    r, c = cell
    unavailable = 0
    bridges = getattr(state, 'bridges_state', None)
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if hasattr(board, 'is_valid_cell'):
            if not board.is_valid_cell(nr, nc, bridges):
                unavailable += 1
        else:
            if not (0 <= nr < board.rows and 0 <= nc < board.cols) or board.grid[nr][nc] in (0, '0'):
                unavailable += 1
    return unavailable >= 2


class BaseCostFunction(ABC):
    depends_on_last_action: bool = False

    @abstractmethod
    def calculate_cost(
        self,
        state: BloxorzState,
        action: str,
        next_state: BloxorzState,
        board: Board,
        last_action: Optional[str] = None,
    ) -> float:
        """Tính chi phí bước đi từ state sang next_state."""
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        """Tên của mô hình chi phí để in báo cáo."""
        raise NotImplementedError

    @staticmethod
    def _validate_cost(cost: float) -> float:
        value = float(cost)
        if not isfinite(value) or value < 0:
            raise ValueError(
                f"UCS yêu cầu trọng số dương hữu hạn, {cost!r}"
            )
        return value


class UniformCost(BaseCostFunction):
    # Mô hình 1: Chi phí đồng nhất c = 1 (UCS thoái hóa thành BFS)
    @property
    def name(self) -> str:
        return "Uniform (c = 1.0)"

    def calculate_cost(
        self,
        state: BloxorzState,
        action: str,
        next_state: BloxorzState,
        board: Board,
        last_action: Optional[str] = None,
    ) -> float:
        return 1.0


class PhysicsBasedCost(BaseCostFunction):
    # Mô hình 2: Chi phí cơ học trọng trường khi nâng hạ trọng tâm khối
    def __init__(self, base_cost: float = 1.0, stand_up_penalty: float = 0.5):
        if base_cost <= 0 or stand_up_penalty < 0:
            raise ValueError("Base_cost phải > 0 và stand_up_penalty >= 0")
        self.base_cost = float(base_cost)
        self.stand_up_penalty = float(stand_up_penalty)

    @property
    def name(self) -> str:
        return "Physics-based (Gravity Lift)"

    def calculate_cost(
        self,
        state: BloxorzState,
        action: str,
        next_state: BloxorzState,
        board: Board,
        last_action: Optional[str] = None,
    ) -> float:
        # Lăn từ Nằm (HORIZONTAL hoặc VERTICAL) sang Đứng (STANDING) -> Tốn công nâng trọng tâm
        cost = self.base_cost
        if not state.is_standing() and next_state.is_standing():
            cost += self.stand_up_penalty     # Cộng thêm chi phí khi lật đứng

        # Lăn từ Đứng sang Nằm hoặc Nằm trượt: Chi phí tiêu chuẩn
        return self._validate_cost(cost)


class RiskSafetyCost(BaseCostFunction):
    # Mô hình 3: Đánh giá an toàn địa hình (Tránh mép vực và ô nguy hiểm)
    def __init__(self, base_cost: float = 1.0, fragile_penalty: float = 2.0, edge_penalty: float = 0.25):
        if base_cost <= 0 or fragile_penalty < 0 or edge_penalty < 0:
            raise ValueError("base_cost cần > 0, hai tham số penalty >= 0")
        self.base_cost = float(base_cost)
        self.fragile_penalty = float(fragile_penalty)
        self.edge_penalty = float(edge_penalty)

    @property
    def name(self) -> str:
        return "Risk-Safety (Terrain-aware)"

    def calculate_cost(
        self,
        state: BloxorzState,
        action: str,
        next_state: BloxorzState,
        board: Board,
        last_action: Optional[str] = None,
    ) -> float:
        cost = self.base_cost
        occupied_cells = set(next_state.get_occupied_cells())

        for r, c in occupied_cells:
            # Kiểm tra ô dễ vỡ (Fragile tile)
            is_fragile = (board.grid[r][c] in (3, '3')) or (
                hasattr(board, 'is_fragile_tile') and board.is_fragile_tile(r, c)
            )
            if is_fragile:
                cost += self.fragile_penalty  # Phạt nặng do rủi ro gãy vỡ sàn

            # Kiểm tra có nằm sát bờ vực (ô void = 0 hoặc nằm ngoài biên)
            is_near_void = False
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if not (0 <= nr < board.rows and 0 <= nc < board.cols) or board.grid[nr][nc] in (0, '0'):
                    is_near_void = True
                    break

            if is_near_void:
                cost += self.edge_penalty  # Phạt nhẹ khi đi sát bờ vực hiểm trở

        return self._validate_cost(cost)


class TunedWeightCost(BaseCostFunction):
    """Mô hình trọng số tối ưu từ thực nghiệm Grid Search & Cross-Validation.

    Trọng số chuẩn hóa đã tìm được:
      - w_step: 1.0 (chi phí bước lăn U/D/L/R; thao tác đổi khối SPACE/SWITCH có chi phí 0.0)
      - w_backtrack: 3.0 (phạt bước đi lập tức đảo chiều bước trước đó)
      - w_void: 2.0 (phạt trạng thái có ô tiếp xúc >= 2 ô vực/ngoài sàn)
      - w_fragile: 4.0 (phạt mỗi ô mong manh mới đi vào)
      - w_switch_change: 2.5 (phạt mỗi cờ cầu bị đảo trạng thái do công tắc)
      - w_bridge_entry: 3.0 (phạt mỗi ô cầu mới đi vào)
    """

    depends_on_last_action: bool = True

    def __init__(
        self,
        w_step: float = 1.0,
        w_backtrack: float = 3.0,
        w_void: float = 2.0,
        w_fragile: float = 4.0,
        w_switch_change: float = 2.5,
        w_bridge_entry: float = 3.0,
    ):
        if w_step <= 0 or any(w < 0 for w in (w_backtrack, w_void, w_fragile, w_switch_change, w_bridge_entry)):
            raise ValueError("w_step phải > 0 và các trọng số phạt phải >= 0")

        self.w_step = float(w_step)
        self.w_backtrack = float(w_backtrack)
        self.w_void = float(w_void)
        self.w_fragile = float(w_fragile)
        self.w_switch_change = float(w_switch_change)
        self.w_bridge_entry = float(w_bridge_entry)

    @property
    def name(self) -> str:
        return (
            f"TunedWeighted(step={self.w_step:g}, back={self.w_backtrack:g}, "
            f"void={self.w_void:g}, frag={self.w_fragile:g}, "
            f"sw={self.w_switch_change:g}, br={self.w_bridge_entry:g})"
        )

    def calculate_cost(
        self,
        state: BloxorzState,
        action: str,
        next_state: BloxorzState,
        board: Board,
        last_action: Optional[str] = None,
    ) -> float:
        is_roll = action in INVERSE_ACTIONS
        if not is_roll:
            # Lệnh đổi khối điều khiển: là bước chuyển trạng thái tìm kiếm nhưng không tính phí lăn
            return 0.0

        cost = self.w_step

        # 1. Backtrack penalty: bước lăn đảo chiều ngay lập tức bước trước đó
        if (
            self.w_backtrack > 0
            and last_action in INVERSE_ACTIONS
            and INVERSE_ACTIONS[last_action] == action
        ):
            cost += self.w_backtrack

        next_cells = set(next_state.get_occupied_cells())
        curr_cells = set(state.get_occupied_cells())
        newly_occupied = next_cells - curr_cells

        # 2. Void exposure penalty: kết thúc tại vị trí có ô kề >= 2 ô vực/ngoài biên
        if self.w_void > 0:
            if any(near_void_cell(board, next_state, cell) for cell in next_cells):
                cost += self.w_void

        # 3. Fragile tile penalty: phạt mỗi ô mong manh mới đi vào
        if self.w_fragile > 0:
            fragile_count = 0
            for r, c in newly_occupied:
                if (hasattr(board, 'is_fragile_tile') and board.is_fragile_tile(r, c)) or board.grid[r][c] in (3, '3'):
                    fragile_count += 1
            cost += self.w_fragile * fragile_count

        # 4. Switch changes penalty: phạt mỗi cờ cầu bị lật trạng thái
        if self.w_switch_change > 0:
            before = getattr(state, 'bridges_state', ()) or ()
            after = getattr(next_state, 'bridges_state', ()) or ()
            maxn = max(len(before), len(after))
            switch_changes = sum(
                1 for i in range(maxn)
                if (before[i] if i < len(before) else False) != (after[i] if i < len(after) else False)
            )
            cost += self.w_switch_change * switch_changes

        # 5. Bridge entries penalty: phạt mỗi ô cầu mới đi vào
        if self.w_bridge_entry > 0:
            bridge_count = 0
            for r, c in newly_occupied:
                if hasattr(board, 'is_bridge_tile') and board.is_bridge_tile(r, c):
                    bridge_count += 1
            cost += self.w_bridge_entry * bridge_count

        return self._validate_cost(cost)


class LearnedWeightCost(TunedWeightCost):
    """Mô hình bộ trọng số tuyến tính (tương thích ngược với các tham số cũ và mặc định dùng trọng số tối ưu)."""

    def __init__(
        self,
        w_step: float = 1.0,
        w_backtrack: float = 3.0,
        w_void: float = 2.0,
        w_fragile: float = 4.0,
        w_switch_change: float = 2.5,
        w_bridge_entry: float = 3.0,
        *,
        w_tilt: Optional[float] = None,
        w_risk: Optional[float] = None,
        **kwargs,
    ):
        if w_risk is not None and w_fragile == 4.0:
            w_fragile = float(w_risk)
        super().__init__(
            w_step=w_step,
            w_backtrack=w_backtrack,
            w_void=w_void,
            w_fragile=w_fragile,
            w_switch_change=w_switch_change,
            w_bridge_entry=w_bridge_entry,
        )
        self.w_tilt = float(w_tilt) if w_tilt is not None else 0.0
        self.w_risk = self.w_fragile

    @property
    def name(self) -> str:
        if self.w_tilt > 0:
            return (
                f"LearnedWeighted(step={self.w_step:g}, tilt={self.w_tilt:g}, "
                f"frag={self.w_fragile:g}, void={self.w_void:g})"
            )
        return super().name

    def calculate_cost(
        self,
        state: BloxorzState,
        action: str,
        next_state: BloxorzState,
        board: Board,
        last_action: Optional[str] = None,
    ) -> float:
        cost = super().calculate_cost(state, action, next_state, board, last_action=last_action)
        if self.w_tilt > 0 and not state.is_standing() and next_state.is_standing():
            cost += self.w_tilt
        return self._validate_cost(cost)
