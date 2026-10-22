from abc import ABC, abstractmethod
from math import isfinite
from src.core.state import BloxorzState, Orientation
from src.core.board import Board

class BaseCostFunction(ABC):
    @abstractmethod
    def calculate_cost(self, state: BloxorzState, action: str, next_state: BloxorzState, board: Board) -> float:
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

    def calculate_cost(self, state: BloxorzState, action: str, next_state: BloxorzState, board: Board) -> float:
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

    def calculate_cost(self, state: BloxorzState, action: str, next_state: BloxorzState, board: Board) -> float:
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

    def calculate_cost(self, state: BloxorzState, action: str, next_state: BloxorzState, board: Board) -> float:
        cost = self.base_cost
        occupied_cells = set(next_state.get_occupied_cells())

        for r, c in occupied_cells:
            # Kiểm tra ô dễ vỡ (Fragile tile - giá trị 3 dạng int hoặc '3' dạng str)
            if board.grid[r][c] in (3, '3'):
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
    


class LearnedWeightCost(BaseCostFunction):
    # Mô hình 4: Bộ trọng số tuyến tính
    def __init__(self, w_step: float = 1.0, w_tilt: float = 1.4, w_risk: float = 2.8):
        if w_step <= 0 or w_tilt < 0 or w_risk <0:
            raise ValueError("w_step > 0, w_tilt và w_risk >= 0")
        
        self.w_step = float(w_step)
        self.w_tilt = float(w_tilt)
        self.w_risk = float(w_risk)

    @property
    def name(self) -> str:
        return (
            f"Weighted (step={self.w_step:g}, tilt={self.w_tilt:g}, "
            f"fragile={self.w_risk:g})"
        )

    def calculate_cost(self, state: BloxorzState, action: str, next_state: BloxorzState, board: Board) -> float:
        cost = self.w_step
        if not state.is_standing() and next_state.is_standing():
            cost += self.w_tilt
        for r, c in next_state.get_occupied_cells():
            if board.grid[r][c] in (3, '3'):
                cost += self.w_risk
        return self._validate_cost(cost)