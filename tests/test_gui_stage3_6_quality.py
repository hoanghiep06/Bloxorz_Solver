"""Import/platform readiness, presentation findings and the dashboard title fix."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

from src.gui.camera import CameraConfig, camera_basis, fit_camera, project_point
from src.gui.hud import TEXT_PRIMARY, TEXT_SECONDARY
from src.gui.layout import calculate_layout, normalized_region
from tools.gui_stage3_6_smoke import SHAPES, SIZES, make_fixture


ROOT = Path(__file__).resolve().parents[1]
HAS_PANDA = importlib.util.find_spec('panda3d') is not None


class PureQualityTests(unittest.TestCase):
    def test_math_contract_adapter_and_tool_import_without_site_packages(self):
        code = """
import sys
from src.gui import contracts, render_adapter, geometry_math, layout, hud, camera
from tools import gui_stage3_6_smoke
assert not any(n.split('.')[0] in ('panda3d','direct','pygame') for n in sys.modules)
assert not any(n.startswith(('src.solvers','src.gui.controller')) for n in sys.modules)
"""
        result = subprocess.run([sys.executable,'-S','-B','-c',code],cwd=ROOT,
                                capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_fixed_camera_design_contains_shape_matrix_at_every_supported_viewport(self):
        import math
        config = CameraConfig()
        self.assertEqual((config.azimuth, config.elevation, config.padding), (30,45,.13))
        back,_,_,_ = camera_basis(config)
        self.assertAlmostEqual(math.degrees(math.asin(back[2])),45)
        for name in SHAPES:
            data=make_fixture(name)
            for width,height in SIZES:
                rect=calculate_layout(width,height).viewport
                fit=fit_camera(data,rect.width,rect.height)
                self.assertEqual(fit.vertical_fov,45)
                for corner in fit.bounds.corners():
                    x,y,depth=project_point(corner,fit)
                    self.assertLessEqual(max(abs(x),abs(y)),.740001)
                    self.assertLess(fit.near,depth)
                    self.assertGreater(fit.far,depth)

    def test_readable_secondary_text_on_white_surface(self):
        def luminance(color):
            linear=[c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in color[:3]]
            return sum(c*w for c,w in zip(linear,(.2126,.7152,.0722)))
        for color in (TEXT_PRIMARY,TEXT_SECONDARY):
            self.assertGreaterEqual(1.05/(luminance(color)+.05),4.5)

    def test_invalid_viewport_dimensions_have_explicit_errors(self):
        rect=calculate_layout(1280,720).viewport
        for width,height in ((0,720),(1280,0),(-1,720),(True,720),(1280,720.5)):
            with self.subTest(size=(width,height)),self.assertRaises(ValueError):
                normalized_region(rect,width,height)
            with self.assertRaises(ValueError):
                fit_camera(make_fixture('basic'),width,height)


@unittest.skipUnless(HAS_PANDA,'Engine import/title checks require GUI .venv.')
class EngineQualityTests(unittest.TestCase):
    def test_importing_all_gui_tests_and_entrypoints_opens_no_window(self):
        code="""
import builtins, unittest
from panda3d.core import GraphicsEngine
from src.gui import app, board_preview, dashboard_preview
suite=unittest.TestLoader().discover('tests',pattern='test_gui*.py')
assert suite.countTestCases()>0
assert GraphicsEngine.getGlobalPtr().getNumWindows()==0
assert not hasattr(builtins,'base')
"""
        result=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_dashboard_requests_specific_title_on_existing_window(self):
        from src.gui.dashboard_preview import create_dashboard
        app,renderer=Mock(),Mock()
        with patch('src.gui.dashboard_preview.create_preview',return_value=(app,renderer)) as create, \
             patch('src.gui.dashboard_preview.DashboardPresentation'):
            result=create_dashboard()
        self.assertEqual(result,(app,renderer))
        create.assert_called_once()
        app.win.requestProperties.assert_called_once()
        properties=app.win.requestProperties.call_args.args[0]
        self.assertEqual(properties.getTitle(),'Bloxorz Solver — 3D Preview')

    def test_title_request_failure_cleans_original_preview(self):
        from src.gui.dashboard_preview import create_dashboard
        app,renderer=Mock(),Mock()
        app.win.requestProperties.side_effect=RuntimeError('title request failed')
        with patch('src.gui.dashboard_preview.create_preview',return_value=(app,renderer)), \
             patch('src.gui.dashboard_preview.DashboardPresentation'), \
             patch('src.gui.dashboard_preview.dispose_presentation') as cleanup:
            with self.assertRaisesRegex(RuntimeError,'title request failed'):
                create_dashboard()
        cleanup.assert_called_once_with(app)
        renderer.dispose.assert_called_once_with()
        app.destroy.assert_called_once_with()
