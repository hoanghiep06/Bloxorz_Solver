"""Whole Basic pipeline with real Core, adapter, geometry, camera and DirectGUI.

No ShowBase or GraphicsWindow is needed. Region/window doubles are explicit;
the companion smoke tool supplies separate onscreen evidence.
"""

import copy
from dataclasses import replace
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.core.board import Board
from src.core.state import BloxorzState, Orientation
from src.gui.contracts import BasicOrientation, BasicTileKind
from src.gui.render_adapter import build_board_data, build_game_snapshot
from tools.gui_stage3_6_smoke import SHAPES, SIZES, make_fixture, make_snapshot


ROOT = Path(__file__).resolve().parents[1]
HAS_PANDA = importlib.util.find_spec('panda3d') is not None


class RegionDouble:
    def __init__(self, camera):
        self.camera, self.dimensions, self.active = camera, (0, 1, 0, 1), True
    def getCamera(self): return self.camera
    def getDimensions(self): return self.dimensions
    def setDimensions(self, *values): self.dimensions = values
    def isActive(self): return self.active
    def setActive(self, value): self.active = value


class WindowDouble:
    width, height = 1280, 720
    def __init__(self, regions): self.regions = regions
    def getDisplayRegions(self): return tuple(self.regions)
    def getXSize(self): return self.width
    def getYSize(self): return self.height
    def getFbProperties(self): return SimpleNamespace(getMultisamples=lambda: 0)
    def getGsg(self): return None


class SceneFixture(unittest.TestCase):
    def setUp(self):
        from panda3d.core import Camera, NodePath, PerspectiveLens
        from src.gui.renderer import BasicSceneRenderer
        from src.gui.board_preview import PreviewPresentation
        from src.gui.dashboard_preview import DashboardPresentation
        from src.gui.hud import HudViewModel
        self.board = Board(str(ROOT / 'levels/level_01.json'))
        self.initial = self.board.get_initial_state()
        self.data = build_board_data(self.board, level_id='levels/level_01.json')
        self.snapshot = build_game_snapshot(self.initial, board_data=self.data,
                                            session_id='integration', state_revision=0)
        self.host = NodePath('host-fixture')
        self.addCleanup(self.host.removeNode)
        scene = self.host.attachNewNode('SceneRoot')
        camera = self.host.attachNewNode('camera')
        lens = PerspectiveLens()
        cam = camera.attachNewNode(Camera('main-camera', lens))
        ui = self.host.attachNewNode(Camera('ui-camera'))
        self.app = SimpleNamespace(
            scene_root=scene, camera=camera, cam=cam, camLens=lens,
            static_board_root=scene.attachNewNode('StaticBoardRoot'),
            block_root=scene.attachNewNode('BlockRoot'),
            dynamic_tile_root=scene.attachNewNode('DynamicTileRoot'),
            effects_root=scene.attachNewNode('EffectsRoot'),
            pixel2d=self.host.attachNewNode('pixel2d'), finalExitCallbacks=[],
            win=WindowDouble([RegionDouble(cam), RegionDouble(ui)]))
        self.renderer = BasicSceneRenderer(self.app.static_board_root, self.app.block_root)
        self.addCleanup(self.renderer.dispose)
        self.renderer.load_board(self.data)
        self.renderer.show_snapshot(self.snapshot)
        self.app.presentation = PreviewPresentation(self.app, self.data)
        self.addCleanup(self.app.presentation.dispose)
        self.app.dashboard = DashboardPresentation(self.app, HudViewModel())
        self.addCleanup(self.app.dashboard.dispose)


@unittest.skipUnless(HAS_PANDA, 'Panda3D integration requires GUI .venv; no window is opened.')
class PipelineIntegrationTests(SceneFixture):
    def test_real_level_static_scene_adapter_camera_and_hud(self):
        original = copy.deepcopy(vars(self.board))
        initial_hash = hash(self.initial)
        with patch.object(Board, 'transition', side_effect=AssertionError('gameplay call')):
            data = build_board_data(self.board, level_id=self.data.level_id)
            snapshot = build_game_snapshot(self.initial, board_data=data,
                                           session_id='integration', state_revision=0)
            self.renderer.load_board(data)
            self.renderer.show_snapshot(snapshot)
        self.assertEqual((data.rows, data.cols), (4, 7))
        self.assertEqual(data.goal_cells, ((1, 6),))
        self.assertEqual(snapshot.anchor_cell, (1, 1))
        static = self.app.static_board_root
        self.assertEqual(static.findAllMatches('**/Floor-*').getNumPaths(), 19)
        self.assertEqual(static.findAllMatches('**/Goal-*').getNumPaths(), 1)
        for r, row in enumerate(data.tiles):
            for c, kind in enumerate(row):
                if kind is BasicTileKind.VOID:
                    self.assertTrue(static.find(f'**/Floor-{r}-{c}').isEmpty())
                    self.assertTrue(static.find(f'**/Goal-{r}-{c}').isEmpty())
        self.assertEqual(sum(kind is BasicTileKind.VOID for row in data.tiles for kind in row), 8)
        goal = static.find('**/Goal-1-6')
        self.assertEqual(tuple(goal.getPos()), (3, .5, 0))
        self.assertFalse(goal.find('GoalMesh').isEmpty())
        self.assertTrue(goal.find('FloorMesh').isEmpty())
        hud = self.app.dashboard.hud
        self.assertEqual(hud.level['text'], 'Level 01')
        self.assertEqual(hud.runtime['text'], 'PREVIEW')
        self.assertEqual([label['text'] for label in hud.metric_values], ['—'] * 5)
        self.assertAlmostEqual(self.app.camLens.getAspectRatio(), 934 / 530, places=5)
        self.assertEqual(vars(self.board), original)
        self.assertEqual(hash(self.initial), initial_hash)

    def test_three_core_poses_have_real_bounds_without_refit_or_mutation(self):
        original = copy.deepcopy(vars(self.board))
        static = self.app.static_board_root.find('BasicBoardContent').node()
        block = self.app.block_root.find('MainBlockVisual').node()
        camera_transform = self.app.camera.getTransform()
        expected = {
            Orientation.STANDING: ((-2, .5, 1), (1, 1, 2)),
            Orientation.HORIZONTAL: ((-1.5, .5, .5), (2, 1, 1)),
            Orientation.VERTICAL: ((-2, 0, .5), (1, 2, 1)),
        }
        for revision, (orientation, (center, dimensions)) in enumerate(expected.items(), 1):
            state = BloxorzState(self.initial.r, self.initial.c, orientation)
            key = hash(state)
            snapshot = build_game_snapshot(state, board_data=self.data,
                                           session_id='integration', state_revision=revision)
            self.renderer.show_snapshot(snapshot)
            path = self.app.block_root.find('MainBlockVisual')
            lower, upper = path.getTightBounds(self.host)
            for axis in range(3):
                self.assertAlmostEqual((lower[axis] + upper[axis]) / 2, center[axis], places=5)
                self.assertAlmostEqual(upper[axis] - lower[axis], dimensions[axis], places=5)
            self.assertAlmostEqual(lower.z, 0, places=5)
            self.assertEqual(tuple(path.getScale()), (1, 1, 1))
            self.assertEqual(path.node(), block)
            self.assertEqual(self.app.static_board_root.find('BasicBoardContent').node(), static)
            self.assertEqual(self.app.camera.getTransform(), camera_transform)
            self.assertEqual(hash(state), key)
        self.assertEqual(vars(self.board), original)

    def test_negative_snapshots_leave_whole_pipeline_unchanged(self):
        path = self.app.block_root.find('MainBlockVisual')
        before = (path.getTransform(), self.app.camera.getTransform(),
                  self.host.findAllMatches('**').getNumPaths())
        for field, value in (('board_revision', 'wrong'), ('orientation', 'DIAGONAL'),
                             ('state_revision', -1), ('block_mode', 'SPLIT')):
            bad = replace(self.snapshot)
            object.__setattr__(bad, field, value)
            with self.subTest(field=field), self.assertRaises((TypeError, ValueError)):
                self.renderer.show_snapshot(bad)
            self.assertEqual(before, (path.getTransform(), self.app.camera.getTransform(),
                                      self.host.findAllMatches('**').getNumPaths()))
        self.renderer.show_snapshot(replace(self.snapshot, state_revision=2))
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.renderer.show_snapshot(replace(self.snapshot, state_revision=1))

    def test_goal_authority_and_invalid_profile_are_atomic(self):
        moved_goal = replace(self.data, board_revision='goal-moved', goal_cells=((2, 6),))
        self.renderer.load_board(moved_goal)
        self.assertFalse(self.app.static_board_root.find('**/Goal-2-6').isEmpty())
        self.assertFalse(self.app.static_board_root.find('**/Floor-1-6').isEmpty())
        content = self.app.static_board_root.find('BasicBoardContent').node()
        with self.assertRaisesRegex(ValueError, 'goal on VOID'):
            self.renderer.load_board(replace(self.data, board_revision='bad-goal', goal_cells=((0, 6),)))
        with self.assertRaisesRegex(ValueError, 'revision reused'):
            self.renderer.load_board(replace(moved_goal, goal_cells=()))
        self.assertEqual(self.app.static_board_root.find('BasicBoardContent').node(), content)
        self.assertFalse(self.app.scene_root.isEmpty())

    def test_hud_binding_never_enables_actions_or_reads_core(self):
        from src.gui.hud import HudViewModel
        hud = self.app.dashboard.hud
        with patch.object(Board, 'get_initial_state', side_effect=AssertionError('HUD read Core')), \
             patch.object(Board, 'transition', side_effect=AssertionError('HUD mutated Core')):
            hud.update_view_model(HudViewModel(move_count=0, search_time_ms=12.5,
                expanded_nodes=123, solution_length=7, peak_python_memory_bytes=2048))
        self.assertEqual([label['text'] for label in hud.metric_values],
                         ['0', '12.50 ms', '123', '7', '2.00 KiB'])
        for widget in (*hud.buttons.values(), hud.speed, hud.speed.component('thumb')):
            self.assertFalse(widget.guiItem.getActive())
            self.assertIsNone(widget['command'])
        with self.assertRaises(ValueError):
            HudViewModel(search_time_ms=float('inf'))
        hud.dispose(); hud.dispose()
        with self.assertRaisesRegex(RuntimeError, 'disposed'):
            hud.update_view_model(HudViewModel())

    def test_shape_matrix_through_renderer_lens_lights_viewport_and_hud(self):
        from direct.showbase.MessengerGlobal import messenger
        from panda3d.core import Point2, Point3
        camera = self.app.presentation.camera
        light = self.app.presentation.lighting
        widgets = tuple(id(widget) for widget in self.app.dashboard.hud._widgets)
        for name in SHAPES:
            data = make_fixture(name)
            self.renderer.load_board(data)
            self.renderer.show_snapshot(make_snapshot(data))
            camera.fit_board(data, 934, 530)
            for width, height in SIZES:
                self.app.win.width, self.app.win.height = width, height
                self.app.camLens.setAspectRatio(width / height)
                messenger.send('aspectRatioChanged')
                fit = camera.current_fit
                for corner in fit.bounds.corners():
                    point = self.app.camera.getRelativePoint(self.host, Point3(*corner))
                    projected = Point2()
                    self.assertTrue(self.app.camLens.project(point, projected))
                    self.assertLessEqual(max(abs(projected.x), abs(projected.y)), .74001)
                    light_point = light.key.getRelativePoint(self.app.scene_root, Point3(*corner))
                    self.assertTrue(light.key.node().getLens().project(light_point, projected))
                    self.assertLess(max(abs(projected.x), abs(projected.y)), 1)
                self.assertEqual(len(self.app.win.regions), 2)
                self.assertEqual(tuple(id(widget) for widget in self.app.dashboard.hud._widgets), widgets)
                self.assertEqual(len(self.app.dashboard.hud.metric_values), 5)
                self.assertAlmostEqual(self.app.camLens.getVfov(), 45, places=4)
