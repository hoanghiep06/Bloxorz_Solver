"""Animation schema 1, independent of Basic v1/Advanced v2. No Panda or Core."""
from dataclasses import dataclass, replace
from enum import Enum

from src.gui.animation_math import RollDirection, finite
from src.gui.contracts import GameSnapshot, StaticBoardData, BasicTileKind
from src.gui.advanced_contracts import (
    AdvancedSnapshot, AdvancedBoardData, AdvancedBlockMode as Mode, AdvancedTileKind,
    WholeBlockVisualPose, validate_snapshot,
)


class AnimationKind(Enum):
    ROLL = 'ROLL'
    EFFECTS = 'EFFECTS'
    TERMINAL = 'TERMINAL'


class AnimationStatus(Enum):
    IDLE = 'IDLE'
    PLAYING = 'PLAYING'
    PAUSED = 'PAUSED'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'
    FAILED = 'FAILED'


class EventKind(Enum):
    FRAGILE_BREAK = 'FRAGILE_BREAK'
    BRIDGE_PRESENT = 'BRIDGE_PRESENT'
    BRIDGE_ABSENT = 'BRIDGE_ABSENT'
    SWITCH_ACTIVATE = 'SWITCH_ACTIVATE'
    SWITCH_DEACTIVATE = 'SWITCH_DEACTIVATE'
    SPLIT = 'SPLIT'
    MERGE = 'MERGE'
    ACTIVE_CUBE_CHANGE = 'ACTIVE_CUBE_CHANGE'
    FALL = 'FALL'
    GOAL_COMPLETE = 'GOAL_COMPLETE'


def text(value, name):
    if type(value) is not str or not value.strip():
        raise ValueError(f'{name} must be nonempty text.')


def checked_cell(cell):
    if type(cell) is not tuple or len(cell) != 2 or any(type(v) is not int or v < 0 for v in cell):
        raise ValueError('Expected immutable nonnegative (row,col) cell.')


@dataclass(frozen=True, slots=True)
class AnimationEvent:
    kind: EventKind
    start: float = 0.0
    end: float = 1.0
    target_id: str | None = None
    cell: tuple[int, int] | None = None
    cube_ids: tuple[str, ...] = ()
    active_cube_id: str | None = None

    def __post_init__(self):
        if type(self.kind) is not EventKind:
            raise TypeError('kind must be EventKind.')
        finite(self.start, 'event.start')
        finite(self.end, 'event.end')
        if not self.start < self.end <= 1:
            raise ValueError('Event requires 0<=start<end<=1.')
        for name in ('target_id', 'active_cube_id'):
            if getattr(self, name) is not None:
                text(getattr(self, name), name)
        if self.cell is not None:
            checked_cell(self.cell)
        if type(self.cube_ids) is not tuple:
            raise TypeError('cube_ids must be a tuple.')
        for key in self.cube_ids:
            text(key, 'cube_id')
        if len(set(self.cube_ids)) != len(self.cube_ids):
            raise ValueError('Duplicate cube IDs.')
        targeted = self.kind in (EventKind.BRIDGE_PRESENT, EventKind.BRIDGE_ABSENT,
                                  EventKind.SWITCH_ACTIVATE, EventKind.SWITCH_DEACTIVATE)
        if targeted != (self.target_id is not None):
            raise ValueError('Only bridge/switch events require target_id.')
        if (self.kind is EventKind.FRAGILE_BREAK) != (self.cell is not None):
            raise ValueError('Only FRAGILE_BREAK requires cell.')
        if self.kind in (EventKind.SPLIT, EventKind.MERGE):
            if len(self.cube_ids) != 2:
                raise ValueError('Split/merge requires ordered two-cube correspondence.')
        elif self.cube_ids:
            raise ValueError('cube_ids only applies to split/merge.')
        if self.kind not in (EventKind.SPLIT, EventKind.ACTIVE_CUBE_CHANGE) and self.active_cube_id is not None:
            raise ValueError('active_cube_id applies only to split/active-change.')


@dataclass(frozen=True, slots=True)
class TerminalVisualOutcome:
    kind: EventKind
    actor_id: str | None = None  # None denotes WHOLE; strings denote stable cube IDs.
    fall_distance: float = 3.0
    roll_direction: RollDirection | None = None
    collapse_cell: tuple[int, int] | None = None

    def __post_init__(self):
        if self.kind not in (EventKind.FALL, EventKind.GOAL_COMPLETE):
            raise ValueError('Terminal outcome must explicitly be FALL or GOAL_COMPLETE.')
        if self.actor_id is not None:
            text(self.actor_id, 'actor_id')
        finite(self.fall_distance, 'fall_distance', minimum=.01)
        if self.roll_direction is not None and (self.kind is not EventKind.FALL
                or type(self.roll_direction) is not RollDirection):
            raise ValueError('Only FALL can include an explicit roll direction.')
        if self.collapse_cell is not None:
            if (self.kind is not EventKind.FALL or type(self.collapse_cell) is not tuple
                    or len(self.collapse_cell) != 2
                    or any(type(v) is not int for v in self.collapse_cell)):
                raise ValueError('collapse_cell must be an integer cell on a FALL outcome.')


@dataclass(frozen=True, slots=True)
class AnimationRequest:
    schema_version: int
    request_id: str
    before_snapshot: GameSnapshot | AdvancedSnapshot
    after_snapshot: GameSnapshot | AdvancedSnapshot | None
    kind: AnimationKind
    duration: float
    direction: RollDirection | None = None
    actor_id: str | None = None
    events: tuple[AnimationEvent, ...] = ()
    terminal: TerminalVisualOutcome | None = None

    @property
    def session_id(self):
        return self.before_snapshot.session_id

    @property
    def board_revision(self):
        return self.before_snapshot.board_revision

    @property
    def from_state_revision(self):
        return self.before_snapshot.state_revision

    @property
    def to_state_revision(self):
        return None if self.after_snapshot is None else self.after_snapshot.state_revision

    def __post_init__(self):
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError('Animation schema_version must be 1.')
        text(self.request_id, 'request_id')
        if type(self.before_snapshot) not in (GameSnapshot, AdvancedSnapshot):
            raise TypeError('before_snapshot must be Basic v1 or Advanced v2.')
        self.before_snapshot.__post_init__()
        if type(self.kind) is not AnimationKind:
            raise TypeError('kind must be AnimationKind.')
        finite(self.duration, 'duration', minimum=.001)
        if self.actor_id is not None:
            text(self.actor_id, 'actor_id')
        if type(self.events) is not tuple:
            raise TypeError('events must be an immutable tuple.')
        for event in self.events:
            if type(event) is not AnimationEvent:
                raise TypeError('Expected typed AnimationEvent.')
            event.__post_init__()
        if tuple(e.start for e in self.events) != tuple(sorted(e.start for e in self.events)):
            raise ValueError('Events must be in caller-specified chronological order.')
        if self.kind is AnimationKind.ROLL:
            if type(self.direction) is not RollDirection:
                raise ValueError('ROLL needs an explicit RollDirection.')
        elif self.direction is not None or self.actor_id is not None:
            raise ValueError('Direction/actor_id only applies to ROLL; terminal has its own actor ID.')
        if self.kind is AnimationKind.TERMINAL:
            if self.after_snapshot is not None or type(self.terminal) is not TerminalVisualOutcome:
                raise ValueError('TERMINAL needs explicit outcome and no fake after snapshot.')
            self.terminal.__post_init__()
            if len(self.events) != 1 or self.events[0].kind is not self.terminal.kind:
                raise ValueError('TERMINAL supports exactly its explicitly matching outcome event.')
        else:
            if self.terminal is not None or type(self.after_snapshot) is not type(self.before_snapshot):
                raise ValueError('Nonterminal request needs same-schema after snapshot and no outcome.')
            self.after_snapshot.__post_init__()
            if (self.after_snapshot.session_id != self.session_id or
                    self.after_snapshot.board_revision != self.board_revision or
                    self.after_snapshot.state_revision <= self.from_state_revision):
                raise ValueError('After must keep board/session and increase state revision.')
            if not self.events and self.kind is AnimationKind.EFFECTS:
                raise ValueError('EFFECTS needs explicit events.')


def as_visual_board(board):
    """Verified Basic semantic conversion for an Advanced rendering host, no Core."""
    if type(board) is AdvancedBoardData:
        board.__post_init__()
        return board
    if type(board) is not StaticBoardData:
        raise TypeError('Expected Basic or Advanced board DTO.')
    board.__post_init__()
    return AdvancedBoardData(2, board.level_id, board.board_revision, board.rows, board.cols,
        tuple(tuple(AdvancedTileKind.VOID if k is BasicTileKind.VOID else AdvancedTileKind.FLOOR
                    for k in row) for row in board.tiles), board.goal_cells, (), ())


def as_visual_snapshot(snapshot):
    if type(snapshot) is AdvancedSnapshot:
        snapshot.__post_init__()
        return snapshot
    if type(snapshot) is not GameSnapshot:
        raise TypeError('Expected Basic or Advanced snapshot DTO.')
    snapshot.__post_init__()
    return AdvancedSnapshot(2, snapshot.session_id, snapshot.state_revision, snapshot.board_revision,
        Mode.WHOLE, WholeBlockVisualPose(snapshot.orientation, snapshot.anchor_cell), (), None, (), (), ())


def validate_request(request, board):
    """Validate event references and consistency, without deriving events or moves."""
    if type(request) is not AnimationRequest:
        raise TypeError('Expected AnimationRequest.')
    request.__post_init__()
    board = as_visual_board(board)
    before = as_visual_snapshot(request.before_snapshot)
    validate_snapshot(before, board)
    if request.after_snapshot is None:
        ids = {c.cube_id for c in before.cubes} if before.block_mode is Mode.SPLIT else {None}
        if request.terminal.actor_id not in ids:
            raise ValueError('Terminal actor is not present in before snapshot.')
        cell = request.terminal.collapse_cell
        if cell is not None and (cell not in board.fragile_cells
                                 or cell not in before.broken_fragile_cells):
            raise ValueError('collapse_cell must refer to a broken fragile tile in before snapshot.')
        if request.terminal.kind is EventKind.GOAL_COMPLETE:
            if before.whole_pose is None or before.whole_pose.orientation.value != 'STANDING' or before.whole_pose.anchor_cell not in board.goal_cells:
                raise ValueError('Goal visual profile requires an explicit standing whole at a goal.')
        return
    after = as_visual_snapshot(request.after_snapshot)
    validate_snapshot(after, board)
    bridges = {s.bridge_id: s.present for s in before.bridge_states}
    broken, switches = set(before.broken_fragile_cells), set(before.activated_switch_ids)
    active = before.active_cube_id
    actor_event = None
    seen = set()
    for event in request.events:
        key = ('bridge', event.target_id) if event.kind in (EventKind.BRIDGE_PRESENT, EventKind.BRIDGE_ABSENT) else (
            ('switch', event.target_id) if event.kind in (EventKind.SWITCH_ACTIVATE, EventKind.SWITCH_DEACTIVATE)
            else ('fragile', event.cell) if event.kind is EventKind.FRAGILE_BREAK else ('actor', None))
        if key in seen:
            raise ValueError('Only one event per visual target is supported in a request.')
        seen.add(key)
        if key[0] == 'bridge':
            target = event.kind is EventKind.BRIDGE_PRESENT
            if event.target_id not in bridges or bridges[event.target_id] == target:
                raise ValueError('Unknown bridge or bridge event does not change its state.')
            bridges[event.target_id] = target
        elif key[0] == 'switch':
            target = event.kind is EventKind.SWITCH_ACTIVATE
            if event.target_id not in {s.switch_id for s in board.switches} or (event.target_id in switches) == target:
                raise ValueError('Unknown switch or activation event conflicts with before state.')
            switches.add(event.target_id) if target else switches.remove(event.target_id)
        elif key[0] == 'fragile':
            if event.cell not in board.fragile_cells or event.cell in broken:
                raise ValueError('Fragile break references an unknown/already broken tile.')
            broken.add(event.cell)
        else:
            actor_event = event
            if request.kind is AnimationKind.ROLL or event.kind not in (
                EventKind.SPLIT, EventKind.MERGE, EventKind.ACTIVE_CUBE_CHANGE
            ):
                raise ValueError('Unsupported actor-event combination; use a separate explicit request.')
            if event.kind is EventKind.SPLIT:
                if before.block_mode is not Mode.WHOLE or after.block_mode is not Mode.SPLIT or set(event.cube_ids) != {c.cube_id for c in after.cubes}:
                    raise ValueError('SPLIT requires whole source and exact destination cube IDs.')
                active = event.active_cube_id
            elif event.kind is EventKind.MERGE:
                if before.block_mode is not Mode.SPLIT or after.block_mode is not Mode.WHOLE or set(event.cube_ids) != {c.cube_id for c in before.cubes}:
                    raise ValueError('MERGE requires exact source IDs and whole destination.')
                active = None
            else:
                if before.block_mode is not Mode.SPLIT or after.block_mode is not Mode.SPLIT or event.active_cube_id not in {None, *(c.cube_id for c in before.cubes)}:
                    raise ValueError('ACTIVE_CUBE_CHANGE needs a supplied split cube ID or None.')
                if event.active_cube_id == before.active_cube_id:
                    raise ValueError('ACTIVE_CUBE_CHANGE must actually change the supplied ID.')
                active = event.active_cube_id
    if bridges != {s.bridge_id: s.present for s in after.bridge_states} or broken != set(after.broken_fragile_cells) or switches != set(after.activated_switch_ids) or active != after.active_cube_id:
        raise ValueError('Explicit events must account exactly for supplied after visual state.')
    if request.kind is AnimationKind.ROLL:
        if before.block_mode is not after.block_mode:
            raise ValueError('ROLL cannot implicitly change block mode.')
        if before.block_mode is Mode.WHOLE:
            if request.actor_id is not None:
                raise ValueError('WHOLE roll uses actor_id=None.')
        else:
            old = {c.cube_id: c.cell for c in before.cubes}
            new = {c.cube_id: c.cell for c in after.cubes}
            if request.actor_id not in old or old.keys() != new.keys() or any(
                old[k] != new[k] for k in old if k != request.actor_id
            ):
                raise ValueError('Cube ROLL requires a known actor; the other cube must stay fixed.')
    elif actor_event is None or actor_event.kind is EventKind.ACTIVE_CUBE_CHANGE:
        if before.block_mode is not after.block_mode or before.whole_pose != after.whole_pose or {
            c.cube_id: c.cell for c in before.cubes
        } != {c.cube_id: c.cell for c in after.cubes}:
            raise ValueError('Actor poses cannot change without an explicit roll/split/merge.')


@dataclass(frozen=True, slots=True)
class AnimationResult:
    request_id: str
    session_id: str
    board_revision: str
    from_state_revision: int
    to_state_revision: int | None
    status: AnimationStatus
    terminal_outcome: TerminalVisualOutcome | None = None
    error: str | None = None

    def __post_init__(self):
        for name in ('request_id', 'session_id', 'board_revision'):
            text(getattr(self, name), name)
        if type(self.from_state_revision) is not int or self.from_state_revision < 0:
            raise ValueError('from_state_revision must be a nonnegative integer.')
        if self.status not in (AnimationStatus.COMPLETED, AnimationStatus.CANCELLED, AnimationStatus.FAILED):
            raise ValueError('Result must have a terminal AnimationStatus.')
        if self.to_state_revision is not None and (type(self.to_state_revision) is not int or self.to_state_revision <= self.from_state_revision):
            raise ValueError('Committed to_state_revision must increase.')
        if self.status is not AnimationStatus.COMPLETED and (self.to_state_revision is not None or self.terminal_outcome is not None):
            raise ValueError('Cancelled/failed result cannot report an after-state or terminal outcome.')
        if self.status is AnimationStatus.COMPLETED and (self.to_state_revision is None) != (self.terminal_outcome is not None):
            raise ValueError('Completed result requires either a committed revision or a terminal outcome.')
        if self.terminal_outcome is not None:
            if type(self.terminal_outcome) is not TerminalVisualOutcome:
                raise TypeError('Expected TerminalVisualOutcome.')
            self.terminal_outcome.__post_init__()
        if self.error is not None:
            text(self.error, 'error')
        if (self.status is AnimationStatus.FAILED) != (self.error is not None):
            raise ValueError('Only FAILED result requires error text.')
