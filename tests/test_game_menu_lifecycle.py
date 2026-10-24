"""Menu rebuilds and delayed widget retirement balance DirectGUI registrations."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

HAS_PANDA=importlib.util.find_spec('panda3d') is not None
if HAS_PANDA:
    from test_gui_stage3_6_integration import SceneFixture
else:
    SceneFixture=unittest.TestCase

@unittest.skipUnless(HAS_PANDA,'DirectGUI required for menu lifecycle tests.')
class GameMenuTests(SceneFixture):
    def setUp(self):
        super().setUp()
        from src.gui.controller import LevelCatalog
        from src.gui.profile import SaveData
        from src.gui.screens import UIFlow
        from gui_task_support import TaskManagerDouble
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.app.render=self.host
        self.app.userExit=Mock()
        self.app.taskMgr=TaskManagerDouble()
        self.before=self.counts()
        self.c=Mock(level_index=0,guide_active=False,manager=None,phase='READY')
        self.flow=UIFlow(self.app,self.c,LevelCatalog(Path(__file__).resolve().parents[1]/'levels'),
                         SaveData(Path(self.temp.name)/'save.json'),Mock(),Mock())
        self.addCleanup(self.flow.dispose)
    def counts(self):
        from direct.gui.DirectGuiBase import DirectGuiWidget
        from direct.showbase.MessengerGlobal import messenger
        return (len(DirectGuiWidget.guiDict),
                sum(len(messenger.whoAccepts(e) or {}) for e in messenger.getEvents()))
    def test_twenty_menu_cycles_do_not_accumulate_widgets_or_listeners(self):
        self.flow.show('settings');self.flow.show('main')
        baseline=self.counts()
        for _ in range(20):
            self.flow.show('settings');self.flow.show('main')
            self.app.taskMgr.tick(deferred_only=True)
            self.assertEqual(self.counts(),baseline)
        self.flow.dispose()
        self.assertEqual(self.counts(),self.before)
    def test_dispose_reclaims_widgets_waiting_for_deferred_retirement(self):
        screen=self.flow.screens['main'];screen.show()
        screen.release_later()
        self.assertTrue(self.flow._retired)
        self.flow.dispose()
        self.assertEqual(self.counts(),self.before)
        self.app.taskMgr.tick(deferred_only=True)
        self.assertEqual(self.counts(),self.before)
    def test_theme_rebuilds_release_old_slider_callbacks(self):
        self.flow.show('settings')
        screen=self.flow.screens['settings'];baseline=self.counts()
        for theme in ('dark','light')*5:
            screen._set_theme(theme)
            self.app.taskMgr.tick(deferred_only=True)
            self.assertEqual(self.counts(),baseline)
        self.flow.dispose();self.assertEqual(self.counts(),self.before)
    def test_all_production_levels_pass_full_capability_validation(self):
        self.assertTrue(all(self.flow.is_supported(index) for index in range(len(self.flow.catalog))))
    def test_mouse_click_over_widget_does_not_move_board(self):
        self.flow.name='game'
        self.flow.save.settings.control_mode='mouse'
        self.c.manager=Mock(is_busy=False)
        self.app.mouseWatcherNode=Mock()
        self.app.mouseWatcherNode.getOverRegion.return_value.getName.return_value=(
            self.app.dashboard.hud.buttons['Exit'].guiId)
        with patch('src.gui.screens.pick_action') as pick:
            self.flow._click()
            pick.assert_not_called()
        self.c.manual_move.assert_not_called()
    def test_mouse_click_over_scene_reaches_controller(self):
        self.flow.name='game'
        self.flow.save.settings.control_mode='mouse'
        self.c.manager=Mock(is_busy=False)
        self.app.mouseWatcherNode=Mock()
        self.app.mouseWatcherNode.getOverRegion.return_value=None
        with patch('src.gui.screens.pick_action',return_value='R'):
            self.flow._click()
        self.c.manual_move.assert_called_once_with('R')

if __name__=='__main__':unittest.main()
