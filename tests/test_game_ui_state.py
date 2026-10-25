"""Result-dialog resize and AI-panel/controller state regressions."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

HAS_PANDA = importlib.util.find_spec('panda3d') is not None
if HAS_PANDA:
    from test_gui_stage3_6_integration import SceneFixture
else:
    SceneFixture = unittest.TestCase


@unittest.skipUnless(HAS_PANDA, 'Panda3D required for game UI state tests.')
class GameUiStateTests(SceneFixture):
    def setUp(self):
        super().setUp()
        from src.gui.controller import GameController, LevelCatalog
        from src.gui.game_scene import GameScene
        from src.gui.profile import SaveData
        from src.gui.screens import UIFlow
        from gui_task_support import TaskManagerDouble
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app.render = self.host
        self.app.userExit = Mock()
        self.app.taskMgr = TaskManagerDouble()
        self.catalog = LevelCatalog(Path(__file__).resolve().parents[1] / 'levels')
        self.c = GameController(catalog=self.catalog, hud=self.app.dashboard.hud,
            prepare_scene=lambda data, snapshot: GameScene(self.app, data, snapshot))
        self.addCleanup(self.c.dispose)
        self.assertTrue(self.c.start())
        self.c.bind_hud()
        self.flow = UIFlow(self.app, self.c, self.catalog,
            SaveData(Path(self.temp.name) / 'save.json'), Mock(), Mock())
        self.addCleanup(self.flow.dispose)
        self.c._on_event = self.flow.on_game_event
        self.flow.show('game')
        self.screen = self.flow.screens['game']
        self.hud = self.app.dashboard.hud
        self.keys = {}
        self.c.bind_keys(lambda key, command, args=(): self.keys.update({key: (command, args)}))

    def labels(self):
        from direct.gui.DirectGui import DirectLabel
        return [str(widget['text']) for widget in self.screen._owned
                if isinstance(widget, DirectLabel)]

    def test_ai_button_is_immediate_on_level_entry_and_skips_intro_when_opened(self):
        with patch.object(self.flow, '_ensure_par'):
            for index in (0, 1, len(self.catalog) - 1):
                self.flow.start_level(index)
                self.assertTrue(self.flow.intro.active)
                self.assertFalse(self.hud.buttons['Guide'].border.isHidden())
                self.flow.toggle_guide()
                self.assertFalse(self.flow.intro.active)
                self.assertTrue(self.c.input_enabled)
                self.assertTrue(self.hud.guide_open)
                for name in ('BFS', 'DFS', 'IDS', 'UCS', 'Greedy', 'A*'):
                    self.assertFalse(self.hud.buttons[name].isHidden())

    def test_ai_button_stays_available_after_manual_move_and_restart(self):
        self.assertTrue(self.c.manual_move('R'))
        self.c.manager.advance(2)
        self.assertEqual(self.c.moves, 1)
        self.assertFalse(self.hud.buttons['Guide'].border.isHidden())
        self.c.restart_level()
        self.assertFalse(self.hud.buttons['Guide'].border.isHidden())

    def test_ai_button_returns_immediately_after_completed_replay(self):
        self.flow.toggle_guide()
        self.hud.buttons['BFS']['command']()
        self.hud.buttons['Play']['command']()
        for _ in range(100):
            if not self.c.manager.is_busy:
                break
            self.c.manager.advance(2)
        self.app.taskMgr.tick(deferred_only=True)
        self.assertIsNotNone(self.c.search)
        self.assertFalse(self.c.guide_active)
        self.assertFalse(self.hud.buttons['Guide'].border.isHidden())

    def test_immediate_solver_selection_clears_previous_result_dialog(self):
        for outcome in ('win', 'fail'):
            with self.subTest(outcome=outcome):
                self.c.phase = 'GOAL' if outcome == 'win' else 'FELL'
                self.screen.show_result() if outcome == 'win' else self.screen.show_fail()
                self.assertTrue(self.screen.result_visible)
                self.assertFalse(self.hud.buttons['Guide'].border.isHidden())
                self.flow.toggle_guide()
                self.hud.buttons['BFS']['command']()
                self.assertEqual(self.c.phase, 'READY')
                self.assertFalse(self.screen.result_visible)
                self.flow.toggle_guide()

    def buttons(self):
        from direct.gui.DirectGui import DirectButton
        return {str(widget['text']): widget for widget in self.screen._owned
                if isinstance(widget, DirectButton)}

    def resize(self, width, height):
        self.flow.size = (width, height)
        self.screen.resize()
        self.app.taskMgr.tick(deferred_only=True)

    def test_win_resize_retains_score_buttons_without_recording_again(self):
        self.c.moves = 7
        self.flow.save.par[self.catalog[0].level_id] = 7
        with patch.object(self.flow.save, 'record', wraps=self.flow.save.record) as record, \
             patch.object(self.flow.save, 'save', wraps=self.flow.save.save) as save:
            self.screen.show_result()
            for size in ((1100, 760), (800, 600), (1280, 720), (1920, 1080)):
                self.resize(*size)
                self.assertTrue(self.screen.result_visible)
                self.assertIn('Level Complete!', self.labels())
                self.assertIn('Moves 7     Par 7', self.labels())
                self.assertEqual(set(self.buttons()), {'Next', 'Retry', 'Levels'})
            record.assert_called_once_with(self.catalog[0].level_id, 7, 3)
            save.assert_called_once()

    def test_fail_resize_retains_dialog_and_its_actions(self):
        self.c.moves = 2
        with patch.object(self.flow.save, 'record') as record:
            self.screen.show_fail()
            for size in ((1100, 760), (1280, 720)):
                self.resize(*size)
                self.assertIn('Level Failed', self.labels())
                self.assertIn('Moves 2', self.labels())
                self.assertEqual(set(self.buttons()), {'Retry', 'Exit'})
            record.assert_not_called()
        self.buttons()['Retry']['command']()
        self.assertFalse(self.screen.result_visible)
        self.resize(1100, 760)
        self.assertFalse(self.screen._owned)
        self.assertEqual(self.c.moves, 0)

    def test_last_level_next_remains_disabled_after_resize(self):
        self.assertTrue(self.c.load_level(len(self.catalog) - 1))
        self.screen.show_result()
        self.resize(1100, 760)
        self.assertEqual(self.buttons()['Next']['state'], 'disabled')

    def test_guided_score_is_not_recomputed_on_resize(self):
        self.c.used_guide = True
        self.c.moves = 7
        with patch.object(self.flow.save, 'record', wraps=self.flow.save.record) as record:
            self.screen.show_result()
            self.c.used_guide = False
            self.resize(1100, 760)
            record.assert_called_once_with(self.catalog[0].level_id, 7, 1)
            self.assertEqual(self.flow.save.stars_for(self.catalog[0].level_id), 1)

    def test_repeated_result_resize_does_not_accumulate_widgets(self):
        from direct.gui.DirectGuiBase import DirectGuiWidget
        self.screen.show_fail()
        self.app.taskMgr.tick(deferred_only=True)
        baseline = len(DirectGuiWidget.guiDict)
        for _ in range(10):
            self.resize(1100, 760)
            self.resize(1280, 720)
            self.assertEqual(len(DirectGuiWidget.guiDict), baseline)

    def test_hide_dialog_then_resize_does_not_resurrect_it(self):
        self.screen.show_result()
        self.flow.show('levels')
        self.flow.show('game')
        self.resize(1100, 760)
        self.assertFalse(self.screen.result_visible)
        self.assertFalse(self.screen._owned)

    def test_closing_ai_panel_clears_selection_and_enter_p_do_nothing(self):
        self.flow.toggle_guide()
        self.hud.buttons['BFS']['command']()
        self.assertEqual(self.c.selected, 'BFS')
        self.flow.toggle_guide()
        self.assertFalse(self.hud.guide_open)
        self.assertIsNone(self.c.selected)
        with patch.object(self.c, 'run_solver') as run:
            for key in ('enter', 'p'):
                command, args = self.keys[key]
                command(*args)
            run.assert_not_called()
        self.assertFalse(self.c.guide_active)
        self.assertFalse(self.hud.buttons['Restart'].border.isHidden())

    def test_closing_selected_panel_preserves_manual_progress(self):
        self.flow.toggle_guide()
        self.hud.buttons['BFS']['command']()
        self.assertTrue(self.c.manual_move('R'))
        self.c.manager.advance(2)
        old = (self.c.state, self.c.moves, self.c.session_id)
        self.flow.toggle_guide()
        self.assertEqual((self.c.state, self.c.moves, self.c.session_id), old)
        self.assertIsNone(self.c.selected)
        self.flow.toggle_guide()
        self.assertIsNone(self.c.selected)
        self.hud.buttons['BFS']['command']()
        self.hud.buttons['Step']['command']()
        self.c.manager.advance(2)
        self.assertTrue(self.c.guide_active)
        self.assertEqual(self.c.moves, 1)

    def test_closing_panel_during_pending_solve_cancels_the_job(self):
        self.flow.toggle_guide()
        self.hud.buttons['BFS']['command']()
        self.c._task_mgr = self.app.taskMgr
        self.hud.buttons['Play']['command']()
        self.assertEqual(self.c.phase, 'SOLVING')
        self.flow.toggle_guide()
        self.assertEqual(self.c.phase, 'READY')
        self.assertIsNone(self.c.selected)
        self.assertIsNone(self.c._deferred)
        self.assertFalse(self.c.guide_active)

    def test_closing_panel_during_manual_roll_does_not_cancel_the_move(self):
        self.flow.toggle_guide()
        self.hud.buttons['BFS']['command']()
        self.assertTrue(self.c.manual_move('R'))
        self.c.manager.advance(.1)
        session = self.c.session_id
        self.flow.toggle_guide()
        self.assertTrue(self.c.manager.is_busy)
        self.c.manager.advance(2)
        self.assertEqual(self.c.moves, 1)
        self.assertEqual(self.c.session_id, session)
        self.assertIsNone(self.c.selected)


if __name__ == '__main__':
    unittest.main()
