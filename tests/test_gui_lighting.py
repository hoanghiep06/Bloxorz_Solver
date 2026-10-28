"""Presentation ownership/state tests; onscreen evidence is recorded separately."""

import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch


HAS_PANDA = importlib.util.find_spec('panda3d') is not None
if HAS_PANDA:
    from panda3d.core import (
        AmbientLight, AntialiasAttrib, DirectionalLight, GeomVertexReader,
        LightAttrib, Material, NodePath, ShaderAttrib,
    )
    from src.gui.camera import fit_camera
    from src.gui.contracts import BasicTileKind, StaticBoardData
    from src.gui.mesh_factory import make_block_mesh
    from src.gui.scene_lighting import SceneLightingController
    from src.gui.scene_style import SHADOW_MASK, SceneStyle


@unittest.skipUnless(HAS_PANDA, 'Panda3D presentation state tests require GUI .venv.')
class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.host = NodePath('host')
        self.scene = self.host.attachNewNode('SceneRoot')
        self.static = self.scene.attachNewNode('StaticBoardRoot')
        self.block = self.scene.attachNewNode('BlockRoot')
        self.camera = self.host.attachNewNode('camera')
        data = StaticBoardData(1, 'presentation', 'fixture', 4, 7,
                               tuple((BasicTileKind.FLOOR,) * 7 for _ in range(4)), ())
        self.fit = fit_camera(data, 1280, 720)
        self.addCleanup(self.host.removeNode)

    def lighting(self, **kwargs):
        light = SceneLightingController(self.scene, self.fit, **kwargs)
        self.addCleanup(light.dispose)
        return light

    def style(self, **kwargs):
        style = SceneStyle(self.static, self.block, self.camera, **kwargs)
        style.update_background(self.fit)
        self.addCleanup(style.dispose)
        return style

    def test_light_types_subtree_and_screen_relative_source(self):
        light = self.lighting()
        self.assertIsInstance(light.ambient.node(), AmbientLight)
        self.assertIsInstance(light.key.node(), DirectionalLight)
        self.assertIsInstance(light.fill.node(), DirectionalLight)
        self.assertTrue(self.scene.hasLight(light.key))
        self.assertFalse(self.camera.hasLight(light.key))
        delta = light.key.getPos(self.scene)
        self.assertLess(sum(delta[i]*self.fit.right[i] for i in range(3)), 0)
        self.assertGreater(sum((delta[i]-self.fit.target[i])*self.fit.up[i] for i in range(3)), 0)

    def test_repeated_refit_and_shadow_toggle_do_not_duplicate_nodes(self):
        light = self.lighting()
        count = self.scene.findAllMatches('**').getNumPaths()
        for _ in range(20):
            light.fit_bounds(self.fit)
            light.set_shadows(False)
        self.assertEqual(self.scene.findAllMatches('**').getNumPaths(), count)
        light.dispose()
        other = self.lighting()
        self.assertEqual(self.scene.findAllMatches('**').getNumPaths(), count)
        self.assertTrue(self.scene.hasLight(other.ambient))

    def test_dispose_preserves_foreign_lights_nodes_and_render_attributes(self):
        foreign = self.scene.attachNewNode(AmbientLight('ForeignLight'))
        self.scene.setLight(foreign)
        sibling = self.scene.attachNewNode('ForeignGeometry')
        light = self.lighting()
        light.dispose()
        light.dispose()
        self.assertTrue(self.scene.hasLight(foreign))
        self.assertFalse(sibling.isEmpty())
        self.assertTrue(self.scene.find('PresentationLights').isEmpty())
        self.assertEqual(self.scene.getParent(), self.host)

    def test_basic_profile_needs_no_gsg_shadow_buffer_or_shader(self):
        light = self.lighting()
        self.assertEqual(light.shadow_status, 'DISABLED')
        self.assertFalse(light.key.node().isShadowCaster())
        self.assertFalse(self.scene.hasAttrib(ShaderAttrib))
        self.assertFalse(light.set_shadows(True, gsg=None))
        self.assertEqual(light.shadow_status, 'UNAVAILABLE')
        self.assertFalse(light.key.node().isShadowCaster())

    def test_capability_failure_keeps_basic_lighting(self):
        light = self.lighting()
        gsg = Mock()
        gsg.getSupportsBasicShaders.return_value = False
        self.assertFalse(light.set_shadows(True, gsg=gsg))
        self.assertTrue(self.scene.hasLight(light.key))
        self.assertEqual(light.shadow_status, 'UNAVAILABLE')

    def test_shadow_toggle_preserves_geometry_vertex_colors_and_shader_state(self):
        node = make_block_mesh()
        self.block.attachNewNode(node)
        buffer = bytes(node.getGeom(0).getVertexData().getArray(0).getHandle().getData())
        before = hashlib.sha256(buffer).hexdigest()
        geometry = self.block.node()
        gsg = Mock()
        gsg.getSupportsBasicShaders.return_value = True
        gsg.getSupportsDepthTexture.return_value = True
        light = self.lighting()
        for enabled in (True, False, True, False):
            light.set_shadows(enabled, gsg=gsg)
            self.assertEqual(light.key.node().isShadowCaster(), enabled)
        after = bytes(node.getGeom(0).getVertexData().getArray(0).getHandle().getData())
        self.assertEqual(before, hashlib.sha256(after).hexdigest())
        self.assertEqual(self.block.node(), geometry)
        self.assertFalse(self.scene.hasAttrib(ShaderAttrib))

    def test_shadow_lens_contains_scene_bounds_and_has_safe_clipping(self):
        from panda3d.core import Point2, Point3
        light = self.lighting()
        lens = light.key.node().getLens()
        for corner in self.fit.bounds.corners():
            point = light.key.getRelativePoint(self.scene, Point3(*corner))
            projected = Point2()
            self.assertTrue(lens.project(point, projected))
            self.assertLess(abs(projected.x), 1)
            self.assertLess(abs(projected.y), 1)
            self.assertLess(lens.getNear(), point.y)
            self.assertGreater(lens.getFar(), point.y)

    def test_matte_material_leaves_diffuse_ambient_vertex_sources_unset(self):
        style = self.style()
        for root in (self.static, self.block):
            material = root.getMaterial()
            self.assertFalse(material.hasDiffuse())
            self.assertFalse(material.hasAmbient())
            self.assertLess(max(material.getSpecular().xyz), .1)
            self.assertFalse(root.hasColor())
        style.dispose()
        self.assertFalse(self.static.hasMaterial())

    def test_style_cleanup_restores_previous_material_and_aa_without_clearing_lights(self):
        previous = Material('ForeignMaterial')
        self.static.setMaterial(previous)
        self.static.setAntialias(AntialiasAttrib.MNone)
        before = self.static.getState()
        light = self.lighting()
        style = self.style(multisamples=4)
        style.dispose()
        style.dispose()
        self.assertEqual(self.static.getState(), before)
        self.assertTrue(self.scene.hasLight(light.ambient))

    def test_fallback_gradient_is_unlit_behind_bounds_without_ground_plane(self):
        # Current design prefers day/night images. Exercise the fallback
        # explicitly, independent of whether the repository assets exist.
        with patch('src.gui.scene_style._find_image', return_value=None):
            style = self.style()
        gradient = self.camera.find('PresentationGradient')
        self.assertFalse(gradient.isEmpty())
        self.assertFalse(gradient.getDepthWrite())
        self.assertFalse(gradient.getDepthTest())
        self.assertEqual(gradient.getBinName(), 'background')
        self.assertTrue(gradient.isHidden(SHADOW_MASK))
        self.assertEqual(self.static.getNumChildren(), 0)
        self.assertEqual(self.block.getNumChildren(), 0)
        vertices = GeomVertexReader(gradient.node().getGeom(0).getVertexData(), 'color')
        colors = [tuple(vertices.getData4f()) for _ in range(4)]
        self.assertNotEqual(colors[0], colors[2])
        self.assertAlmostEqual(colors[0][0], 231/255, places=6)
        self.assertAlmostEqual(colors[2][0], 241/255, places=6)
        max_depth = max(sum((p[i]-self.fit.position[i])*self.fit.forward[i] for i in range(3))
                        for p in self.fit.bounds.corners())
        self.assertGreater(gradient.getY()+1, max_depth)
        self.assertLess(gradient.getY()+1, self.fit.far)
        style.dispose()
        self.assertTrue(self.camera.find('PresentationGradient').isEmpty())

    def test_image_backdrop_keeps_unlit_depth_and_shadow_contract(self):
        style = self.style()
        backdrop = self.camera.find('PresentationBackdrop')
        self.assertFalse(backdrop.isEmpty())
        self.assertTrue(backdrop.hasTexture())
        self.assertFalse(backdrop.getDepthWrite())
        self.assertFalse(backdrop.getDepthTest())
        self.assertEqual(backdrop.getBinName(), 'background')
        self.assertTrue(backdrop.isHidden(SHADOW_MASK))
        style.dispose()
        self.assertTrue(backdrop.isEmpty() or self.camera.find('PresentationBackdrop').isEmpty())

    def test_aa_state_depends_on_framebuffer_readback(self):
        for samples, enabled, status in ((0, True, 'UNAVAILABLE'), (4, True, 'MSAA_4X'),
                                          (8, False, 'DISABLED')):
            style = self.style(multisamples=samples, antialiasing=enabled)
            self.assertEqual(style.aa_status, status)
            mode = self.static.getAttrib(AntialiasAttrib).getMode()
            expected = AntialiasAttrib.MMultisample if samples > 1 and enabled else AntialiasAttrib.MNone
            self.assertEqual(mode, expected)
            style.dispose()

    def test_import_has_no_window_or_core_side_effect(self):
        code = """
import sys
from panda3d.core import GraphicsEngine
import src.gui.scene_style
import src.gui.scene_lighting
assert GraphicsEngine.getGlobalPtr().getNumWindows() == 0
assert not any(n.startswith('src.core') or n.startswith('src.solvers')
               or n.split('.')[0] == 'pygame' for n in sys.modules)
"""
        result = subprocess.run([sys.executable, '-B', '-c', code],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_main_cleans_presentation_then_renderer_then_host(self):
        from src.gui.board_preview import main
        order = []
        app, renderer = Mock(), Mock()
        app.run.side_effect = RuntimeError('loop')
        renderer.dispose.side_effect = lambda: order.append('renderer')
        app.destroy.side_effect = lambda: order.append('host')
        with patch('src.gui.board_preview.create_preview', return_value=(app, renderer)) as create, \
             patch('src.gui.board_preview.dispose_presentation', side_effect=lambda app: order.append('presentation')):
            with self.assertRaises(RuntimeError):
                main(['--pose', 'VERTICAL', '--shadows', '--no-aa'])
        self.assertEqual(order, ['presentation', 'renderer', 'host'])
        self.assertTrue(create.call_args.kwargs['shadows'])
        self.assertFalse(create.call_args.kwargs['antialiasing'])

    def test_partial_presentation_setup_failure_removes_allocated_style_and_nodes(self):
        from panda3d.core import PerspectiveLens
        from src.gui.board_preview import PreviewPresentation
        from types import SimpleNamespace
        from src.gui.contracts import BasicTileKind, StaticBoardData
        window = Mock()
        window.getXSize.return_value = 1280
        window.getYSize.return_value = 720
        window.getFbProperties.return_value.getMultisamples.return_value = 4
        app = SimpleNamespace(camera=self.camera, camLens=PerspectiveLens(), win=window,
                              scene_root=self.scene, static_board_root=self.static,
                              block_root=self.block, finalExitCallbacks=[])
        data = StaticBoardData(1, 'fixture', 'setup-failure', 1, 1, ((BasicTileKind.FLOOR,),), ())
        before = self.static.getState()
        with patch('src.gui.board_preview.SceneLightingController', side_effect=RuntimeError('setup failed')):
            with self.assertRaisesRegex(RuntimeError, 'setup failed'):
                PreviewPresentation(app, data)
        self.assertEqual(self.static.getState(), before)
        self.assertTrue(self.camera.find('PresentationGradient').isEmpty())
        self.assertEqual(app.finalExitCallbacks, [])


if __name__ == '__main__':
    unittest.main()
