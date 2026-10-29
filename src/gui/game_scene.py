"""Staged per-level visual ownership. Build hidden, activate, then release the old scene."""
from src.gui.advanced_renderer import AdvancedSceneRenderer
from src.gui.animation_effects import AnimatedSurfaceLayer
from src.gui.animation_manager import AnimationManager


class GameScene:
    def __init__(self, app, board, snapshot, *, on_activate=None):
        self.app, self.board, self.on_activate = app, board, on_activate
        self.roots = tuple(root.attachNewNode('StagedLevel') for root in
                           (app.static_board_root, app.dynamic_tile_root, app.block_root))
        self.layer = self.renderer = self.manager = None
        self._disposed = False
        for root in self.roots:
            root.hide()
        try:
            self.layer = AnimatedSurfaceLayer(self.roots[1], board)
            self.renderer = AdvancedSceneRenderer(self.roots[0], self.layer.renderer_root, self.roots[2])
            self.renderer.load_board(board)
            self.manager = AnimationManager(self.renderer, board, snapshot, self.roots[2],
                                            surface_layer=self.layer, task_mgr=app.taskMgr, audio=getattr(app,'game_audio',None))
        except BaseException:
            self.dispose()
            raise

    def activate(self):
        if self._disposed:
            raise RuntimeError('Level scene is disposed.')
        if self.on_activate is not None:
            self.on_activate(self.board)
        for root in self.roots:
            root.show()

    def dispose(self):
        if self._disposed:
            return
        self._disposed = True
        try:
            if self.manager is not None:
                self.manager.dispose()
        finally:
            try:
                if self.renderer is not None:
                    self.renderer.dispose()
            finally:
                if self.layer is not None:
                    self.layer.dispose()
                for root in self.roots:
                    root.removeNode()
