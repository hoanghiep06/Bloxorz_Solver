"""Pure ViewModel validation plus real DirectGUI scene-node checks (no window)."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from dataclasses import replace

from src.gui.hud import HudViewModel, UNKNOWN, metric_values
from src.gui.layout import calculate_layout


class HudDataTests(unittest.TestCase):
    def test_unknown_is_not_measured_zero(self):
        self.assertEqual(metric_values(HudViewModel()), (UNKNOWN,) * 5)
        self.assertEqual(metric_values(HudViewModel(move_count=0, search_time_ms=0,
                         expanded_nodes=0, solution_length=0, peak_python_memory_bytes=0)),
                         ('0', '0.00 ms', '0', '0', '0 B'))

    def test_unit_formatting(self):
        model = HudViewModel(search_time_ms=1250, peak_python_memory_bytes=1048576)
        self.assertEqual(metric_values(model)[1], '1.25 s')
        self.assertEqual(metric_values(model)[4], '1.00 MiB')
        self.assertEqual(metric_values(replace(model, peak_python_memory_bytes=2048))[4], '2.00 KiB')

    def test_invalid_data_rejected(self):
        for field in ('move_count', 'expanded_nodes', 'solution_length', 'peak_python_memory_bytes'):
            for bad in (-1, True, 1.5, '1'):
                with self.subTest(field=field, value=bad), self.assertRaises(ValueError):
                    HudViewModel(**{field: bad})
        for bad in (-1, True, float('nan'), float('inf'), '1'):
            with self.subTest(time=bad), self.assertRaises(ValueError):
                HudViewModel(search_time_ms=bad)
        for field in ('level_label', 'runtime_status'):
            for bad in ('', ' ', None, 1):
                with self.assertRaises(ValueError):
                    HudViewModel(**{field: bad})

    def test_import_is_engine_and_gameplay_independent(self):
        code = """
import sys
from src.gui.hud import HudViewModel, metric_values
assert metric_values(HudViewModel()) == ('—',) * 5
assert not any(n.split('.')[0] in ('panda3d','direct','pygame') or
    n.startswith(('src.core','src.solvers','src.gui.controller')) for n in sys.modules)
"""
        result = subprocess.run([sys.executable, '-S', '-B', '-c', code], capture_output=True,
                                text=True, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(importlib.util.find_spec('panda3d'), 'DirectGUI requires GUI .venv.')
class HudWidgetTests(unittest.TestCase):
    def setUp(self):
        from panda3d.core import NodePath
        from src.gui.hud import HudShell
        self.parent = NodePath('pixel2d-fixture')
        self.foreign = self.parent.attachNewNode('foreign')
        self.hud = HudShell(self.parent)
        self.addCleanup(self.parent.removeNode)
        self.addCleanup(self.hud.dispose)
        self.hud.apply_layout(calculate_layout(1280, 720))

    def test_surfaces_controls_and_disabled_gui_items(self):
        from direct.gui import DirectGuiGlobals as DGG
        self.assertEqual(set(self.hud.surfaces), {'controls', 'metrics'})
        self.assertEqual(set(self.hud.buttons), {'Exit', 'Restart', 'Guide',
            'BFS', 'DFS', 'IDS', 'UCS', 'Greedy', 'A*', 'Play', 'Step', 'View', 'Tutorial'})
        for control in (*self.hud.buttons.values(), self.hud.speed, self.hud.speed.component('thumb')):
            self.assertEqual(control['state'], DGG.DISABLED)
            self.assertFalse(control.guiItem.getActive())
            self.assertIsNone(control['command'])

    def test_model_updates_and_real_zero(self):
        self.assertEqual([label['text'] for label in self.hud.metric_values], [UNKNOWN] * 5)
        self.hud.update_view_model(HudViewModel(level_label='Example', runtime_status='READY',
                                               move_count=0, expanded_nodes=24))
        self.assertEqual(self.hud.level['text'], 'Example')
        self.assertEqual(self.hud.runtime['text'], 'READY')
        self.assertEqual(self.hud.metric_values[0]['text'], '0')
        self.assertEqual(self.hud.metric_values[2]['text'], '24')
        self.assertEqual(self.hud.metric_values[1]['text'], UNKNOWN)

    def test_ai_button_is_immediate_and_returns_after_guide_mode(self):
        button = self.hud.buttons['Guide'].border
        self.assertFalse(button.isHidden())
        self.hud.set_guide_mode(True)
        self.assertFalse(button.isHidden())
        self.hud.set_guide_mode(False)
        self.assertFalse(button.isHidden())
        self.hud.set_guide_visible(True)
        self.hud.set_guide_visible(False)
        self.assertFalse(button.isHidden())

    def test_resize_retains_widgets_and_labels_fit(self):
        identities = tuple(id(widget) for widget in self.hud._widgets)
        from panda3d.core import TextNode
        measure = TextNode('measure')
        for width, height in ((1280,720), (1366,768), (1920,1080), (1024,768), (1024,720)):
            self.hud.apply_layout(calculate_layout(width, height))
            self.assertEqual(identities, tuple(id(widget) for widget in self.hud._widgets))
            cell = (width - 80) / 5
            for label in self.hud.metric_labels:
                self.assertLess(measure.calcWidth(label['text']) * label['text_scale'][0], cell - 12)
            for name, button in self.hud.buttons.items():
                # Icon toolbar has no text; algorithm chips retain text-fit checks.
                text = button['text']
                if text:
                    self.assertLess(measure.calcWidth(text) * 16, button['frameSize'][1] - 8)
                else:
                    self.assertGreaterEqual(button['frameSize'][1], 44)

    def test_long_labels_elided_and_small_window_recovers(self):
        self.hud.update_view_model(HudViewModel(level_label='A very long level name ' * 10,
                                               runtime_status='A long status ' * 10,
                                               expanded_nodes=10**120))
        self.hud.apply_layout(calculate_layout(1024,720))
        self.assertTrue(self.hud.level['text'].endswith('…'))
        self.assertTrue(self.hud.metric_values[2]['text'].endswith('…'))
        self.hud.apply_layout(calculate_layout(640,480))
        self.assertFalse(self.hud.warning.isHidden())
        self.assertTrue(all(surface.isHidden() for surface in self.hud.surfaces.values()))
        self.hud.apply_layout(calculate_layout(1280,720))
        self.assertTrue(self.hud.warning.isHidden())

    def test_dispose_preserves_foreign_nodes(self):
        root = self.hud.root
        self.hud.dispose()
        self.hud.dispose()
        self.assertTrue(root.isEmpty())
        self.assertFalse(self.foreign.isEmpty())
        self.assertFalse(self.parent.isEmpty())
