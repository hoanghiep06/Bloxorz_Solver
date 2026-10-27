from dataclasses import dataclass
from enum import Enum
from inspect import Parameter, Signature
from typing import List, Optional, Tuple

class Orientation(Enum):
    STANDING = 0     # Chiếm 1 ô (r, c)
    HORIZONTAL = 1   # Nằm ngang: (r, c) và (r, c + 1)
    VERTICAL = 2     # Nằm dọc: (r, c) và (r + 1, c)

@dataclass(frozen=True, eq=False, repr=False)
class BloxorzState:
    """Stable search key anchored at the top/left occupied cell or split cubes.

    When whole (cubes is None):
        - r, c: anchor coordinate (int)
        - orientation: STANDING, HORIZONTAL, or VERTICAL
        - bridges_state: Tuple[bool, ...] indicating bridge passability
    When split (cubes is not None):
        - cubes: Tuple[Tuple[int, int], Tuple[int, int]] positions of both 1x1x1 cubes
        - active_cube: 0 or 1 index of the cube currently being controlled
        - bridges_state: Tuple[bool, ...]
    """

    r: int
    c: int
    orientation: Orientation
    bridges_state: Tuple[bool, ...] = ()
    cubes: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None
    active_cube: int = 0

    __signature__ = Signature([
        Parameter('r', Parameter.POSITIONAL_OR_KEYWORD),
        Parameter('c', Parameter.POSITIONAL_OR_KEYWORD),
        Parameter('orientation', Parameter.POSITIONAL_OR_KEYWORD),
        Parameter('bridges_state', Parameter.POSITIONAL_OR_KEYWORD, default=()),
    ])

    def __post_init__(self):
        if type(self.r) is not int or type(self.c) is not int:
            raise TypeError("State coordinates r and c must be integers (not booleans).")
        if not isinstance(self.orientation, Orientation):
            raise ValueError("State orientation must be an Orientation member.")
        if not isinstance(self.bridges_state, tuple) or any(
            type(flag) is not bool for flag in self.bridges_state
        ):
            raise TypeError("bridges_state must be a tuple of booleans.")
        if self.cubes is not None:
            if not isinstance(self.cubes, tuple) or len(self.cubes) != 2:
                raise TypeError("cubes must be a tuple of two coordinate pairs.")
            for pos in self.cubes:
                if not isinstance(pos, tuple) or len(pos) != 2 or type(pos[0]) is not int or type(pos[1]) is not int:
                    raise TypeError("cube coordinates must be tuples of two integers.")
            if self.active_cube not in (0, 1):
                raise ValueError("active_cube must be 0 or 1.")

    @classmethod
    def create_split(
        cls,
        cube0: Tuple[int, int],
        cube1: Tuple[int, int],
        active_cube: int = 0,
        bridges_state: Tuple[bool, ...] = ()
    ) -> 'BloxorzState':
        """Helper to create a split BloxorzState with two unit cubes."""
        return cls(
            r=cube0[0] if active_cube == 0 else cube1[0],
            c=cube0[1] if active_cube == 0 else cube1[1],
            orientation=Orientation.STANDING,
            bridges_state=bridges_state,
            cubes=(cube0, cube1),
            active_cube=active_cube
        )

    def is_split(self) -> bool:
        """Kiểm tra xem khối có đang bị tách thành 2 khối 1x1x1 không."""
        return self.cubes is not None

    def get_occupied_cells(self) -> List[Tuple[int, int]]:
        """Trả về danh sách các ô (r, c) mà khối đang chiếm giữ."""
        if self.cubes is not None:
            return list(self.cubes)
        if self.orientation == Orientation.STANDING:
            return [(self.r, self.c)]
        elif self.orientation == Orientation.HORIZONTAL:
            return [(self.r, self.c), (self.r, self.c + 1)]
        elif self.orientation == Orientation.VERTICAL:
            return [(self.r, self.c), (self.r + 1, self.c)]

    def is_standing(self) -> bool:
        if self.cubes is not None:
            return False
        return self.orientation == Orientation.STANDING

    def __hash__(self):
        if self.cubes is not None:
            return hash((self.cubes, self.active_cube, self.bridges_state))
        return hash((self.r, self.c, self.orientation, self.bridges_state))

    def __eq__(self, other):
        if not isinstance(other, BloxorzState):
            return False
        if self.cubes is not None or other.cubes is not None:
            return (self.cubes, self.active_cube, self.bridges_state) == \
                   (other.cubes, other.active_cube, other.bridges_state)
        return (self.r, self.c, self.orientation, self.bridges_state) == \
               (other.r, other.c, other.orientation, other.bridges_state)

    def __lt__(self, other):
        return False

    def __repr__(self):
        if self.cubes is not None:
            return (f"State(SPLIT, cubes={self.cubes}, active={self.active_cube}, "
                    f"bridges_state={self.bridges_state})")
        if self.bridges_state:
            return (f"State({self.r}, {self.c}, {self.orientation.name}, "
                    f"bridges_state={self.bridges_state})")
        return f"State({self.r}, {self.c}, {self.orientation.name})"
