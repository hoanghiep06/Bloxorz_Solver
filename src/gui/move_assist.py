"""Read-only move previews. Core owns every transition and failure decision.

Coordinates outside the board are intentionally legal in these assist-only DTOs;
this module never builds render snapshots or changes the search state.
"""
from dataclasses import dataclass
from enum import Enum
from src.core.board import ACTIONS, DIRECTION_DELTA
from src.gui.mouse_control import controlled_cells


class Severity(Enum):
    SAFE = 'safe'
    DANGER = 'danger'
    BLOCKED = 'blocked'


@dataclass(frozen=True, slots=True)
class MovePreview:
    action: str
    landing_cells: tuple
    severity: Severity
    message: str
    markers: tuple = ()
    affected_cube: int | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class AssistPreview:
    moves: tuple[MovePreview, ...]
    # (supported cell, cardinal direction) identifies only exposed edges.
    edges: tuple

    def for_action(self, action):
        return next(move for move in self.moves if move.action == action)


def predict_moves(board, state):
    moves = []
    for action in ACTIONS:
        outcome = board.describe_transition(state, action)
        motion = outcome.motion_state
        landing = tuple(controlled_cells(motion)) if motion is not None else ()
        result = outcome.next_state or outcome.attempted_state
        markers = ()
        if result is not None:
            if not state.is_split() and result.is_split():
                markers = tuple(result.cubes)
            elif state.is_split() and not result.is_split():
                landing = tuple(result.get_occupied_cells())
            if outcome.failed_cube is not None and result.is_split():
                markers = tuple(dict.fromkeys((*markers, result.cubes[outcome.failed_cube])))
        reason = outcome.failure_reason
        if reason == 'blocked':
            severity, message = Severity.BLOCKED, 'Move blocked'
        elif reason:
            severity = Severity.DANGER
            message = ('Fragile tile will break' if reason == 'fragile'
                       else 'This move will fall')
            if outcome.failed_cube is not None:
                message += f' (Cube {outcome.failed_cube + 1})'
        else:
            severity, message = Severity.SAFE, 'Safe move'
        moves.append(MovePreview(action, landing, severity, message, markers,
                                 outcome.failed_cube, reason))
    footprint = set(controlled_cells(state))
    edges = tuple((cell, action) for cell in sorted(footprint)
                  for action, (dr, dc) in DIRECTION_DELTA.items()
                  if (cell[0] + dr, cell[1] + dc) not in footprint
                  and not board.is_valid_cell(cell[0] + dr, cell[1] + dc,
                                              state.bridges_state))
    return AssistPreview(tuple(moves), edges)


class MovePredictor:
    """One bounded cache per UI layer; camera/hover do not invoke Core again."""
    def __init__(self):
        self._key = self._value = None

    def get(self, board, state, session):
        key = (board, session, state)
        if key != self._key:
            self._value = predict_moves(board, state)
            self._key = key
        return self._value

    def clear(self):
        self._key = self._value = None
