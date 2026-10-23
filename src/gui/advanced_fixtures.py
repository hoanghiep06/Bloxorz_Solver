"""VISUAL DEMO DATA. These snapshots are not Core levels or legal transitions."""

from dataclasses import dataclass

from src.gui.advanced_contracts import (
    AdvancedBlockMode as Mode, AdvancedSnapshot, AdvancedTileKind as Tile,
    BridgeVisualDefinition, BridgeVisualState, SplitCubeVisualState,
    SwitchVisualDefinition, SwitchVisualKind, WholeBlockVisualPose,
    AdvancedBoardData, create_advanced_board_data, validate_snapshot,
)
from src.gui.contracts import BasicOrientation

SCENARIOS = ('basic', 'fragile', 'bridge', 'switches', 'split', 'combined')


@dataclass(frozen=True, slots=True)
class VisualVariant:
    name: str
    label: str
    snapshot: AdvancedSnapshot


@dataclass(frozen=True, slots=True)
class VisualFixture:
    """Deterministic immutable fixture, explicitly detached from Core authority."""
    name: str
    board: AdvancedBoardData
    variants: tuple[VisualVariant, ...]
    provenance: str = 'VISUAL DEMO DATA'

    def variant(self, name=None):
        if name is None:
            return self.variants[0]
        for variant in self.variants:
            if variant.name == name:
                return variant
        raise ValueError(f'Unknown state {name!r} for {self.name}; choose '
                         + ', '.join(v.name for v in self.variants))


def get_visual_fixture(name='combined') -> VisualFixture:
    if name not in SCENARIOS:
        raise ValueError(f'Unknown scenario {name!r}; choose {SCENARIOS}.')
    rows, cols = (5, 9) if name == 'combined' else (4, 7)
    tiles = [[Tile.FLOOR for _ in range(cols)] for _ in range(rows)]
    bridges, switches = (), ()
    if name in ('fragile', 'combined'):
        for r, c in ((3, 1), (3, 2)):
            tiles[r][c] = Tile.FRAGILE
    if name in ('bridge', 'combined'):
        for r in range(rows):
            for c in (3, 4):
                tiles[r][c] = Tile.VOID
        cells = ((1, 3), (1, 4))
        for r, c in cells:
            tiles[r][c] = Tile.BRIDGE
        bridges = (BridgeVisualDefinition('bridge-main', cells),)
    if name in ('switches', 'combined'):
        positions = ((3, 0), (3, 5), (3, 6)) if name == 'combined' else ((3, 1), (3, 3), (3, 5))
        switches = tuple(SwitchVisualDefinition(kind.value.lower(), cell, kind)
                         for kind, cell in zip(SwitchVisualKind, positions))
    # An explicit VOID notch makes the edge silhouette inspectable in every demo.
    tiles[0][-1] = Tile.VOID
    board = create_advanced_board_data('visual-demo:' + name,
              tuple(tuple(row) for row in tiles), goal_cells=((1, cols - 1),),
              bridges=bridges, switches=switches)
    variants = []

    def add(state, label, *, split=False, active=None, present=True, broken=(), activated=(),
            orientation=BasicOrientation.STANDING):
        snapshot = AdvancedSnapshot(2, 'visual-demo:' + name, len(variants), board.board_revision,
            Mode.SPLIT if split else Mode.WHOLE,
            None if split else WholeBlockVisualPose(orientation, (1, 1)),
            (SplitCubeVisualState('cube-a', (1, 1)), SplitCubeVisualState('cube-b', (2, cols - 2)))
            if split else (), active,
            tuple(BridgeVisualState(b.bridge_id, present) for b in bridges), broken, activated)
        validate_snapshot(snapshot, board)
        variants.append(VisualVariant(state, label, snapshot))

    if name == 'basic':
        for orientation in BasicOrientation:
            add(orientation.value.lower(), orientation.value, orientation=orientation)
    elif name == 'fragile':
        add('intact', 'FRAGILE INTACT')
        add('broken', 'FRAGILE BROKEN', broken=board.fragile_cells)
    elif name == 'bridge':
        add('present', 'BRIDGE PRESENT')
        add('absent', 'BRIDGE ABSENT', present=False)
    elif name == 'switches':
        add('inactive', 'SWITCHES INACTIVE')
        add('activated', 'SWITCHES ACTIVATED', activated=tuple(s.switch_id for s in switches))
    elif name == 'split':
        add('whole', 'WHOLE BLOCK')
        add('cube-a', 'CUBE A ACTIVE', split=True, active='cube-a')
        add('cube-b', 'CUBE B ACTIVE', split=True, active='cube-b')
        add('no-active', 'NO ACTIVE CUBE', split=True)
    else:
        add('whole', 'COMBINED / WHOLE')
        add('absent', 'BRIDGE ABSENT', present=False)
        add('broken', 'FRAGILE BROKEN', broken=board.fragile_cells)
        add('cube-a', 'CUBE A ACTIVE', split=True, active='cube-a',
            activated=tuple(s.switch_id for s in switches))
        add('cube-b', 'CUBE B ACTIVE', split=True, active='cube-b',
            broken=board.fragile_cells, present=False)
    return VisualFixture(name, board, tuple(variants))
