from enum import Enum
from typing import Tuple, FrozenSet

class Orientation(Enum):
    STANDING = 0     # Chiếm 1 ô (r, c)
    HORIZONTAL = 1   # Nằm ngang: (r, c) và (r, c + 1)
    VERTICAL = 2     # Nằm dọc: (r, c) và (r + 1, c)

class BloxorzState:
    def __init__(self, r: int, c: int, orientation: Orientation, bridges_state: Tuple[bool, ...] = ()):
        self.r = r
        self.c = c
        self.orientation = orientation
        # bridges_state lưu trạng thái đóng/mở của các cầu (hỗ trợ nâng cao sau này)
        self.bridges_state = bridges_state

    def get_occupied_cells(self):
        """Trả về danh sách các ô (r, c) mà khối đang chiếm giữ."""
        if self.orientation == Orientation.STANDING:
            return [(self.r, self.c)]
        elif self.orientation == Orientation.HORIZONTAL:
            return [(self.r, self.c), (self.r, self.c + 1)]
        elif self.orientation == Orientation.VERTICAL:
            return [(self.r, self.c), (self.r + 1, self.c)]

    def is_standing(self) -> bool:
        return self.orientation == Orientation.STANDING

    def __hash__(self):
        return hash((self.r, self.c, self.orientation, self.bridges_state))

    def __eq__(self, other):
        if not isinstance(other, BloxorzState):
            return False
        return (self.r, self.c, self.orientation, self.bridges_state) == \
               (other.r, other.c, other.orientation, other.bridges_state)
    def __lt__(self, other):
        return False
    def __repr__(self):
        return f"State({self.r}, {self.c}, {self.orientation.name})"