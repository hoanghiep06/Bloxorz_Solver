"""Composition and failure cleanup; real onscreen evidence is a separate smoke run."""
import importlib.util
from contextlib import redirect_stderr
import io
import unittest
from unittest.mock import Mock, patch

from src.gui.advanced_fixtures import get_visual_fixture, SCENARIOS
HAS_PANDA = importlib.util.find_spec('panda3d') is not None
if HAS_PANDA:
    from panda3d.core import NodePath, AntialiasAttrib, MaterialAttrib, Material
    from src.gui import advanced_preview as preview
    from src.gui.camera import board_bounds, fit_camera, project_point
    from src.gui.contracts import BasicTileKind
    from src.gui.advanced_renderer import AdvancedSceneRenderer
    from src.gui.hud import HudViewModel
    from tools.gui_stage3_6_smoke import _vertices


@unittest.skipUnless(HAS_PANDA, 'Panda3D not installed')
class AdvancedPreviewTests(unittest.TestCase):
    def test_framing_carrier_is_explicitly_geometry_only(self):
        board = get_visual_fixture().board
        proxy = preview.build_framing_data(board)
        self.assertTrue(proxy.level_id.startswith('framing-only:'))
        self.assertEqual((proxy.rows, proxy.cols, proxy.board_revision),
                         (board.rows, board.cols, board.board_revision))
        self.assertEqual(proxy.goal_cells, ())
        self.assertTrue(all(kind is BasicTileKind.VOID for row in proxy.tiles for kind in row))
        with self.assertRaises(TypeError):
            preview.build_framing_data(proxy)

    def test_actual_advanced_geometry_fits_existing_camera_at_minimum_size(self):
        for name in SCENARIOS:
            fixture = get_visual_fixture(name)
            framing = preview.build_framing_data(fixture.board)
            fit = fit_camera(framing, 678, 530)
            world = NodePath('world')
            roots = tuple(world.attachNewNode(n) for n in ('static', 'dynamic', 'block'))
            renderer = AdvancedSceneRenderer(*roots)
            try:
                renderer.load_board(fixture.board)
                for variant in fixture.variants:
                    renderer.show_snapshot(variant.snapshot)
                    for root in roots:
                        for point in _vertices(root, world):
                            x, y, depth = project_point(point, fit)
                            self.assertLessEqual(max(abs(x), abs(y)), .741)
                            self.assertTrue(fit.near < depth < fit.far)
            finally:
                renderer.dispose()
                world.removeNode()

    def test_bad_fixture_selection_does_not_open_window(self):
        with patch.object(preview, 'BloxorzPreviewApp') as host:
            for args in (('bad', None), ('bridge', 'bad')):
                with self.assertRaises(ValueError):
                    preview.create_advanced_preview(*args)
            host.assert_not_called()

    def test_cli_invalid_state_exits_before_host(self):
        with patch.object(preview, 'create_advanced_preview') as factory, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                preview.main(['--scenario', 'bridge', '--state', 'bogus'])
            self.assertEqual(caught.exception.code, 2)
            factory.assert_not_called()

    def test_preview_failure_releases_renderer_host_and_temporary_config(self):
        app, renderer = Mock(), Mock()
        app.finalExitCallbacks = []
        with patch.object(preview, 'BloxorzPreviewApp', return_value=app), \
             patch.object(preview, 'AdvancedSceneRenderer', return_value=renderer), \
             patch.object(preview, 'AdvancedPreviewPresentation', side_effect=RuntimeError('fail')), \
             patch.object(preview, 'unloadPrcFile') as unload:
            with self.assertRaises(RuntimeError):
                preview.create_advanced_preview()
            renderer.dispose.assert_called_once()
            app.destroy.assert_called_once()
            unload.assert_called_once()

    def test_cleanup_continues_if_dashboard_dispose_raises(self):
        app, renderer = Mock(), Mock()
        app.dashboard.dispose.side_effect = RuntimeError('fail')
        with patch.object(preview, 'dispose_presentation') as presentation:
            with self.assertRaises(RuntimeError):
                preview.dispose_advanced_preview(app, renderer)
            presentation.assert_called_once_with(app)
            renderer.dispose.assert_called_once()
            app.destroy.assert_called_once()

    def test_dynamic_root_style_is_inherited_and_restored_without_foreign_loss(self):
        app = Mock()
        app.dynamic_tile_root = NodePath('dynamic')
        app.static_board_root = NodePath('static')
        foreign = app.dynamic_tile_root.attachNewNode('foreign')
        original = Material('original')
        app.dynamic_tile_root.setMaterial(original)
        before = app.dynamic_tile_root.getState()
        app.static_board_root.setMaterial(Material('new'))
        app.static_board_root.setAntialias(AntialiasAttrib.MMultisample)
        with patch.object(preview.PreviewPresentation, '__init__', return_value=None), \
             patch.object(preview.PreviewPresentation, 'dispose'):
            presentation = preview.AdvancedPreviewPresentation(app, None)
            self.assertEqual(app.dynamic_tile_root.getMaterial(), app.static_board_root.getMaterial())
            self.assertEqual(app.dynamic_tile_root.getAntialias(), AntialiasAttrib.MMultisample)
            presentation.dispose()
            presentation.dispose()
        self.assertEqual(app.dynamic_tile_root.getState(), before)
        self.assertFalse(foreign.isEmpty())
        app.dynamic_tile_root.removeNode()
        app.static_board_root.removeNode()

    def test_preview_composition_uses_one_host_and_unknown_metrics(self):
        app, renderer = Mock(), Mock()
        with patch.object(preview, 'BloxorzPreviewApp', return_value=app) as host, \
             patch.object(preview, 'AdvancedSceneRenderer', return_value=renderer), \
             patch.object(preview, 'AdvancedPreviewPresentation'), \
             patch.object(preview, 'DashboardPresentation') as dashboard:
            actual_app, actual_renderer = preview.create_advanced_preview('split', 'cube-b')
            host.assert_called_once_with()
            self.assertIs(actual_app, app)
            self.assertIs(actual_renderer, renderer)
            model = dashboard.call_args.args[1]
            self.assertIsInstance(model, HudViewModel)
            self.assertIn('VISUAL DEMO DATA', model.level_label)
            self.assertEqual(model.runtime_status, 'CUBE B ACTIVE')
            self.assertIsNone(model.move_count)
            self.assertIsNone(model.search_time_ms)
            self.assertIsNone(model.expanded_nodes)
            self.assertIsNone(model.solution_length)
            self.assertIsNone(model.peak_python_memory_bytes)
