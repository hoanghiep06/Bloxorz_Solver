"""Read-only adapter for the verified Core Basic profile (raw tiles 0/1/2)."""

import hashlib
import json

from src.core.board import Board
from src.core.state import BloxorzState, Orientation
from src.gui.contracts import (
    BasicOrientation,
    BasicTileKind,
    GameSnapshot,
    StaticBoardData,
    _require_cell,
    _require_int,
    _require_text,
)


_ORIENTATIONS = {
    Orientation.STANDING: BasicOrientation.STANDING,
    Orientation.HORIZONTAL: BasicOrientation.HORIZONTAL,
    Orientation.VERTICAL: BasicOrientation.VERTICAL,
}


def build_board_data(board: Board, *, level_id: str) -> StaticBoardData:
    """Copy a Core Board into immutable Basic data and a SHA-256 revision.

    Only the current Board class/profile is supported. Other tile codes are a
    capability error, even though Core currently treats every nonzero code as floor.
    No rule validation, transitions, file loading or graphics calls are performed.
    """
    if type(board) is not Board:
        raise TypeError("board must use the supported Core Board schema.")
    _require_text(level_id, "level_id")
    _require_int(board.rows, "board.rows", minimum=1)
    _require_int(board.cols, "board.cols", minimum=1)
    if not isinstance(board.grid, (list, tuple)) or len(board.grid) != board.rows:
        raise ValueError("board.grid must contain exactly board.rows rows.")
    raw_rows = []
    tiles = []
    for row_index, row in enumerate(board.grid):
        if not isinstance(row, (list, tuple)) or len(row) != board.cols:
            raise ValueError(f"board.grid[{row_index}] must contain exactly board.cols cells.")
        for col_index, code in enumerate(row):
            field = f"board.grid[{row_index}][{col_index}]"
            if type(code) is not int:
                raise TypeError(f"{field} must be an integer tile code (not bool).")
            if code not in (0, 1, 2):
                raise ValueError(f"{field}: unsupported Basic tile code {code}; expected 0/1/2.")
        raw_rows.append(tuple(row))
        tiles.append(tuple(BasicTileKind.VOID if code == 0 else BasicTileKind.FLOOR
                           for code in row))
    goal = (board.goal_r, board.goal_c)
    _require_cell(goal, "board.goal")
    if goal[0] >= board.rows or goal[1] >= board.cols:
        raise ValueError("board.goal lies outside the board.")
    # Raw codes stay in the digest even when both 1 and 2 render as FLOOR.
    payload = {
        "level_id": level_id,
        "rows": board.rows,
        "cols": board.cols,
        "grid": raw_rows,
        "goal_cells": (goal,),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True).encode("utf-8")
    revision = hashlib.sha256(canonical).hexdigest()
    return StaticBoardData(1, level_id, revision, board.rows, board.cols,
                           tuple(tiles), (goal,))


def build_game_snapshot(
    state: BloxorzState,
    *,
    board_data: StaticBoardData,
    session_id: str,
    state_revision: int,
) -> GameSnapshot:
    """Read a Core pose; attach caller context without computing a next state.

    This checks structure and board bounds, never tile support or win/loss. It does
    not read a Core Board or rehash/copy the static grid. The caller is responsible
    for pairing the authoritative state with the board used to obtain it.
    """
    if type(state) is not BloxorzState:
        raise TypeError("state must use the supported Core BloxorzState schema.")
    if type(board_data) is not StaticBoardData:
        raise TypeError("board_data must be StaticBoardData.")
    if type(state.bridges_state) is not tuple or state.bridges_state:
        raise ValueError("state.bridges_state: unsupported Basic bridge configuration; "
                         "no bridge definitions/ID mapping are available.")
    if not isinstance(state.orientation, Orientation) or state.orientation not in _ORIENTATIONS:
        raise ValueError("state.orientation is unsupported; expected Core Orientation.")
    orientation = _ORIENTATIONS[state.orientation]
    anchor = (state.r, state.c)
    _require_cell(anchor, "state.anchor_cell")
    source_cells = state.get_occupied_cells()
    if not isinstance(source_cells, (list, tuple, set, frozenset)):
        raise TypeError("state.occupied_cells must be a list, tuple or set of cells.")
    if len(source_cells) not in (1, 2):
        raise ValueError("state.occupied_cells must contain one or two Basic cells.")
    cells = []
    for index, cell in enumerate(source_cells):
        if not isinstance(cell, (list, tuple)):
            raise TypeError(f"state.occupied_cells[{index}] must be a coordinate pair.")
        detached_cell = tuple(cell)
        _require_cell(detached_cell, f"state.occupied_cells[{index}]")
        cells.append(detached_cell)
    snapshot = GameSnapshot(1, session_id, state_revision, board_data.board_revision,
                            "WHOLE", orientation, anchor, tuple(sorted(cells)))
    for index, (row, col) in enumerate(snapshot.occupied_cells):
        if row >= board_data.rows or col >= board_data.cols:
            raise ValueError(f"occupied_cells[{index}] lies outside board_data bounds.")
    return snapshot
