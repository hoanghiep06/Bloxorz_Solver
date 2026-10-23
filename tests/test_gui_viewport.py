"""Viewport ownership using region doubles and real Panda camera/lens/events.

DisplayRegion GPU integration is verified separately by the desktop smoke run.
"""
import importlib.util
import unittest

from src.gui.layout import calculate_layout, normalized_region
from src.gui.viewport import DashboardViewport


class Region:
    def __init__(self, camera, dimensions=(0,1,0,1), active=True):
        self.camera, self.dimensions, self.active = camera, dimensions, active
    def getCamera(self): return self.camera
    def getDimensions(self): return self.dimensions
    def setDimensions(self, *values): self.dimensions = values
    def isActive(self): return self.active
    def setActive(self, value): self.active = value


class Window:
    width, height = 1280, 720
    def __init__(self, regions): self.regions = regions
    def getDisplayRegions(self): return tuple(self.regions)
    def getXSize(self): return self.width
    def getYSize(self): return self.height


@unittest.skipUnless(importlib.util.find_spec('panda3d'), 'Camera/lens/events require GUI .venv.')
class ViewportTests(unittest.TestCase):
    def setUp(self):
        from panda3d.core import NodePath, PerspectiveLens
        from src.gui.camera import BoardCameraController
        from src.gui.contracts import StaticBoardData, BasicTileKind
        self.root = NodePath('scene')
        self.camera = self.root.attachNewNode('main-camera')
        self.lens = PerspectiveLens()
        self.controller = BoardCameraController(self.camera, self.lens)
        data = StaticBoardData(1, 'viewport-test', 'rev', 4, 7,
                              tuple((BasicTileKind.FLOOR,) * 7 for _ in range(4)), ())
        self.controller.fit_board(data, 1280,720)
        self.region = Region(self.camera)
        self.ui = Region(self.root.attachNewNode('ui-camera'))
        self.shadow = Region(self.root.attachNewNode('shadow-camera'), (.1,.9,.2,.8))
        self.window = Window([self.region, self.ui, self.shadow])
        self.layouts, self.fits = [], []
        self.viewport = DashboardViewport(self.window, self.camera, self.controller,
                                          on_refit=self.fits.append, on_layout=self.layouts.append)
        self.addCleanup(self.root.removeNode)
        self.addCleanup(self.controller.dispose)
        self.addCleanup(self.viewport.dispose)

    def test_only_main_region_changes_and_no_duplication(self):
        expected = normalized_region(calculate_layout(1280,720).viewport,1280,720)
        self.assertEqual(self.region.dimensions, expected)
        self.assertEqual(self.ui.dimensions, (0,1,0,1))
        self.assertEqual(self.shadow.dimensions, (.1,.9,.2,.8))
        self.assertEqual(len(self.window.regions), 3)

    def test_resize_lens_and_envelope_after_showbase_aspect_adjustment(self):
        from direct.showbase.MessengerGlobal import messenger
        from src.gui.camera import project_point
        for width, height in ((1280,720),(1366,768),(1920,1080),(1024,768),(1024,720)):
            self.window.width, self.window.height = width,height
            self.lens.setAspectRatio(width/height)
            messenger.send('aspectRatioChanged')
            messenger.send('window-event', [self.window])
            layout = self.viewport.layout
            self.assertAlmostEqual(self.lens.getAspectRatio(), layout.viewport.width/layout.viewport.height, places=5)
            self.assertAlmostEqual(self.lens.getVfov(), 45, places=4)
            for corner in self.controller.current_fit.bounds.corners():
                x,y,depth = project_point(corner,self.controller.current_fit)
                self.assertLessEqual(max(abs(x),abs(y)), .740001)
                self.assertLess(self.lens.getNear(),depth)
                self.assertGreater(self.lens.getFar(),depth)
        self.assertTrue(self.fits)

    def test_same_resize_does_not_duplicate_layout_or_camera_handlers(self):
        from direct.showbase.MessengerGlobal import messenger
        count = len(self.layouts)
        listener = self.controller._listener
        for _ in range(20):
            messenger.send('window-event',[self.window])
        self.assertEqual(len(self.layouts),count)
        self.assertIs(self.controller._listener,listener)
        self.assertTrue(listener.isAccepting('window-event'))
        self.assertTrue(listener.isAccepting('aspectRatioChanged'))

    def test_minimized_fallback_and_recovery(self):
        previous = self.controller.current_fit
        self.window.width = self.window.height = 0
        self.assertFalse(self.viewport.refresh())
        self.assertIs(self.controller.current_fit,previous)
        self.window.width,self.window.height = 640,480
        self.viewport.refresh()
        self.assertFalse(self.region.active)
        self.assertFalse(self.viewport.layout.supported)
        self.window.width,self.window.height = 1024,720
        self.viewport.refresh()
        self.assertTrue(self.region.active)

    def test_cleanup_restores_dimensions_listener_and_foreign_handler(self):
        from direct.showbase.DirectObject import DirectObject
        from direct.showbase.MessengerGlobal import messenger
        other = DirectObject()
        observed=[]
        other.accept('window-event',lambda window:observed.append(window))
        self.addCleanup(other.ignoreAll)
        old_listener = self.controller._listener
        self.viewport.dispose()
        self.viewport.dispose()
        self.assertEqual(self.region.dimensions,(0,1,0,1))
        self.assertTrue(self.region.active)
        self.assertFalse(old_listener.isAccepting('window-event'))
        self.window.width = 1366
        messenger.send('window-event',[self.window])
        self.assertAlmostEqual(self.lens.getAspectRatio(),1366/720,places=5)
        self.assertEqual(observed,[self.window])
        self.assertFalse(self.camera.isEmpty())

    def test_wrong_or_ambiguous_region_rejected_before_binding(self):
        for regions in ([],[self.region,self.region]):
            with self.assertRaises(ValueError):
                DashboardViewport(Window(regions),self.camera,self.controller,
                                  on_refit=self.fits.append,on_layout=self.layouts.append)

    def test_provider_failure_restores_camera_and_region(self):
        self.viewport.dispose()
        def fail(layout): raise RuntimeError('HUD failed')
        with self.assertRaisesRegex(RuntimeError,'HUD failed'):
            DashboardViewport(self.window,self.camera,self.controller,
                              on_refit=self.fits.append,on_layout=fail)
        self.assertEqual(self.region.dimensions,(0,1,0,1))
        self.assertTrue(self.region.active)

    def test_shutdown_restore_does_not_refit_detached_light_roots(self):
        self.fits.clear()
        listener = self.controller._listener
        self.viewport.dispose(refit=False)
        self.assertEqual(self.fits,[])
        self.assertFalse(listener.isAccepting('window-event'))
        self.assertEqual(self.region.dimensions,(0,1,0,1))

    def test_dashboard_cleanup_after_host_detaches_scene(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from src.gui.dashboard_preview import DashboardPresentation
        from src.gui.hud import HudViewModel
        self.viewport.dispose()
        scene = self.root.attachNewNode('SceneRoot')
        refit = Mock()
        presentation = SimpleNamespace(camera=self.controller,_refit=refit)
        app = SimpleNamespace(pixel2d=self.root.attachNewNode('pixel2d'),
                              scene_root=scene, finalExitCallbacks=[],
                              presentation=presentation, win=self.window,cam=self.camera)
        dashboard = DashboardPresentation(app, HudViewModel())
        self.addCleanup(dashboard.dispose)
        refit.reset_mock()
        scene.removeNode()
        dashboard.dispose()
        refit.assert_not_called()
        self.assertTrue(dashboard.hud.root.isEmpty())
        self.assertEqual(app.finalExitCallbacks,[])


@unittest.skipUnless(importlib.util.find_spec('panda3d'), 'Dashboard composition requires GUI .venv.')
class DashboardLifecycleTests(unittest.TestCase):
    def test_loop_failure_cleans_dashboard_before_existing_presentation(self):
        from unittest.mock import patch, Mock
        from src.gui.dashboard_preview import main
        app, renderer, calls = Mock(), Mock(), []
        app.run.side_effect = RuntimeError('loop failed')
        app.dashboard.dispose.side_effect = lambda: calls.append('dashboard')
        renderer.dispose.side_effect = lambda: calls.append('renderer')
        app.destroy.side_effect = lambda: calls.append('host')
        with patch('src.gui.dashboard_preview.create_dashboard', return_value=(app, renderer)), \
             patch('src.gui.dashboard_preview.dispose_presentation',
                   side_effect=lambda host: calls.append('presentation')):
            with self.assertRaisesRegex(RuntimeError,'loop failed'):
                main([])
        self.assertEqual(calls,['dashboard','presentation','renderer','host'])

    def test_setup_failure_destroys_original_preview_resources(self):
        from unittest.mock import patch, Mock
        from src.gui.dashboard_preview import create_dashboard
        app, renderer = Mock(), Mock()
        with patch('src.gui.dashboard_preview.create_preview', return_value=(app,renderer)), \
             patch('src.gui.dashboard_preview.DashboardPresentation', side_effect=RuntimeError('setup')), \
             patch('src.gui.dashboard_preview.dispose_presentation') as cleanup:
            with self.assertRaisesRegex(RuntimeError,'setup'):
                create_dashboard()
        cleanup.assert_called_once_with(app)
        renderer.dispose.assert_called_once_with()
        app.destroy.assert_called_once_with()
