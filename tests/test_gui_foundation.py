"""Foundation checks without opening a desktop window during test discovery."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


@unittest.skipUnless(
    importlib.util.find_spec("panda3d") is not None,
    "Panda3D is optional for the existing CLI; use the GUI virtual environment.",
)
class FoundationTests(unittest.TestCase):
    def test_import_does_not_create_a_host_window_or_import_game_logic(self):
        project_root = Path(__file__).resolve().parents[1]
        check = """
import builtins
import sys
from panda3d.core import GraphicsEngine, WindowProperties

engine = GraphicsEngine.getGlobalPtr()
assert engine.getNumWindows() == 0
properties_before = WindowProperties.getDefault()

from src.gui import app

assert engine.getNumWindows() == 0
assert not hasattr(builtins, 'base')
assert WindowProperties.getDefault() == properties_before
assert not any(
    name == 'src.core' or name.startswith('src.core.')
    or name == 'src.solvers' or name.startswith('src.solvers.')
    or name == 'pygame' or name.startswith('pygame.')
    for name in sys.modules
)
print('import-safe')
"""
        result = subprocess.run(
            [sys.executable, "-B", "-c", check],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "import-safe")

    def test_entry_point_cleans_up_if_main_loop_raises(self):
        from src.gui.app import main

        with patch("src.gui.app.BloxorzPreviewApp") as app_class:
            app = app_class.return_value
            app.run.side_effect = RuntimeError("loop failed")

            with self.assertRaisesRegex(RuntimeError, "loop failed"):
                main()

            app_class.assert_called_once_with()
            app.run.assert_called_once_with()
            app.destroy.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
