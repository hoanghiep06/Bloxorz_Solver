"""Schema 2 visual data only: no engine, Core references or gameplay inference.

Snapshots are complete visual states, not deltas. Bridge ``present`` means an
actual platform. IDs and all dynamic states must be supplied by the caller.
"""

from dataclasses import dataclass
from enum import Enum
import hashlib
import json

from src.gui.contracts import BasicOrientation

Cell = tuple[int, int]


class AdvancedTileKind(Enum):
    VOID = 'VOID'
    FLOOR = 'FLOOR'
    FRAGILE = 'FRAGILE'
    BRIDGE = 'BRIDGE'


class SwitchVisualKind(Enum):
    SOFT = 'SOFT'
    HEAVY = 'HEAVY'
    SPLIT = 'SPLIT'


class AdvancedBlockMode(Enum):
    WHOLE = 'WHOLE'
    SPLIT = 'SPLIT'


def _text(value, field):
    if type(value) is not str or not value.strip():
        raise ValueError(f'{field} must be nonempty text.')


def _integer(value, field, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{field} must be an integer >= {minimum} (not bool).')


def _cell(value):
    if type(value) is not tuple or len(value) != 2:
        raise TypeError('cell must be an immutable (row, col) tuple.')
    for coordinate in value:
        _integer(coordinate, 'coordinate')


def _tuple(value, field):
    if type(value) is not tuple:
        raise TypeError(f'{field} must be an immutable tuple.')


def _unique(values, field):
    if len(set(values)) != len(values):
        raise ValueError(f'{field} contains duplicates.')


def _cells(value, field):
    _tuple(value, field)
    for cell in value:
        _cell(cell)
    _unique(value, field)


def _objects(value, cls, field, id_field):
    _tuple(value, field)
    for item in value:
        if type(item) is not cls:
            raise TypeError(f'{field} must contain {cls.__name__}.')
        item.__post_init__()
    _unique(tuple(getattr(item, id_field) for item in value), field)


def _schema(value):
    _integer(value, 'schema_version')
    if value != 2:
        raise ValueError('Advanced schema_version must be 2.')


@dataclass(frozen=True, slots=True)
class BridgeVisualDefinition:
    bridge_id: str
    cells: tuple[Cell, ...]

    def __post_init__(self):
        _text(self.bridge_id, 'bridge_id')
        _cells(self.cells, 'bridge cells')
        if not self.cells:
            raise ValueError('A bridge definition needs at least one cell.')


@dataclass(frozen=True, slots=True)
class SwitchVisualDefinition:
    switch_id: str
    cell: Cell
    kind: SwitchVisualKind

    def __post_init__(self):
        _text(self.switch_id, 'switch_id')
        _cell(self.cell)
        if type(self.kind) is not SwitchVisualKind:
            raise TypeError('kind must be SwitchVisualKind.')


@dataclass(frozen=True, slots=True)
class BridgeVisualState:
    bridge_id: str
    present: bool

    def __post_init__(self):
        _text(self.bridge_id, 'bridge_id')
        if type(self.present) is not bool:
            raise TypeError('present must be bool: platform present/absent.')


@dataclass(frozen=True, slots=True)
class SplitCubeVisualState:
    cube_id: str
    cell: Cell

    def __post_init__(self):
        _text(self.cube_id, 'cube_id')
        _cell(self.cell)


@dataclass(frozen=True, slots=True)
class WholeBlockVisualPose:
    orientation: BasicOrientation
    anchor_cell: Cell

    def __post_init__(self):
        if type(self.orientation) is not BasicOrientation:
            raise TypeError('orientation must be BasicOrientation.')
        _cell(self.anchor_cell)


@dataclass(frozen=True, slots=True)
class AdvancedBoardData:
    schema_version: int
    level_id: str
    board_revision: str
    rows: int
    cols: int
    tiles: tuple[tuple[AdvancedTileKind, ...], ...]
    goal_cells: tuple[Cell, ...]
    bridges: tuple[BridgeVisualDefinition, ...]
    switches: tuple[SwitchVisualDefinition, ...]

    @property
    def fragile_cells(self):
        return tuple((r, c) for r, row in enumerate(self.tiles)
                     for c, kind in enumerate(row) if kind is AdvancedTileKind.FRAGILE)

    def check_bounds(self, cell):
        _cell(cell)
        if cell[0] >= self.rows or cell[1] >= self.cols:
            raise ValueError(f'cell {cell} is outside board dimensions.')

    def __post_init__(self):
        _schema(self.schema_version)
        _text(self.level_id, 'level_id')
        _text(self.board_revision, 'board_revision')
        _integer(self.rows, 'rows', 1)
        _integer(self.cols, 'cols', 1)
        _tuple(self.tiles, 'tiles')
        if len(self.tiles) != self.rows:
            raise ValueError('tiles must match rows.')
        for row in self.tiles:
            _tuple(row, 'tile row')
            if len(row) != self.cols:
                raise ValueError('tile row must match cols.')
            if any(type(kind) is not AdvancedTileKind for kind in row):
                raise TypeError('tiles must contain AdvancedTileKind.')
        _cells(self.goal_cells, 'goal_cells')
        for cell in self.goal_cells:
            self.check_bounds(cell)
            if self.tiles[cell[0]][cell[1]] is not AdvancedTileKind.FLOOR:
                raise ValueError('Visual profile supports a goal recess on FLOOR only.')
        _objects(self.bridges, BridgeVisualDefinition, 'bridges', 'bridge_id')
        bridge_cells = []
        for bridge in self.bridges:
            for cell in bridge.cells:
                self.check_bounds(cell)
                bridge_cells.append(cell)
        _unique(bridge_cells, 'bridge cell ownership')
        declared = {(r, c) for r, row in enumerate(self.tiles) for c, kind in enumerate(row)
                    if kind is AdvancedTileKind.BRIDGE}
        if set(bridge_cells) != declared:
            raise ValueError('Bridge definitions must partition exactly the BRIDGE tiles.')
        _objects(self.switches, SwitchVisualDefinition, 'switches', 'switch_id')
        _unique(tuple(s.cell for s in self.switches), 'switch positions')
        for switch in self.switches:
            self.check_bounds(switch.cell)
            if (self.tiles[switch.cell[0]][switch.cell[1]] is not AdvancedTileKind.FLOOR
                    or switch.cell in self.goal_cells):
                raise ValueError('Visual switch overlay requires a non-goal FLOOR.')


@dataclass(frozen=True, slots=True)
class AdvancedSnapshot:
    schema_version: int
    session_id: str
    state_revision: int
    board_revision: str
    block_mode: AdvancedBlockMode
    whole_pose: WholeBlockVisualPose | None
    cubes: tuple[SplitCubeVisualState, ...]
    active_cube_id: str | None
    bridge_states: tuple[BridgeVisualState, ...]
    broken_fragile_cells: tuple[Cell, ...]
    activated_switch_ids: tuple[str, ...]

    def __post_init__(self):
        _schema(self.schema_version)
        _text(self.session_id, 'session_id')
        _text(self.board_revision, 'board_revision')
        _integer(self.state_revision, 'state_revision')
        if type(self.block_mode) is not AdvancedBlockMode:
            raise TypeError('block_mode must be AdvancedBlockMode.')
        _objects(self.cubes, SplitCubeVisualState, 'cubes', 'cube_id')
        if self.block_mode is AdvancedBlockMode.WHOLE:
            if type(self.whole_pose) is not WholeBlockVisualPose or self.cubes or self.active_cube_id is not None:
                raise ValueError('WHOLE requires whole_pose, no cubes or active_cube_id.')
            self.whole_pose.__post_init__()
        else:
            if self.whole_pose is not None or len(self.cubes) != 2:
                raise ValueError('SPLIT requires exactly two cubes and no whole_pose.')
            if self.active_cube_id is not None:
                _text(self.active_cube_id, 'active_cube_id')
                if self.active_cube_id not in {c.cube_id for c in self.cubes}:
                    raise ValueError('active_cube_id must reference a supplied cube.')
        _objects(self.bridge_states, BridgeVisualState, 'bridge_states', 'bridge_id')
        _cells(self.broken_fragile_cells, 'broken_fragile_cells')
        _tuple(self.activated_switch_ids, 'activated_switch_ids')
        for value in self.activated_switch_ids:
            _text(value, 'activated switch ID')
        _unique(self.activated_switch_ids, 'activated_switch_ids')


def validate_snapshot(snapshot: AdvancedSnapshot, board: AdvancedBoardData) -> None:
    """Validate references and bounds, never passability or split/merge legality.

    Overlapping cubes, cubes on VOID and blocks on broken tiles are deliberately
    representable: deciding their gameplay meaning belongs to authoritative Core.
    """
    if type(board) is not AdvancedBoardData or type(snapshot) is not AdvancedSnapshot:
        raise TypeError('Expected AdvancedBoardData and AdvancedSnapshot schema 2.')
    board.__post_init__()
    snapshot.__post_init__()
    if snapshot.board_revision != board.board_revision:
        raise ValueError('snapshot.board_revision does not match loaded board.')
    if {s.bridge_id for s in snapshot.bridge_states} != {b.bridge_id for b in board.bridges}:
        raise ValueError('Complete bridge_states must match bridge definitions exactly.')
    if not set(snapshot.broken_fragile_cells) <= set(board.fragile_cells):
        raise ValueError('broken_fragile_cells must reference FRAGILE definitions.')
    if not set(snapshot.activated_switch_ids) <= {s.switch_id for s in board.switches}:
        raise ValueError('activated_switch_ids references an unknown switch.')
    if snapshot.whole_pose is not None:
        r, c = snapshot.whole_pose.anchor_cell
        board.check_bounds((r, c))
        if snapshot.whole_pose.orientation is BasicOrientation.HORIZONTAL:
            board.check_bounds((r, c + 1))
        elif snapshot.whole_pose.orientation is BasicOrientation.VERTICAL:
            board.check_bounds((r + 1, c))
    for cube in snapshot.cubes:
        board.check_bounds(cube.cell)


def create_advanced_board_data(level_id, tiles, *, goal_cells=(), bridges=(), switches=()):
    """Build deterministic content identity from typed visual data, never raw codes.

    Tuple order is part of the payload identity. This is a visual-data factory,
    not an adapter for the still-pending Advanced Core schema.
    """
    _tuple(tiles, 'tiles')
    cols = len(tiles[0]) if tiles and type(tiles[0]) is tuple else 0
    board = AdvancedBoardData(2, level_id, 'validation', len(tiles), cols,
                              tiles, goal_cells, bridges, switches)
    payload = [2, level_id, [[kind.value for kind in row] for row in tiles], goal_cells,
               [(b.bridge_id, b.cells) for b in bridges],
               [(s.switch_id, s.cell, s.kind.value) for s in switches]]
    digest = hashlib.sha256(json.dumps(payload, separators=(',', ':'),
                                       ensure_ascii=False).encode('utf-8')).hexdigest()
    from dataclasses import replace
    return replace(board, board_revision=digest)
