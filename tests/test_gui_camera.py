"""Camera frustum mathematics and real Panda lens/event integration."""

from dataclasses import replace
import importlib.util
import math
from pathlib import Path
import subprocess
import sys
import unittest

from src.gui.camera import CameraConfig, SceneBounds, board_bounds, camera_basis, fit_camera, project_point
from src.gui.contracts import BasicOrientation, BasicTileKind, GameSnapshot, StaticBoardData


def fixture(rows=4, cols=7):
    return StaticBoardData(1, 'camera-fixture', f'{rows}x{cols}', rows, cols,
                           tuple((BasicTileKind.FLOOR,) * cols for _ in range(rows)), ())


SIZES = ((1280, 720), (934, 530), (1024, 720), (1920, 1080), (300, 1000), (1200, 300))
HAS_PANDA = importlib.util.find_spec('panda3d') is not None


class CameraMathTests(unittest.TestCase):
    def test_direction_angles_and_orthogonal_basis(self):
        back, right, up, forward = camera_basis()
        self.assertAlmostEqual(math.degrees(math.asin(back[2])), 45)
        self.assertAlmostEqual(math.degrees(math.atan2(back[0], -back[1])), 30)
        self.assertEqual(forward, tuple(-x for x in back))
        for vector in (back, right, up, forward):
            self.assertAlmostEqual(sum(v*v for v in vector), 1)
        for a, b in ((right, up), (up, forward), (right, forward)):
            self.assertAlmostEqual(sum(x*y for x, y in zip(a, b)), 0)

    def test_fov_uses_viewport_aspect(self):
        for width, height in SIZES:
            fit = fit_camera(fixture(), width, height)
            expected = math.degrees(2 * math.atan(width / height * math.tan(math.radians(22.5))))
            self.assertAlmostEqual(fit.horizontal_fov, expected)
            self.assertEqual(fit.vertical_fov, 45)
            self.assertEqual(fit.aspect, width / height)

    def test_all_corners_fit_padded_frustum_for_six_board_shapes_and_six_viewports(self):
        for rows, cols in ((4, 7), (3, 15), (15, 3), (10, 10), (1, 1), (100, 500)):
            for size in SIZES:
                with self.subTest(board=(rows, cols), size=size):
                    fit = fit_camera(fixture(rows, cols), *size)
                    projected = [project_point(p, fit) for p in fit.bounds.corners()]
                    for x, y, depth in projected:
                        self.assertLessEqual(abs(x), 0.74 + 1e-9)
                        self.assertLessEqual(abs(y), 0.74 + 1e-9)
                        self.assertLess(fit.near, depth)
                        self.assertGreater(fit.far, depth)
                    self.assertAlmostEqual(max(max(abs(x), abs(y)) for x, y, _ in projected), 0.74)

    def test_target_envelope_and_clipping(self):
        board = fixture()
        fit = fit_camera(board, 1280, 720)
        self.assertEqual(fit.target, (0, 0, 0.4))
        self.assertEqual(fit.bounds, SceneBounds((-3.5, -2, -0.18), (3.5, 2, 2.3)))
        self.assertGreater(fit.near, 0)
        self.assertGreater(fit.far, fit.near)
        self.assertLess(fit.far / fit.near, 100)

    def test_pitch_and_deterministic_results(self):
        board = fixture()
        fit = fit_camera(board, 934, 530)
        self.assertEqual(fit, fit_camera(board, 934, 530))
        scaled = fit_camera(board, 934, 530, pitch=2)
        for a, b in zip(fit.position, scaled.position):
            self.assertAlmostEqual(2*a, b)
        self.assertTrue(all(math.isfinite(v) for v in (*scaled.position, scaled.near, scaled.far)))

    def test_invalid_inputs_reject_instead_of_producing_nan_or_singularity(self):
        for field, value in (('elevation', 90), ('padding', 0.5), ('vertical_fov', 0),
                             ('vertical_fov', float('nan')), ('azimuth', float('inf'))):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    CameraConfig(**{field: value})
        for size in ((0, 1), (1, 0), (-1, 2), (True, 2), (1.5, 2)):
            with self.assertRaises(ValueError):
                fit_camera(fixture(), *size)
        for pitch in (0, -1, True, float('inf')):
            with self.assertRaises(ValueError):
                board_bounds(fixture(), pitch=pitch)
        with self.assertRaises(ValueError):
            SceneBounds((0, 0, 0), (0, 1, 1))

    def test_camera_math_imports_without_engine_or_core(self):
        code = """
import sys
from src.gui.camera import CameraConfig, camera_basis
assert camera_basis(CameraConfig())[0][2] > 0
assert not any(n.split('.')[0] in ('panda3d', 'direct', 'pygame')
               or n.startswith('src.core') for n in sys.modules)
"""
        result = subprocess.run([sys.executable, '-S', '-B', '-c', code],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_dto_is_not_modified_and_current_snapshot_is_not_an_input(self):
        data = fixture()
        before = hash(data)
        fit_camera(data, 1280, 720)
        self.assertEqual(hash(data), before)
        self.assertEqual(data, fixture())


@unittest.skipUnless(HAS_PANDA, 'Panda3D lens/scene integration requires GUI .venv.')
class CameraIntegrationTests(unittest.TestCase):
    def setUp(self):
        from panda3d.core import NodePath, PerspectiveLens
        from src.gui.camera import BoardCameraController
        self.root = NodePath('scene')
        self.node = self.root.attachNewNode('camera')
        self.lens = PerspectiveLens()
        self.controller = BoardCameraController(self.node, self.lens)
        self.data = fixture()
        self.addCleanup(self.root.removeNode)
        self.addCleanup(self.controller.dispose)

    def test_lens_readback_and_real_projection_of_all_corners(self):
        from panda3d.core import Point2, Point3
        for size in SIZES:
            self.controller.fit_board(self.data, *size)
            fit = self.controller.current_fit
            self.assertAlmostEqual(self.lens.getVfov(), 45, places=4)
            self.assertAlmostEqual(self.lens.getHfov(), fit.horizontal_fov, places=4)
            self.assertAlmostEqual(self.lens.getAspectRatio(), size[0]/size[1], places=5)
            for corner in fit.bounds.corners():
                point = self.node.getRelativePoint(self.root, Point3(*corner))
                ndc = Point2()
                self.assertTrue(self.lens.project(point, ndc))
                self.assertLessEqual(abs(ndc.x), .74001)
                self.assertLessEqual(abs(ndc.y), .74001)
                self.assertLess(self.lens.getNear(), point.y)
                self.assertGreater(self.lens.getFar(), point.y)

    def test_resize_keeps_camera_identity_and_zero_size_is_noop(self):
        self.controller.fit_board(self.data, 1280, 720)
        identity = self.node.node()
        previous = self.controller.current_fit
        self.assertFalse(self.controller.set_viewport_size(0, 0))
        self.assertEqual(previous, self.controller.current_fit)
        self.controller.set_viewport_size(300, 1000)
        self.assertEqual(identity, self.node.node())
        self.assertAlmostEqual(self.lens.getVfov(), 45, places=4)

    def test_listener_is_independent_rebinding_and_cleanup_preserve_foreign_handler(self):
        from direct.showbase.DirectObject import DirectObject
        from direct.showbase.MessengerGlobal import messenger
        class Window:
            def getXSize(self): return 1280
            def getYSize(self): return 720
        window = Window()
        other = DirectObject()
        observed = []
        other.accept('window-event', lambda win: observed.append(win))
        self.addCleanup(other.ignoreAll)
        self.controller.fit_board(self.data, 1280, 720)
        for _ in range(5):
            self.controller.bind_window(window, viewport_size=lambda win: (934, 530))
        # Simulate ShowBase's full-window adjustment before its emitted event.
        self.lens.setAspectRatio(1280/720)
        messenger.send('aspectRatioChanged')
        messenger.send('window-event', [window])
        self.assertAlmostEqual(self.lens.getAspectRatio(), 934/530, places=5)
        self.assertAlmostEqual(self.lens.getVfov(), 45, places=4)
        self.controller.dispose()
        messenger.send('window-event', [window])
        self.assertEqual(observed, [window, window])
        self.assertTrue(other.isAccepting('window-event'))

    def test_snapshot_update_does_not_move_camera_or_refit(self):
        from src.gui.renderer import BasicSceneRenderer
        from unittest.mock import patch
        renderer = BasicSceneRenderer(self.root.attachNewNode('static'), self.root.attachNewNode('block'))
        self.addCleanup(renderer.dispose)
        renderer.load_board(self.data)
        self.controller.fit_board(self.data, 1280, 720)
        transform = self.node.getTransform()
        snapshot = GameSnapshot(1, 'camera-test', 0, self.data.board_revision, 'WHOLE',
                                BasicOrientation.STANDING, (1, 1), ((1, 1),))
        with patch.object(self.controller, 'fit_board', side_effect=AssertionError('refit')):
            renderer.show_snapshot(snapshot)
        self.assertEqual(self.node.getTransform(), transform)


if __name__ == '__main__':
    unittest.main()
