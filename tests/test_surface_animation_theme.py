"""Static and animated tile colors must follow the same current theme."""
import unittest

from gui_animation_support import AnimationSceneCase, HAS_PANDA
from src.gui.animation_contracts import (
    AnimationRequest, AnimationKind, AnimationEvent, EventKind, TerminalVisualOutcome,
)


@unittest.skipUnless(HAS_PANDA, 'Panda3D required.')
class SurfaceAnimationThemeTests(AnimationSceneCase):
    def setUp(self):
        from src.gui import scene_style
        self.original_theme = scene_style.TILE_THEME
        super().setUp()

    def tearDown(self):
        from src.gui.scene_style import apply_tile_theme
        if self.root is not None:
            apply_tile_theme(self.root, self.original_theme)
        super().tearDown()

    @staticmethod
    def colors(node):
        from panda3d.core import GeomVertexReader
        result = set()
        for path in node.findAllMatches('**/+GeomNode'):
            if path.isHidden():
                continue
            for geom in path.node().getGeoms():
                reader = GeomVertexReader(geom.getVertexData(), 'color')
                while not reader.isAtEnd():
                    result.add(tuple(round(v, 4) for v in reader.getData4f()))
        return result

    @staticmethod
    def color(theme, key):
        from src.gui.advanced_mesh_factory import PALETTES
        return tuple(round(v, 4) for v in PALETTES[theme][key])

    def test_bridge_static_and_animation_use_same_palette_in_both_themes(self):
        from src.gui.scene_style import apply_tile_theme
        for theme in ('light', 'dark'):
            self.build('bridge')
            apply_tile_theme(self.root, theme)
            request = self.fixture.requests[0]
            self.manager.submit(request)
            self.manager.advance(request.duration * .5)
            animated = self.colors(self.layer._bridges['bridge-main'])
            self.assertIn(self.color(theme, 'BRIDGE_TOP'), animated)
            self.assertNotIn(self.color('dark' if theme == 'light' else 'light', 'BRIDGE_TOP'), animated)
            self.manager.advance(request.duration)
            self.assertEqual(animated, self.colors(self.renderer._bridges['bridge-main']))

    def test_fragile_and_all_switch_types_keep_the_current_theme(self):
        from src.gui.scene_style import apply_tile_theme
        for theme in ('light', 'dark'):
            for scenario in ('fragile', 'switches'):
                with self.subTest(theme=theme, scenario=scenario):
                    self.build(scenario)
                    apply_tile_theme(self.root, theme)
                    request = self.fixture.requests[0]
                    self.manager.submit(request)
                    self.manager.advance(request.duration * .95)
                    if scenario == 'fragile':
                        intact, _ = self.layer._fragile[(5, 2)]
                        self.assertIn(self.color(theme, 'FRAGILE'), self.colors(intact))
                    else:
                        for _, active in self.layer._switches.values():
                            self.assertIn(self.color(theme, 'ACTIVE'), self.colors(active))
                    self.manager.advance(request.duration)

    def test_all_six_falling_fragments_have_the_matching_palette(self):
        from src.gui.scene_style import apply_tile_theme
        for theme in ('light', 'dark'):
            self.build('fragile')
            apply_tile_theme(self.root, theme)
            self.finish(self.fixture.requests[0])
            request = AnimationRequest(1, 'theme-collapse', self.manager.current_snapshot,
                None, AnimationKind.TERMINAL, .9, events=(AnimationEvent(EventKind.FALL),),
                terminal=TerminalVisualOutcome(EventKind.FALL, collapse_cell=(5, 2)))
            self.manager.submit(request)
            self.manager.advance(.3)
            _, pieces = self.layer._debris[(5, 2)]
            self.assertEqual(len(pieces), 6)
            for piece in pieces:
                self.assertIn(self.color(theme, 'FRAGILE'), self.colors(piece))
                other = 'dark' if theme == 'light' else 'light'
                self.assertNotIn(self.color(other, 'FRAGILE'), self.colors(piece))
            self.manager.cancel()
            self.assertTrue(self.layer.animated_root.isHidden())

    def test_theme_changes_during_pause_do_not_move_actors_or_add_nodes(self):
        from src.gui.scene_style import apply_tile_theme
        self.build('bridge')
        self.manager.submit(self.fixture.requests[0])
        self.manager.advance(.3)
        self.manager.pause()
        poses, progress = self.poses(), self.manager.progress
        count = self.root.findAllMatches('**').getNumPaths()
        bridge = self.layer._bridges['bridge-main']
        transform = bridge.getTransform()
        for theme in ('dark', 'light') * 10:
            apply_tile_theme(self.root, theme)
            self.manager.advance(10)
            self.assertIn(self.color(theme, 'BRIDGE_TOP'), self.colors(bridge))
            self.assertEqual(self.poses(), poses)
            self.assertEqual(self.manager.progress, progress)
            self.assertEqual(bridge.getTransform(), transform)
            self.assertEqual(self.root.findAllMatches('**').getNumPaths(), count)
            self.assertTrue(self.layer.renderer_root.isHidden())
        self.manager.cancel()
        self.assertFalse(self.layer.renderer_root.isHidden())

    def test_new_level_inherits_dark_and_dispose_releases_variant_handles(self):
        from src.gui.scene_style import apply_tile_theme
        apply_tile_theme(self.root, 'dark')
        self.build('bridge')
        self.manager.submit(self.fixture.requests[0])
        self.manager.advance(.5)
        self.assertIn(self.color('dark', 'BRIDGE_TOP'),
                      self.colors(self.layer._bridges['bridge-main']))
        self.manager.dispose()
        self.renderer.dispose()
        self.layer.dispose()
        self.assertEqual(self.layer._tile_variants, {})
