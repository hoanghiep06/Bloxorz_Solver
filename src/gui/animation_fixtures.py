"""ANIMATION DEMO DATA — NOT AUTHORITATIVE GAMEPLAY.

Explicit storyboards and hand-authored geometry endpoints, never Core moves,
solver routes or production levels. Every request supplies its own events.
"""
from dataclasses import dataclass, replace

from src.gui.animation_contracts import (
    AnimationRequest, AnimationEvent, AnimationKind as Kind, EventKind as Event,
    TerminalVisualOutcome, validate_request,
)
from src.gui.animation_math import RollDirection as Direction
from src.gui.contracts import BasicOrientation as Orientation, BasicTileKind, StaticBoardData, GameSnapshot
from src.gui.advanced_contracts import (
    AdvancedSnapshot, AdvancedBoardData, AdvancedBlockMode as Mode, AdvancedTileKind as Tile,
    BridgeVisualDefinition, BridgeVisualState, SwitchVisualDefinition, SwitchVisualKind,
    SplitCubeVisualState as Cube, WholeBlockVisualPose as Whole, create_advanced_board_data,
)

SCENARIOS = ('basic-roll', 'roll-chain', 'cube-roll', 'fragile', 'bridge', 'switches',
             'split', 'merge', 'active-cube', 'fall', 'goal', 'combined')
PROVENANCE = 'ANIMATION DEMO DATA — NOT AUTHORITATIVE GAMEPLAY'


@dataclass(frozen=True, slots=True)
class AnimationFixture:
    name: str
    board: StaticBoardData | AdvancedBoardData
    initial: GameSnapshot | AdvancedSnapshot
    requests: tuple[AnimationRequest, ...]
    provenance: str = PROVENANCE


def _basic_snapshot(board, orientation, anchor, revision):
    r, c = anchor
    cells = ((r, c),)
    if orientation is Orientation.HORIZONTAL:
        cells += ((r, c+1),)
    elif orientation is Orientation.VERTICAL:
        cells += ((r+1, c),)
    return GameSnapshot(1, 'animation-demo:basic', revision, board.board_revision,
                         'WHOLE', orientation, anchor, cells)


def get_roll_fixture(orientation=Orientation.STANDING, direction=Direction.RIGHT):
    """Explicit expected endpoints for all twelve cuboid geometry examples."""
    if type(orientation) is not Orientation or type(direction) is not Direction:
        raise ValueError('Expected typed orientation and direction.')
    targets = {
        Orientation.STANDING: {Direction.RIGHT: (Orientation.HORIZONTAL, (3, 5)),
            Direction.LEFT: (Orientation.HORIZONTAL, (3, 2)), Direction.UP: (Orientation.VERTICAL, (1, 4)),
            Direction.DOWN: (Orientation.VERTICAL, (4, 4))},
        Orientation.HORIZONTAL: {Direction.RIGHT: (Orientation.STANDING, (3, 6)),
            Direction.LEFT: (Orientation.STANDING, (3, 3)), Direction.UP: (Orientation.HORIZONTAL, (2, 4)),
            Direction.DOWN: (Orientation.HORIZONTAL, (4, 4))},
        Orientation.VERTICAL: {Direction.RIGHT: (Orientation.VERTICAL, (3, 5)),
            Direction.LEFT: (Orientation.VERTICAL, (3, 3)), Direction.UP: (Orientation.STANDING, (2, 4)),
            Direction.DOWN: (Orientation.STANDING, (5, 4))},
    }
    board = StaticBoardData(1, 'animation-demo:basic', 'animation-basic-v1', 7, 11,
        tuple((BasicTileKind.FLOOR,)*11 for _ in range(7)), ((3, 10),))
    before = _basic_snapshot(board, orientation, (3, 4), 0)
    target_orientation, cell = targets[orientation][direction]
    after = _basic_snapshot(board, target_orientation, cell, 1)
    request = AnimationRequest(1, f'roll-{orientation.value}-{direction.name}', before, after,
                                Kind.ROLL, .85, direction)
    validate_request(request, board)
    return AnimationFixture('basic-roll', board, before, (request,))


def get_animation_fixture(name='combined'):
    if name not in SCENARIOS:
        raise ValueError(f'Unknown animation scenario {name!r}; choose {SCENARIOS}.')
    if name == 'basic-roll':
        return get_roll_fixture()
    if name == 'roll-chain':
        base = get_roll_fixture()
        # Manually authored poses, checked by the animation geometry validator.
        route = (
            (Direction.RIGHT, Orientation.HORIZONTAL, (3, 5)),
            (Direction.RIGHT, Orientation.STANDING, (3, 7)),
            (Direction.LEFT, Orientation.HORIZONTAL, (3, 5)),
            (Direction.LEFT, Orientation.STANDING, (3, 4)),
            (Direction.UP, Orientation.VERTICAL, (1, 4)),
            (Direction.UP, Orientation.STANDING, (0, 4)),
            (Direction.DOWN, Orientation.VERTICAL, (1, 4)),
            (Direction.DOWN, Orientation.STANDING, (3, 4)),
            (Direction.RIGHT, Orientation.HORIZONTAL, (3, 5)),
            (Direction.UP, Orientation.HORIZONTAL, (2, 5)),
            (Direction.LEFT, Orientation.STANDING, (2, 4)),
            (Direction.DOWN, Orientation.VERTICAL, (3, 4)),
            (Direction.LEFT, Orientation.VERTICAL, (3, 3)),
            (Direction.RIGHT, Orientation.VERTICAL, (3, 4)),
            (Direction.UP, Orientation.STANDING, (2, 4)),
            (Direction.DOWN, Orientation.VERTICAL, (3, 4)),
        )
        requests, before = [], base.initial
        for i, (direction, orientation, cell) in enumerate(route, 1):
            after = _basic_snapshot(base.board, orientation, cell, i)
            requests.append(AnimationRequest(1, f'chain-{i}', before, after, Kind.ROLL, .55, direction))
            before = after
        return AnimationFixture(name, base.board, base.initial, tuple(requests))
    rows, cols = 7, 11
    tiles = [[Tile.FLOOR]*cols for _ in range(rows)]
    tiles[1][1] = Tile.VOID
    tiles[5][2] = Tile.FRAGILE
    for c in (4, 5):
        tiles[5][c] = Tile.BRIDGE
    board = create_advanced_board_data('animation-demo:advanced', tuple(tuple(row) for row in tiles),
        goal_cells=((3, 10),), bridges=(BridgeVisualDefinition('bridge-main', ((5, 4), (5, 5))),),
        switches=tuple(SwitchVisualDefinition(kind.value.lower(), (5, col), kind)
                       for kind, col in zip(SwitchVisualKind, (7, 8, 9))))
    initial = AdvancedSnapshot(2, 'animation-demo:' + name, 0, board.board_revision, Mode.WHOLE,
        Whole(Orientation.STANDING, (3, 4)), (), None,
        (BridgeVisualState('bridge-main', False),), (), ())
    if name in ('merge', 'active-cube', 'cube-roll'):
        initial = replace(initial, block_mode=Mode.SPLIT, whole_pose=None,
                          cubes=(Cube('cube-a', (3, 4)), Cube('cube-b', (3, 8))), active_cube_id='cube-a')
    elif name == 'fall':
        initial = replace(initial, whole_pose=Whole(Orientation.STANDING, (1, 1)))
    elif name == 'goal':
        initial = replace(initial, whole_pose=Whole(Orientation.STANDING, (3, 10)))
    requests, current = [], initial

    def add(after=None, *, kind=Kind.EFFECTS, events=(), direction=None, actor_id=None, terminal=None, duration=1.1):
        nonlocal current
        if after is not None:
            after = replace(after, state_revision=current.state_revision+1)
        request = AnimationRequest(1, f'{name}-{len(requests)+1}', current, after, kind,
            duration, direction, actor_id, events, terminal)
        validate_request(request, board)
        requests.append(request)
        if after is not None:
            current = after

    def split():
        add(replace(current, block_mode=Mode.SPLIT, whole_pose=None,
                    cubes=(Cube('cube-a', (3, 5)), Cube('cube-b', (3, 8))), active_cube_id='cube-a'),
            events=(AnimationEvent(Event.SPLIT, cube_ids=('cube-a', 'cube-b'), active_cube_id='cube-a'),))

    def merge():
        add(replace(current, block_mode=Mode.WHOLE, whole_pose=Whole(Orientation.STANDING, (3, 6)),
                    cubes=(), active_cube_id=None),
            events=(AnimationEvent(Event.MERGE, cube_ids=('cube-a', 'cube-b')),))

    def active(cube_id):
        add(replace(current, active_cube_id=cube_id),
            events=(AnimationEvent(Event.ACTIVE_CUBE_CHANGE, active_cube_id=cube_id),), duration=.65)

    if name == 'fragile':
        add(replace(current, broken_fragile_cells=((5, 2),)),
            events=(AnimationEvent(Event.FRAGILE_BREAK, cell=(5, 2)),))
    elif name == 'bridge':
        add(replace(current, bridge_states=(BridgeVisualState('bridge-main', True),)),
            events=(AnimationEvent(Event.BRIDGE_PRESENT, target_id='bridge-main'),))
        add(replace(current, bridge_states=(BridgeVisualState('bridge-main', False),)),
            events=(AnimationEvent(Event.BRIDGE_ABSENT, target_id='bridge-main'),))
    elif name == 'switches':
        for activated, event in ((True, Event.SWITCH_ACTIVATE), (False, Event.SWITCH_DEACTIVATE)):
            add(replace(current, activated_switch_ids=('soft', 'heavy', 'split') if activated else ()),
                events=tuple(AnimationEvent(event, start=i*.12, end=.65+i*.12, target_id=key)
                             for i, key in enumerate(('soft', 'heavy', 'split'))))
    elif name == 'split':
        split()
    elif name == 'merge':
        merge()
    elif name == 'active-cube':
        active('cube-b'); active(None); active('cube-a')
    elif name == 'cube-roll':
        add(replace(current, cubes=(Cube('cube-a', (3, 5)), current.cubes[1])),
            kind=Kind.ROLL, direction=Direction.RIGHT, actor_id='cube-a')
    elif name in ('fall', 'goal'):
        event = Event.FALL if name == 'fall' else Event.GOAL_COMPLETE
        add(kind=Kind.TERMINAL, terminal=TerminalVisualOutcome(event), events=(AnimationEvent(event),), duration=1.5)
    else:
        add(replace(current, whole_pose=Whole(Orientation.HORIZONTAL, (3, 5))),
            kind=Kind.ROLL, direction=Direction.RIGHT, duration=.85)
        add(replace(current, activated_switch_ids=('soft',), bridge_states=(BridgeVisualState('bridge-main', True),)),
            events=(AnimationEvent(Event.SWITCH_ACTIVATE, 0, .35, target_id='soft'),
                    AnimationEvent(Event.BRIDGE_PRESENT, .35, 1, target_id='bridge-main')))
        add(replace(current, broken_fragile_cells=((5, 2),)),
            events=(AnimationEvent(Event.FRAGILE_BREAK, cell=(5, 2)),))
        split()
        active('cube-b')
        add(replace(current, cubes=(current.cubes[0], Cube('cube-b', (3, 7)))),
            kind=Kind.ROLL, direction=Direction.LEFT, actor_id='cube-b', duration=.85)
        merge()
    return AnimationFixture(name, board, initial, tuple(requests))
