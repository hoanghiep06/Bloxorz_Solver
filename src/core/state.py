from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

class Orientation(Enum):
    STANDING = 0     # Chiếm 1 ô (r, c)
    HORIZONTAL = 1   # Nằm ngang: (r, c) và (r, c + 1)
    VERTICAL = 2     # Nằm dọc: (r, c) và (r + 1, c)

@dataclass(frozen=True, eq=False, repr=False)
class BloxorzState:
    """Stable search key anchored at the top/left occupied cell.

    Bridge flags participate in identity; bridge effects are not implemented yet.
    Board validates support/bounds separately, so negative coordinates are allowed.
    """

    r: int
    c: int
    orientation: Orientation
    bridges_state: Tuple[bool, ...] = ()

    def __post_init__(self):
        if type(self.r) is not int or type(self.c) is not int:
            raise TypeError("State coordinates r and c must be integers (not booleans).")
        if not isinstance(self.orientation, Orientation):
            raise ValueError("State orientation must be an Orientation member.")
        if not isinstance(self.bridges_state, tuple) or any(
            type(flag) is not bool for flag in self.bridges_state
        ):
            raise TypeError("bridges_state must be a tuple of booleans.")

    def get_occupied_cells(self) -> List[Tuple[int, int]]:
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

    def __repr__(self):
        if self.bridges_state:
            return (f"State({self.r}, {self.c}, {self.orientation.name}, "
                    f"bridges_state={self.bridges_state})")
        return f"State({self.r}, {self.c}, {self.orientation.name})"
