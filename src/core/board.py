import json
from typing import Optional
from src.core.state import BloxorzState, Orientation

# Định nghĩa các hành động
ACTIONS = ['U', 'D', 'L', 'R']

class Board:
    def __init__(self, filepath: str):
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid level JSON in {filepath}: {exc.msg} "
                    f"(line {exc.lineno}, column {exc.colno})."
                ) from exc
        if not isinstance(data, dict):
            raise ValueError("Level must be a JSON object with grid, start and goal.")
        for key in ('grid', 'start', 'goal'):
            if key not in data:
                raise ValueError(f"Level is missing required field '{key}'.")

        grid = data['grid']
        if not isinstance(grid, list) or not grid:
            raise ValueError("Level grid must be a non-empty list of rows.")
        if not isinstance(grid[0], list) or not grid[0]:
            raise ValueError("Level grid rows must be non-empty lists.")
        cols = len(grid[0])
        for row in grid:
            if not isinstance(row, list) or len(row) != cols:
                raise ValueError("Level grid must be rectangular with non-empty rows.")
            if any(type(cell) is not int for cell in row):
                raise ValueError("Level grid cells must be integer tile codes (not booleans).")

        self.grid = data['grid']
        self.rows = len(self.grid)
        self.cols = len(self.grid[0])
        for key in ('start', 'goal'):
            position = data[key]
            if (not isinstance(position, list) or len(position) != 2
                    or any(type(coord) is not int for coord in position)):
                raise ValueError(f"Level {key} must be [row, col] with two integers.")
            r, c = position
            if not (0 <= r < self.rows and 0 <= c < self.cols):
                raise ValueError(f"Level {key} {position} lies outside the grid.")
            if self.grid[r][c] == 0:
                raise ValueError(f"Level {key} {position} must not be on a void tile.")

        self.start_r, self.start_c = data['start']
        self.goal_r, self.goal_c = data['goal']

    def get_initial_state(self) -> BloxorzState:
        return BloxorzState(self.start_r, self.start_c, Orientation.STANDING)

    def is_goal(self, state: BloxorzState) -> bool:
        """Đích chỉ được chấp nhận khi khối đứng thẳng trên ô Goal."""
        return state.is_standing() and state.r == self.goal_r and state.c == self.goal_c

    def is_valid_cell(self, r: int, c: int) -> bool:
        """Kiểm tra ô nằm trong sàn và không rơi vào vực (0: void)."""
        if type(r) is not int or type(c) is not int:
            raise TypeError("Cell coordinates r and c must be integers (not booleans).")
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
        """Return a new valid state or None; unsupported actions raise ValueError.

        The source must be a valid BloxorzState on this board and is never mutated.
        """
        if action not in ACTIONS:
            raise ValueError(f"Unsupported action {action!r}; expected one of {ACTIONS}.")
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
