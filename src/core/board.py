import json
from typing import List, Tuple, Optional
from src.core.state import BloxorzState, Orientation

# Định nghĩa các hành động
ACTIONS = ['U', 'D', 'L', 'R']

class Board:
    def __init__(self, filepath: str):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.grid = data['grid']
        self.rows = len(self.grid)
        self.cols = len(self.grid[0])
        self.start_r, self.start_c = data['start']
        self.goal_r, self.goal_c = data['goal']

    def get_initial_state(self) -> BloxorzState:
        return BloxorzState(self.start_r, self.start_c, Orientation.STANDING)

    def is_goal(self, state: BloxorzState) -> bool:
        """Đích chỉ được chấp nhận khi khối đứng thẳng trên ô Goal."""
        return state.is_standing() and state.r == self.goal_r and state.c == self.goal_c

    def is_valid_cell(self, r: int, c: int) -> bool:
        """Kiểm tra ô nằm trong sàn và không rơi vào vực (0: void)."""
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return self.grid[r][c] != 0
        return False

    def is_valid_state(self, state: BloxorzState) -> bool:
        cells = state.get_occupied_cells()
        for r, c in cells:
            if not self.is_valid_cell(r, c):
                return False
        # (Chỗ này TV1 có thể bổ sung kiểm tra ô cam Fragile tiles sau)
        return True

    def transition(self, state: BloxorzState, action: str) -> Optional[BloxorzState]:
        """Bảng xoay lật trạng thái chuẩn của Bloxorz."""
        r, c, o = state.r, state.c, state.orientation
        new_r, new_c, new_o = r, c, o

        if o == Orientation.STANDING:
            if action == 'U':   new_r, new_c, new_o = r - 2, c, Orientation.VERTICAL
            elif action == 'D': new_r, new_c, new_o = r + 1, c, Orientation.VERTICAL
            elif action == 'L': new_r, new_c, new_o = r, c - 2, Orientation.HORIZONTAL
            elif action == 'R': new_r, new_c, new_o = r, c + 1, Orientation.HORIZONTAL

        elif o == Orientation.HORIZONTAL:
            if action == 'U':   new_r, new_c, new_o = r - 1, c, Orientation.HORIZONTAL
            elif action == 'D': new_r, new_c, new_o = r + 1, c, Orientation.HORIZONTAL
            elif action == 'L': new_r, new_c, new_o = r, c - 1, Orientation.STANDING
            elif action == 'R': new_r, new_c, new_o = r, c + 2, Orientation.STANDING

        elif o == Orientation.VERTICAL:
            if action == 'U':   new_r, new_c, new_o = r - 1, c, Orientation.STANDING
            elif action == 'D': new_r, new_c, new_o = r + 2, c, Orientation.STANDING
            elif action == 'L': new_r, new_c, new_o = r, c - 1, Orientation.VERTICAL
            elif action == 'R': new_r, new_c, new_o = r, c + 1, Orientation.VERTICAL

        next_state = BloxorzState(new_r, new_c, new_o, state.bridges_state)
        return next_state if self.is_valid_state(next_state) else None