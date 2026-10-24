"""Authoritative Core -> Advanced visual DTOs. Basic preview APIs stay separate."""
from src.core.state import Orientation
from src.gui.contracts import BasicOrientation
from src.gui.advanced_contracts import (
    AdvancedTileKind as Tile, AdvancedBlockMode as Mode, AdvancedSnapshot,
    BridgeVisualDefinition, BridgeVisualState, SwitchVisualDefinition,
    SwitchVisualKind, WholeBlockVisualPose, SplitCubeVisualState,
    create_advanced_board_data, validate_snapshot,
)

CUBE_IDS = ('cube-0', 'cube-1')
ORIENTATIONS = {orientation: BasicOrientation[orientation.name] for orientation in Orientation}


def build_board_data(board, *, level_id):
    tiles = []
    kinds = {0: Tile.VOID, 1: Tile.FLOOR, 2: Tile.FLOOR, 3: Tile.FRAGILE,
             4: Tile.FLOOR, 5: Tile.FLOOR, 6: Tile.FLOOR, 7: Tile.BRIDGE}
    for row in board.grid:
        if any(code not in kinds for code in row):
            raise ValueError('Unsupported game tile code; expected 0 through 7.')
        tiles.append([kinds[code] for code in row])
    def check(cell):
        if (len(cell) != 2 or any(type(value) is not int for value in cell)
                or not 0 <= cell[0] < board.rows or not 0 <= cell[1] < board.cols):
            raise ValueError(f'Mechanic cell {cell!r} lies outside the board.')
    for cell in board.fragile_cells:
        check(cell)
        if tiles[cell[0]][cell[1]] is Tile.VOID:
            raise ValueError('Fragile metadata must reference a supported tile.')
        tiles[cell[0]][cell[1]] = Tile.FRAGILE
    bridges = []
    for index, bridge in enumerate(board.bridges):
        cells = tuple(tuple(cell) for cell in bridge.get('cells', ()))
        for cell in cells:
            check(cell)
            if cell in board.fragile_cells:
                raise ValueError('Bridge and fragile definitions must not overlap.')
            tiles[cell[0]][cell[1]] = Tile.BRIDGE
        bridges.append(BridgeVisualDefinition(str(bridge.get('id', index)), cells))
    switch_types = {}
    for cell, definitions in board.switches_by_cell.items():
        check(cell)
        types = {definition.get('type') for definition in definitions}
        if len(types) != 1:
            raise ValueError('One tile cannot display multiple different switch kinds.')
        switch_types[cell] = types.pop()
    for cell, definition in board.split_switches.items():
        check(cell)
        if cell in switch_types and switch_types[cell] != 'split':
            raise ValueError('Split switch overlaps a different switch kind.')
        switch_types[cell] = 'split'
        positions = definition.get('split_positions', ())
        if len(positions) != 2 or positions[0] == positions[1]:
            raise ValueError('Split switch requires two distinct destination cells.')
        for position in positions:
            check(position)
    switches = []
    for cell, kind in sorted(switch_types.items()):
        try:
            visual_kind = SwitchVisualKind[kind.upper()]
        except (KeyError, AttributeError) as error:
            raise ValueError(f'Unsupported switch kind {kind!r}.') from error
        switches.append(SwitchVisualDefinition(f'switch:{cell[0]}:{cell[1]}', cell, visual_kind))
    # A marker without configuration would otherwise look operational but do nothing.
    for r, row in enumerate(board.grid):
        for c, code in enumerate(row):
            if code in (4, 5, 6) and (r, c) not in switch_types:
                raise ValueError(f'Switch tile {(r, c)} has no mechanic definition.')
    return create_advanced_board_data(level_id, tuple(tuple(row) for row in tiles),
        goal_cells=((board.goal_r, board.goal_c),), bridges=tuple(bridges), switches=tuple(switches))


def build_game_snapshot(state, *, board_data, session_id, state_revision,
                        broken_fragile_cells=()):
    if len(state.bridges_state) != len(board_data.bridges):
        raise ValueError('Core bridge flags must match the visual bridge definitions.')
    occupied = set(state.get_occupied_cells())
    active_switches = tuple(switch.switch_id for switch in board_data.switches
        if switch.cell in occupied and (switch.kind is SwitchVisualKind.SOFT
                                       or state.is_standing()))
    snapshot = AdvancedSnapshot(2, session_id, state_revision, board_data.board_revision,
        Mode.SPLIT if state.is_split() else Mode.WHOLE,
        None if state.is_split() else WholeBlockVisualPose(ORIENTATIONS[state.orientation], (state.r, state.c)),
        tuple(SplitCubeVisualState(CUBE_IDS[index], cell) for index, cell in enumerate(state.cubes))
        if state.is_split() else (), CUBE_IDS[state.active_cube] if state.is_split() else None,
        tuple(BridgeVisualState(bridge.bridge_id, flag)
              for bridge, flag in zip(board_data.bridges, state.bridges_state)),
        tuple(broken_fragile_cells), active_switches)
    validate_snapshot(snapshot, board_data)
    return snapshot


def prepare_level(board, *, level_id, session_id, state_revision=0):
    data = build_board_data(board, level_id=level_id)
    initial = board.get_initial_state()
    if not board.is_valid_state(initial):
        raise ValueError('Initial block state is not supported by this board.')
    snapshot = build_game_snapshot(initial, board_data=data, session_id=session_id,
                                   state_revision=state_revision)
    return data, initial, snapshot
