"""Headless scene graph behavior, identity, atomic rejection and ownership."""
from dataclasses import replace
import importlib.util
import unittest
from unittest.mock import patch

from src.gui.advanced_fixtures import get_visual_fixture, SCENARIOS
from src.gui.advanced_contracts import BridgeVisualState, WholeBlockVisualPose
from src.gui.contracts import BasicOrientation

HAS_PANDA = importlib.util.find_spec('panda3d') is not None
if HAS_PANDA:
    from panda3d.core import NodePath
    from src.gui.advanced_renderer import AdvancedSceneRenderer


@unittest.skipUnless(HAS_PANDA, 'Panda3D not installed')
class AdvancedRendererTests(unittest.TestCase):
    def setUp(self):
        self.roots = tuple(NodePath(name) for name in ('static', 'dynamic', 'block'))
        self.foreign = tuple(root.attachNewNode('foreign') for root in self.roots)
        self.renderer = AdvancedSceneRenderer(*self.roots)
        self.fixture = get_visual_fixture('combined')
        self.renderer.load_board(self.fixture.board)

    def tearDown(self):
        self.renderer.dispose()
        for root in self.roots:
            root.removeNode()

    def show(self, state='whole', revision=None):
        snap = self.fixture.variant(state).snapshot
        if revision is not None:
            snap = replace(snap, state_revision=revision)
        self.renderer.show_snapshot(snap)
        return snap

    def counts(self):
        return tuple(root.findAllMatches('**').getNumPaths() for root in self.roots)

    def scene_state(self):
        return [(path.node(), path.getTransform(), path.isHidden(), path.getTag('cube_id'))
                for root in self.roots for path in root.findAllMatches('**')]

    def test_distinct_roots_and_pitch_validated(self):
        for args in ((self.roots[0],) * 3, (None, *self.roots[1:]), (NodePath(), *self.roots[1:])):
            with self.assertRaises(ValueError):
                AdvancedSceneRenderer(*args)
        with self.assertRaises(ValueError):
            AdvancedSceneRenderer(*self.roots, pitch=True)

    def test_load_does_not_guess_dynamic_state(self):
        self.assertTrue(self.renderer._contents[1].isHidden())
        self.assertTrue(self.renderer._contents[2].isHidden())
        self.assertFalse(self.renderer._contents[0].isHidden())

    def test_no_floor_under_fragile_or_bridge_and_goal_void_handling(self):
        static = self.renderer._contents[0]
        for r, c in (*self.fixture.board.fragile_cells, *self.fixture.board.bridges[0].cells, (0, 8)):
            self.assertTrue(static.find(f'Floor-{r}-{c}').isEmpty())
        self.assertFalse(static.find('Goal-1-8').isEmpty())
        self.assertTrue(static.find('Floor-1-8').isEmpty())

    def test_fragile_broken_replaces_intact(self):
        self.show()
        for intact, broken in self.renderer._fragile.values():
            self.assertFalse(intact.isHidden())
            self.assertTrue(broken.isHidden())
        self.show('broken')
        for intact, broken in self.renderer._fragile.values():
            self.assertTrue(intact.isHidden())
            self.assertFalse(broken.isHidden())

    def test_multicell_bridge_present_absent(self):
        self.show()
        bridge = self.renderer._bridges['bridge-main']
        self.assertEqual(bridge.getNumChildren(), 2)
        self.assertFalse(bridge.isHidden())
        self.show('absent')
        self.assertTrue(bridge.isHidden())
        self.assertTrue(all(child.isHidden() for child in bridge.getChildren()))

    def test_switch_activation_comes_only_from_ids(self):
        self.show()
        for inactive, active in self.renderer._switches.values():
            self.assertFalse(inactive.isHidden())
            self.assertTrue(active.isHidden())
        self.show('cube-a')
        for inactive, active in self.renderer._switches.values():
            self.assertTrue(inactive.isHidden())
            self.assertFalse(active.isHidden())

    def test_whole_split_exclusive_and_active_id(self):
        for i, state in enumerate(('whole', 'cube-a', 'cube-b', 'whole')):
            self.show(state, revision=i)
            split = state != 'whole'
            self.assertEqual(self.renderer._whole.isHidden(), split)
            self.assertEqual(sum(not c.isHidden() for c in self.renderer._cubes), 2 if split else 0)
            visible = [c.getTag('cube_id') for c, marker in zip(self.renderer._cubes, self.renderer._indicators)
                       if not marker.isHidden()]
            self.assertEqual(visible, [state] if split else [])

    def test_cube_identity_survives_tuple_reordering_and_positions(self):
        snap = self.show('cube-a')
        nodes = {c.getTag('cube_id'): c.node() for c in self.renderer._cubes}
        cubes = tuple(replace(c, cell=(0, 0)) for c in reversed(snap.cubes))
        self.renderer.show_snapshot(replace(snap, state_revision=99, cubes=cubes))
        self.assertEqual(nodes, {c.getTag('cube_id'): c.node() for c in self.renderer._cubes})
        for cube in self.renderer._cubes:
            self.assertAlmostEqual(cube.getZ(), .5)

    def test_no_active_id_means_no_highlight(self):
        snap = self.fixture.variant('cube-a').snapshot
        self.renderer.show_snapshot(replace(snap, active_cube_id=None))
        self.assertTrue(all(n.isHidden() for n in self.renderer._indicators))

    def test_revision_rules_and_opaque_session_replacement(self):
        snap = self.show(revision=5)
        before = self.scene_state()
        self.renderer.show_snapshot(snap)
        for altered in (replace(snap, state_revision=4), replace(snap, activated_switch_ids=('soft',))):
            with self.assertRaises(ValueError):
                self.renderer.show_snapshot(altered)
            self.assertEqual(self.scene_state(), before)
        self.renderer.show_snapshot(replace(snap, session_id='arbitrary-older-looking', state_revision=0))
        self.assertEqual(self.renderer._snapshot.state_revision, 0)

    def test_invalid_updates_leave_all_visuals_unchanged(self):
        snap = self.show('cube-a')
        before = self.scene_state()
        for fields in ({'board_revision': 'wrong'}, {'bridge_states': ()},
                       {'bridge_states': (BridgeVisualState('unknown', False),)},
                       {'broken_fragile_cells': ((0, 0),)}, {'activated_switch_ids': ('unknown',)},
                       {'cubes': (snap.cubes[0], replace(snap.cubes[1], cell=(99, 0)))}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.renderer.show_snapshot(replace(snap, state_revision=99, **fields))
            self.assertEqual(self.scene_state(), before)
            self.assertIs(self.renderer._snapshot, snap)

    def test_absolute_whole_pose_and_custom_pitch(self):
        fixture = get_visual_fixture('basic')
        self.renderer.load_board(fixture.board)
        for v in fixture.variants:
            self.renderer.show_snapshot(v.snapshot)
            low, high = self.renderer._whole.getTightBounds()
            self.assertAlmostEqual(low.z, 0, places=5)
            expected = 2 if v.name == 'standing' else 1
            self.assertAlmostEqual(high.z, expected, places=5)

    def test_repeated_updates_reuse_nodes_meshes_and_static_content(self):
        self.show()
        counts, static = self.counts(), self.renderer._contents[0].node()
        meshes = self.renderer._meshes.copy()
        for i in range(300):
            self.show(self.fixture.variants[i % len(self.fixture.variants)].name, revision=i + 1)
        self.assertEqual(self.counts(), counts)
        self.assertEqual(self.renderer._contents[0].node(), static)
        self.assertEqual(self.renderer._meshes, meshes)
        self.assertLessEqual(len(self.renderer._cube_slots), 2)

    def test_load_same_board_noop_revision_conflict_and_failed_build_atomic(self):
        self.show()
        old = self.scene_state()
        self.renderer.load_board(self.fixture.board)
        self.assertEqual(self.scene_state(), old)
        with self.assertRaises(ValueError):
            self.renderer.load_board(replace(self.fixture.board, level_id='changed'))
        with patch.object(self.renderer, '_instance', side_effect=RuntimeError('construction failure')):
            with self.assertRaises(RuntimeError):
                self.renderer.load_board(get_visual_fixture('basic').board)
        self.assertEqual(self.scene_state(), old)

    def test_reload_clear_dispose_preserve_host_and_foreign_nodes(self):
        for name in SCENARIOS * 3:
            fixture = get_visual_fixture(name)
            self.renderer.load_board(fixture.board)
            self.renderer.show_snapshot(fixture.variants[0].snapshot)
            self.assertEqual(tuple(root.getNumChildren() for root in self.roots), (2, 2, 2))
        for operation in (self.renderer.clear, self.renderer.clear, self.renderer.dispose, self.renderer.dispose):
            operation()
            self.assertTrue(all(not node.isEmpty() for node in (*self.roots, *self.foreign)))
            self.assertEqual(tuple(root.getNumChildren() for root in self.roots), (1, 1, 1))
        with self.assertRaises(RuntimeError):
            self.renderer.load_board(self.fixture.board)

    def test_clear_retains_prototypes_and_show_requires_board(self):
        meshes = self.renderer._meshes.copy()
        self.renderer.clear()
        self.assertEqual(meshes, self.renderer._meshes)
        with self.assertRaises(RuntimeError):
            self.show()
        self.renderer.load_board(self.fixture.board)
        self.show()

    def test_no_window_or_gameplay_imports(self):
        # Creation in these tests itself needs no ShowBase. Enforce the boundary
        # against accidental future Core/Controller/Solver imports too.
        import ast
        from pathlib import Path
        tree = ast.parse(Path('src/gui/advanced_renderer.py').read_text())
        modules = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        self.assertFalse(any(m.startswith(('src.core', 'src.solvers', 'src.controller', 'direct.')) for m in modules))
