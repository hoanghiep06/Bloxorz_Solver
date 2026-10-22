"""Engine scene-graph fixture helper; no ShowBase or GraphicsWindow."""
import importlib.util
import unittest
HAS_PANDA = importlib.util.find_spec('panda3d') is not None
if HAS_PANDA:
    from panda3d.core import NodePath
    from src.gui.advanced_renderer import AdvancedSceneRenderer
    from src.gui.animation_contracts import as_visual_board
    from src.gui.animation_effects import AnimatedSurfaceLayer
    from src.gui.animation_manager import AnimationManager
from src.gui.animation_fixtures import get_animation_fixture


class AnimationSceneCase(unittest.TestCase):
    FIXTURE = 'basic-roll'

    def setUp(self):
        self.root = self.manager = self.renderer = self.layer = None
        self.build(self.FIXTURE)

    def build(self, fixture):
        self.clean()
        self.fixture = get_animation_fixture(fixture) if isinstance(fixture, str) else fixture
        self.root = NodePath('world')
        self.static, self.dynamic, self.block = (self.root.attachNewNode(n) for n in ('static', 'dynamic', 'block'))
        self.foreign = tuple(r.attachNewNode('foreign') for r in (self.static, self.dynamic, self.block))
        self.board = as_visual_board(self.fixture.board)
        self.layer = AnimatedSurfaceLayer(self.dynamic, self.board)
        self.renderer = AdvancedSceneRenderer(self.static, self.layer.renderer_root, self.block)
        self.renderer.load_board(self.board)
        self.manager = AnimationManager(self.renderer, self.fixture.board, self.fixture.initial,
                                         self.block, surface_layer=self.layer)

    def clean(self):
        for obj in (self.manager, self.renderer, self.layer):
            if obj is not None:
                obj.dispose()
        if self.root is not None:
            self.root.removeNode()
        self.root = self.manager = self.renderer = self.layer = None

    def tearDown(self):
        self.clean()

    def poses(self):
        return dict(self.manager.current_visual_poses)

    def state(self):
        return [(p.node(), p.getTransform(), p.isHidden()) for p in self.root.findAllMatches('**')]

    def finish(self, request, callback=None):
        self.manager.submit(request, callback)
        self.manager.advance(request.duration)
