"""Repeated operations across renderer, presentation and Dashboard ownership."""
from dataclasses import replace
import unittest
from unittest.mock import patch

from src.gui.contracts import BasicOrientation
from tools.gui_stage3_6_smoke import make_fixture, make_snapshot
from test_gui_stage3_6_integration import HAS_PANDA, SceneFixture


@unittest.skipUnless(HAS_PANDA, 'Panda3D stability requires GUI .venv; no window is opened.')
class StabilityTests(SceneFixture):
    def counts(self):
        from direct.showbase.MessengerGlobal import messenger
        app = self.app
        return (self.host.findAllMatches('**').getNumPaths(), len(app.dashboard.hud._widgets),
                len(app.win.regions), len(app.finalExitCallbacks),
                len(messenger.whoAccepts('window-event') or {}),
                len(messenger.whoAccepts('aspectRatioChanged') or {}),
                sum(len(messenger.whoAccepts(e) or {}) for e in messenger.getEvents()))

    def test_500_snapshots_keep_block_board_buffers_camera_and_data_stable(self):
        from panda3d.core import Quat, Vec3
        from src.gui.geometry_math import block_pose
        camera = self.app.presentation.camera
        transform = self.app.camera.getTransform()
        content = self.app.static_board_root.find('BasicBoardContent').node()
        block = self.app.block_root.find('MainBlockVisual')
        prototypes = (self.renderer._floor_mesh, self.renderer._goal_mesh, self.renderer._block_mesh)
        before_buffers = [bytes(node.getGeom(0).getVertexData().getArray(0).getHandle().getData())
                          for node in prototypes]
        counts = self.counts()
        data_hash = hash(self.data)
        with patch.object(camera, 'fit_board', side_effect=AssertionError('snapshot camera refit')):
            for i in range(500):
                pose = tuple(BasicOrientation)[i % 3]
                snapshot = make_snapshot(self.data, pose, revision=i + 1)
                self.renderer.show_snapshot(snapshot)
                self.assertEqual(self.app.block_root.find('MainBlockVisual'), block)
                canonical = block_pose(*snapshot.anchor_cell, pose, rows=self.data.rows, cols=self.data.cols)
                quat = Quat(); quat.setFromAxisAngle(canonical.angle_degrees, Vec3(*canonical.rotation_axis))
                self.assertTrue(block.getQuat().almostEqual(quat, 1e-6))
                self.assertEqual(tuple(block.getPos()), canonical.center)
        self.assertEqual(self.counts(), counts)
        self.assertEqual(self.app.static_board_root.find('BasicBoardContent').node(), content)
        self.assertEqual(self.app.camera.getTransform(), transform)
        self.assertEqual(hash(self.data), data_hash)
        self.assertEqual(before_buffers, [bytes(node.getGeom(0).getVertexData().getArray(0).getHandle().getData())
                                         for node in prototypes])

    def test_100_reloads_preserve_foreign_nodes_and_replace_only_owned_tiles(self):
        static = self.app.static_board_root
        foreign = static.attachNewNode('ForeignOwnedByHost')
        self.app.block_root.attachNewNode('ForeignBlockRootChild')
        for i in range(100):
            data = replace(make_fixture(('wide', 'tall', 'square', 'sparse', 'tiny')[i % 5]),
                           board_revision=f'reload-{i}')
            old = static.find('BasicBoardContent')
            self.renderer.load_board(data)
            self.assertFalse(old.hasParent())
            self.assertEqual(static.getNumChildren(), 2)
            self.renderer.show_snapshot(make_snapshot(data))
            content = static.find('BasicBoardContent')
            self.renderer.load_board(data)
            self.assertEqual(static.find('BasicBoardContent'), content)
            self.assertEqual(self.app.block_root.getNumChildren(), 2)
            expected = sum(kind.value != 'VOID' for row in data.tiles for kind in row)
            self.assertEqual(content.getNumChildren(), expected)
            self.assertEqual(foreign.getParent(), static)
        before = static.find('BasicBoardContent').node()
        with self.assertRaisesRegex(ValueError, 'goal on VOID'):
            self.renderer.load_board(replace(make_fixture('sparse'), goal_cells=((0, 0),)))
        self.assertEqual(static.find('BasicBoardContent').node(), before)

    def test_140_resize_events_keep_widgets_regions_listeners_and_lens_stable(self):
        from direct.showbase.MessengerGlobal import messenger
        sizes = ((1280,720),(1024,720),(1920,1080),(1366,768),(1024,768),(640,480),(1280,720))
        counts = self.counts()
        listener = self.app.presentation.camera._listener
        identities = tuple(id(w) for w in self.app.dashboard.hud._widgets)
        for _ in range(20):
            for width,height in sizes:
                self.app.win.width,self.app.win.height = width,height
                self.app.camLens.setAspectRatio(width/height)
                messenger.send('aspectRatioChanged')
                messenger.send('window-event',[self.app.win])
                self.assertEqual(self.counts(),counts)
                self.assertIs(self.app.presentation.camera._listener,listener)
                self.assertEqual(tuple(id(w) for w in self.app.dashboard.hud._widgets),identities)
                layout = self.app.dashboard.viewport.layout
                if layout.supported:
                    self.assertAlmostEqual(self.app.camLens.getAspectRatio(),layout.viewport.width/layout.viewport.height,places=5)
                else:
                    self.assertFalse(self.app.win.regions[0].active)
        previous = self.app.presentation.camera.current_fit
        self.app.win.width=self.app.win.height=0
        messenger.send('window-event',[self.app.win])
        self.assertIs(self.app.presentation.camera.current_fit,previous)

    def test_40_dashboard_recreations_restore_preview_and_balance_resources(self):
        from src.gui.dashboard_preview import DashboardPresentation
        from src.gui.hud import HudViewModel
        from direct.showbase.MessengerGlobal import messenger
        counts = self.counts()
        for _ in range(40):
            old = self.app.dashboard
            listener = self.app.presentation.camera._listener
            old.dispose();old.dispose()
            self.assertEqual(self.app.win.regions[0].dimensions,(0,1,0,1))
            self.assertTrue(old.hud.root.isEmpty())
            self.assertEqual(messenger.getAllAccepting(listener),[])
            self.assertAlmostEqual(self.app.camLens.getAspectRatio(),1280/720,places=5)
            self.app.dashboard = DashboardPresentation(self.app,HudViewModel())
            self.assertEqual(self.counts(),counts)
        self.addCleanup(self.app.dashboard.dispose)

    def test_partial_hud_failure_releases_widgets_and_subscriptions(self):
        from src.gui.hud import HudShell
        before = self.counts()
        original = HudShell._label
        def fail_at_solver(shell,parent,text,*args,**kwargs):
            if text == 'AI SOLVERS':
                raise RuntimeError('injected partial HUD failure')
            return original(shell,parent,text,*args,**kwargs)
        with patch.object(HudShell,'_label',fail_at_solver):
            with self.assertRaisesRegex(RuntimeError,'partial HUD'):
                HudShell(self.app.pixel2d)
        self.assertEqual(self.counts(),before)
        self.assertEqual(self.app.pixel2d.findAllMatches('DashboardHUD').getNumPaths(),1)

    def test_partial_viewport_failure_keeps_existing_preview_alive(self):
        from src.gui.dashboard_preview import DashboardPresentation
        from src.gui.hud import HudViewModel
        self.app.dashboard.dispose()
        before = self.host.findAllMatches('**').getNumPaths()
        callback_count = len(self.app.finalExitCallbacks)
        with patch('src.gui.dashboard_preview.DashboardViewport',side_effect=RuntimeError('viewport failed')):
            with self.assertRaisesRegex(RuntimeError,'viewport failed'):
                DashboardPresentation(self.app,HudViewModel())
        self.assertEqual(self.host.findAllMatches('**').getNumPaths(),before)
        self.assertEqual(len(self.app.finalExitCallbacks),callback_count)
        self.assertFalse(self.app.scene_root.isEmpty())
        self.assertTrue(self.app.pixel2d.find('DashboardHUD').isEmpty())
