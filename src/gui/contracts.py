"""Immutable Basic render data; coordinates are always logical (row, col).

Direct constructors require tuples, including nested containers. These contracts
describe structure, not passability, movement, victory or rendering resources.
"""

from dataclasses import dataclass
from enum import Enum


class BasicTileKind(Enum):
    """Basic surface kinds; goal positions are carried separately."""

    VOID = "VOID"
    FLOOR = "FLOOR"


class BasicOrientation(Enum):
    """A whole block's logical footprint, independent of engine rotations."""

    STANDING = "STANDING"
    HORIZONTAL = "HORIZONTAL"
    VERTICAL = "VERTICAL"


def _require_int(value: int, field: str, *, minimum: int = 0) -> None:
    if type(value) is not int:
        raise TypeError(f"{field} must be an integer (not bool).")
    if value < minimum:
        raise ValueError(f"{field} must be >= {minimum}.")


def _require_text(value: str, field: str) -> None:
    if type(value) is not str:
        raise TypeError(f"{field} must be a string.")
    if not value.strip():
        raise ValueError(f"{field} must not be empty or whitespace.")


def _require_cell(cell: tuple[int, int], field: str) -> None:
    if type(cell) is not tuple or len(cell) != 2:
        raise TypeError(f"{field} must be a tuple (row, col).")
    for index, coordinate in enumerate(cell):
        _require_int(coordinate, f"{field}[{index}]")


def _require_schema(version: int) -> None:
    _require_int(version, "schema_version")
    if version != 1:
        raise ValueError("schema_version must be 1.")


@dataclass(frozen=True, slots=True)
class StaticBoardData:
    """Detached static board data, built once per level/content load."""

    schema_version: int
    level_id: str
    board_revision: str
    rows: int
    cols: int
    tiles: tuple[tuple[BasicTileKind, ...], ...]
    goal_cells: tuple[tuple[int, int], ...]

    def __post_init__(self) -> None:
        _require_schema(self.schema_version)
        _require_text(self.level_id, "level_id")
        _require_text(self.board_revision, "board_revision")
        _require_int(self.rows, "rows", minimum=1)
        _require_int(self.cols, "cols", minimum=1)
        if type(self.tiles) is not tuple:
            raise TypeError("tiles must be a tuple of tuples.")
        if len(self.tiles) != self.rows:
            raise ValueError(f"tiles must contain exactly {self.rows} rows.")
        for row_index, row in enumerate(self.tiles):
            if type(row) is not tuple:
                raise TypeError(f"tiles[{row_index}] must be a tuple.")
            if len(row) != self.cols:
                raise ValueError(f"tiles[{row_index}] must contain exactly {self.cols} cells.")
            for col_index, kind in enumerate(row):
                if not isinstance(kind, BasicTileKind):
                    raise TypeError(f"tiles[{row_index}][{col_index}] must be BasicTileKind.")
        if type(self.goal_cells) is not tuple:
            raise TypeError("goal_cells must be a tuple of cells.")
        for index, cell in enumerate(self.goal_cells):
            _require_cell(cell, f"goal_cells[{index}]")
            if cell[0] >= self.rows or cell[1] >= self.cols:
                raise ValueError(f"goal_cells[{index}] lies outside the board.")
        if len(set(self.goal_cells)) != len(self.goal_cells):
            raise ValueError("goal_cells must not contain duplicate cells.")


@dataclass(frozen=True, slots=True)
class GameSnapshot:
    """One whole-block pose plus caller identity, without a Core reference.

    Occupied cells must be in canonical row/column order. Board bounds are checked
    by the adapter, since this DTO deliberately carries no board dimensions.
    """

    schema_version: int
    session_id: str
    state_revision: int
    board_revision: str
    block_mode: str
    orientation: BasicOrientation
    anchor_cell: tuple[int, int]
    occupied_cells: tuple[tuple[int, int], ...]

    def __post_init__(self) -> None:
        _require_schema(self.schema_version)
        _require_text(self.session_id, "session_id")
        _require_int(self.state_revision, "state_revision")
        _require_text(self.board_revision, "board_revision")
        if type(self.block_mode) is not str or self.block_mode != "WHOLE":
            raise ValueError("block_mode must be WHOLE; split is unsupported in Basic.")
        if not isinstance(self.orientation, BasicOrientation):
            raise TypeError("orientation must be BasicOrientation.")
        _require_cell(self.anchor_cell, "anchor_cell")
        if type(self.occupied_cells) is not tuple:
            raise TypeError("occupied_cells must be a tuple of cells.")
        for index, cell in enumerate(self.occupied_cells):
            _require_cell(cell, f"occupied_cells[{index}]")
        row, col = self.anchor_cell
        # Footprint consistency only: no movement table or game-rule evaluation.
        expected = {
            BasicOrientation.STANDING: ((row, col),),
            BasicOrientation.HORIZONTAL: ((row, col), (row, col + 1)),
            BasicOrientation.VERTICAL: ((row, col), (row + 1, col)),
        }[self.orientation]
        if self.occupied_cells != expected:
            raise ValueError("occupied_cells inconsistent with orientation/anchor_cell "
                             "or not in canonical order.")
