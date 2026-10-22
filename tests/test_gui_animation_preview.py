"""Composition/failure tests, no native window; real smoke has its own harness."""
from contextlib import redirect_stderr
import io
import importlib.util
import unittest
from unittest.mock import Mock, patch
HAS_PANDA=importlib.util.find_spec('panda3d') is not None
if HAS_PANDA:
    from src.gui import animation_preview as preview
    from src.gui.animation_fixtures import get_animation_fixture


@unittest.skipUnless(HAS_PANDA,'Panda3D not installed')
class AnimationPreviewTests(unittest.TestCase):
    def test_bad_scenario_and_speed_reject_before_window(self):
        with patch.object(preview,'BloxorzPreviewApp') as host:
            for kwargs in ({'scenario':'bad'},{'speed':0},{'speed':float('nan')}):
                with self.assertRaises(ValueError):preview.create_animation_preview(**kwargs)
            host.assert_not_called()

    def test_cli_rejects_invalid_rate_before_factory(self):
        with patch.object(preview,'create_animation_preview') as factory, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:preview.main(['--speed','nan'])
            self.assertEqual(caught.exception.code,2);factory.assert_not_called()

    def test_one_host_and_fixture_inputs_not_core_calls(self):
        app=Mock();app.finalExitCallbacks=[]
        with patch.object(preview,'BloxorzPreviewApp',return_value=app) as host, \
             patch.object(preview,'AnimatedSurfaceLayer'), patch.object(preview,'AdvancedSceneRenderer'), \
             patch.object(preview,'AdvancedPreviewPresentation'), patch.object(preview,'DashboardPresentation') as hud, \
             patch.object(preview,'AnimationManager') as manager,patch.object(preview,'AnimationDemoDriver'):
            result=preview.create_animation_preview('combined')
            host.assert_called_once_with();self.assertIs(result[0],app)
            self.assertEqual(manager.call_args.args[2],get_animation_fixture().initial)
            self.assertIn('ANIMATION DEMO DATA',hud.call_args.args[1].level_label)
            self.assertIsNone(hud.call_args.args[1].move_count)
            self.assertEqual(len(app.finalExitCallbacks),1)

    def test_creation_failure_cleans_renderer_surface_host(self):
        app=Mock();app.finalExitCallbacks=[]
        with patch.object(preview,'BloxorzPreviewApp',return_value=app), \
             patch.object(preview,'AnimatedSurfaceLayer') as layer,patch.object(preview,'AdvancedSceneRenderer') as renderer, \
             patch.object(preview,'AdvancedPreviewPresentation',side_effect=RuntimeError('fail')):
            with self.assertRaises(RuntimeError):preview.create_animation_preview()
            renderer.return_value.dispose.assert_called_once()
            layer.return_value.dispose.assert_called_once()
            app.destroy.assert_called_once()

    def test_driver_owns_only_one_task_and_stops_idempotently(self):
        app=Mock();manager=Mock();fixture=get_animation_fixture('basic-roll')
        driver=preview.AnimationDemoDriver(app,manager,fixture)
        driver.dispose();driver.dispose()
        app.taskMgr.add.assert_called_once();app.taskMgr.remove.assert_called_once()

    def test_cleanup_continues_if_manager_dispose_raises(self):
        app=Mock();app.finalExitCallbacks=[];manager=Mock();renderer=Mock()
        manager.dispose.side_effect=RuntimeError('fail')
        with patch.object(preview,'dispose_presentation') as presentation:
            with self.assertRaises(RuntimeError):preview.dispose_animation_preview(app,renderer,manager)
            presentation.assert_called_once_with(app)
            renderer.dispose.assert_called_once();app.destroy.assert_called_once()
            app.bufferViewer.ignoreAll.assert_called_once()

    def test_autoplay_driver_submits_only_its_finite_fixture(self):
        app=Mock();manager=Mock();manager.is_busy=False
        fixture=get_animation_fixture('basic-roll')
        driver=preview.AnimationDemoDriver(app,manager,fixture)
        clock=Mock();clock.getDt.return_value=.6
        with patch.object(preview,'ClockObject') as clocks:
            clocks.getGlobalClock.return_value=clock
            driver._update(Mock());driver._update(Mock())
        manager.submit.assert_called_once_with(fixture.requests[0])
        self.assertEqual(driver.index,1)
        driver.dispose()
