"""Pure schema/reference tests: these run without Panda3D installed."""
from dataclasses import FrozenInstanceError, replace
import subprocess
import sys
import unittest

from src.gui.advanced_contracts import (
    AdvancedBlockMode as Mode, AdvancedTileKind as Tile, AdvancedSnapshot,
    BridgeVisualDefinition, BridgeVisualState, SplitCubeVisualState,
    SwitchVisualDefinition, SwitchVisualKind, WholeBlockVisualPose,
    create_advanced_board_data, validate_snapshot,
)
from src.gui.advanced_fixtures import SCENARIOS, get_visual_fixture
from src.gui.contracts import BasicOrientation


class AdvancedContractTests(unittest.TestCase):
    def setUp(self):
        self.fixture = get_visual_fixture('combined')
        self.board = self.fixture.board
        self.snapshot = self.fixture.variants[0].snapshot

    def test_all_fixtures_validate_and_declare_provenance(self):
        for name in SCENARIOS:
            fixture = get_visual_fixture(name)
            self.assertEqual(fixture.provenance, 'VISUAL DEMO DATA')
            for variant in fixture.variants:
                with self.subTest(name=name, state=variant.name):
                    validate_snapshot(variant.snapshot, fixture.board)

    def test_deep_immutability(self):
        for obj, key in ((self.board, 'rows'), (self.snapshot, 'state_revision'),
                         (self.board.bridges[0], 'bridge_id'), (self.board.switches[0], 'cell')):
            with self.assertRaises(FrozenInstanceError):
                setattr(obj, key, None)
        with self.assertRaises(TypeError):
            self.board.tiles[0][0] = Tile.VOID
        with self.assertRaises(TypeError):
            replace(self.snapshot, bridge_states=list(self.snapshot.bridge_states))
        with self.assertRaises(TypeError):
            replace(self.board, tiles=tuple(list(row) for row in self.board.tiles))

    def test_identity_is_deterministic_and_sensitive_to_semantics(self):
        self.assertEqual(self.board, get_visual_fixture('combined').board)
        fields = dict(goal_cells=self.board.goal_cells, bridges=self.board.bridges,
                      switches=self.board.switches)
        changed = create_advanced_board_data('different-id', self.board.tiles, **fields)
        self.assertNotEqual(changed.board_revision, self.board.board_revision)
        changed = create_advanced_board_data(self.board.level_id, self.board.tiles,
                    **{**fields, 'switches': tuple(replace(s, kind=SwitchVisualKind.HEAVY)
                                                   for s in self.board.switches)})
        self.assertNotEqual(changed.board_revision, self.board.board_revision)

    def test_invalid_dimensions_and_grid(self):
        for fields in ({'rows': 0}, {'cols': True}, {'rows': 2}, {'cols': 3}, {'tiles': ()},
                       {'tiles': self.board.tiles[:-1] + ((),)}):
            with self.subTest(fields=fields), self.assertRaises((TypeError, ValueError)):
                replace(self.board, **fields)

    def test_schema_and_visual_enums_are_strict(self):
        for fields in ({'schema_version': 1}, {'schema_version': True}):
            with self.assertRaises(ValueError):
                replace(self.board, **fields)
        for fields in ({'schema_version': 1}, {'block_mode': 'WHOLE'}):
            with self.assertRaises((ValueError, TypeError)):
                replace(self.snapshot, **fields)
        with self.assertRaises(TypeError):
            SwitchVisualDefinition('x', (0, 0), 'SOFT')
        with self.assertRaises(TypeError):
            create_advanced_board_data('x', (('FLOOR',),))

    def test_goal_profile_and_duplicate_goals(self):
        for goals in (((0, 8),), ((3, 1),), ((1, 3),), ((1, 8), (1, 8)), ((99, 1),)):
            with self.subTest(goals=goals), self.assertRaises(ValueError):
                replace(self.board, goal_cells=goals)
        self.assertEqual(replace(self.board, goal_cells=()).goal_cells, ())

    def test_bridge_definitions_must_partition_bridge_cells(self):
        for bridges in ((), self.board.bridges * 2,
                        (BridgeVisualDefinition('x', ((0, 0),)),),
                        (BridgeVisualDefinition('x', ((1, 3),)),),
                        (BridgeVisualDefinition('x', ((99, 0),)),),
                        self.board.bridges + (BridgeVisualDefinition('overlap', ((1, 3),)),)):
            with self.subTest(bridges=bridges), self.assertRaises(ValueError):
                replace(self.board, bridges=bridges)
        for args in (('', ((1, 3),)), ('x', ()), ('x', ((1, 3), (1, 3)))):
            with self.assertRaises(ValueError):
                BridgeVisualDefinition(*args)

    def test_switch_definitions_validate_identity_and_overlay_profile(self):
        for switches in (self.board.switches * 2,
                        (replace(self.board.switches[0], cell=(1, 8)),),
                        (replace(self.board.switches[0], cell=(3, 1)),),
                        (replace(self.board.switches[0], cell=(99, 0)),),
                        (self.board.switches[0], replace(self.board.switches[1], cell=(3, 0)))):
            with self.subTest(switches=switches), self.assertRaises(ValueError):
                replace(self.board, switches=switches)
        with self.assertRaises(ValueError):
            SwitchVisualDefinition(' ', (0, 0), SwitchVisualKind.SOFT)

    def test_complete_bridge_states_not_guessed(self):
        for states in ((), (BridgeVisualState('unknown', True),)):
            with self.assertRaises(ValueError):
                validate_snapshot(replace(self.snapshot, bridge_states=states), self.board)
        with self.assertRaises(ValueError):
            replace(self.snapshot, bridge_states=self.snapshot.bridge_states * 2)
        with self.assertRaises(TypeError):
            BridgeVisualState('x', 1)

    def test_broken_and_activated_references(self):
        for fields in ({'broken_fragile_cells': ((0, 0),)},
                       {'broken_fragile_cells': ((99, 0),)},
                       {'activated_switch_ids': ('unknown',)}):
            with self.assertRaises(ValueError):
                validate_snapshot(replace(self.snapshot, **fields), self.board)
        for fields in ({'broken_fragile_cells': ((3, 1), (3, 1))},
                       {'activated_switch_ids': ('soft', 'soft')}):
            with self.assertRaises(ValueError):
                replace(self.snapshot, **fields)

    def test_mode_exclusivity(self):
        cube = SplitCubeVisualState('cube-a', (0, 0))
        for fields in ({'cubes': (cube,)}, {'active_cube_id': 'cube-a'}, {'whole_pose': None},
                       {'block_mode': Mode.SPLIT},
                       {'block_mode': Mode.SPLIT, 'whole_pose': None, 'cubes': (cube,)}):
            with self.assertRaises(ValueError):
                replace(self.snapshot, **fields)

    def test_cube_ids_and_active_membership(self):
        snap = self.fixture.variant('cube-a').snapshot
        for fields in ({'active_cube_id': 'unknown'}, {'cubes': snap.cubes * 2},
                       {'cubes': (snap.cubes[0], snap.cubes[0])}):
            with self.assertRaises(ValueError):
                replace(snap, **fields)
        with self.assertRaises(ValueError):
            SplitCubeVisualState('', (0, 0))
        validate_snapshot(replace(snap, active_cube_id=None), self.board)

    def test_bounds_include_whole_footprint(self):
        for orientation, anchor in ((BasicOrientation.HORIZONTAL, (0, 8)),
                                    (BasicOrientation.VERTICAL, (4, 0)),
                                    (BasicOrientation.STANDING, (99, 0))):
            with self.assertRaises(ValueError):
                validate_snapshot(replace(self.snapshot,
                    whole_pose=WholeBlockVisualPose(orientation, anchor)), self.board)
        snap = self.fixture.variant('cube-a').snapshot
        with self.assertRaises(ValueError):
            validate_snapshot(replace(snap, cubes=(snap.cubes[0],
                replace(snap.cubes[1], cell=(99, 0)))), self.board)

    def test_structural_validation_does_not_enforce_game_rules(self):
        snap = self.fixture.variant('cube-a').snapshot
        cubes = tuple(replace(cube, cell=(0, 8)) for cube in snap.cubes)
        validate_snapshot(replace(snap, cubes=cubes), self.board)  # same VOID cell
        validate_snapshot(replace(self.snapshot, broken_fragile_cells=((3, 1),),
            whole_pose=WholeBlockVisualPose(BasicOrientation.STANDING, (3, 1))), self.board)
        validate_snapshot(replace(self.snapshot, activated_switch_ids=('soft',)), self.board)

    def test_session_revision_and_board_identity(self):
        for fields in ({'session_id': ' '}, {'state_revision': -1}, {'state_revision': True},
                       {'board_revision': ''}):
            with self.assertRaises(ValueError):
                replace(self.snapshot, **fields)
        with self.assertRaises(ValueError):
            validate_snapshot(replace(self.snapshot, board_revision='other'), self.board)

    def test_forged_nested_mutable_data_is_revalidated(self):
        bridge = BridgeVisualState('bridge-main', True)
        object.__setattr__(bridge, 'present', 'yes')
        with self.assertRaises(TypeError):
            replace(self.snapshot, bridge_states=(bridge,))

    def test_fixture_lookup_rejects_unknown_names(self):
        with self.assertRaises(ValueError):
            get_visual_fixture('not-a-level')
        with self.assertRaises(ValueError):
            self.fixture.variant('not-a-state')

    def test_pure_import_does_not_load_engine_or_core(self):
        result = subprocess.run([sys.executable, '-B', '-c',
            'import sys; import src.gui.advanced_fixtures; '
            'assert not any(n.startswith(("panda3d", "direct.", "src.core")) for n in sys.modules)'],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
