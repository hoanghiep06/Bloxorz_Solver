"""Standalone static-board inspection using the unchanged Stage 3.1 host."""

import argparse
from pathlib import Path

from panda3d.core import loadPrcFileData, unloadPrcFile

from src.core.board import Board
from src.core.state import BloxorzState, Orientation
from src.gui.app import BloxorzPreviewApp
from src.gui.camera import BoardCameraController
from src.gui.contracts import BasicOrientation
from src.gui.render_adapter import build_board_data, build_game_snapshot
from src.gui.renderer import BasicSceneRenderer
from src.gui.scene_lighting import SceneLightingController
from src.gui.scene_style import SceneStyle


DEFAULT_LEVEL = Path(__file__).resolve().parents[2] / "levels" / "level_01.json"
_CORE_ORIENTATIONS = {
    BasicOrientation.STANDING: Orientation.STANDING,
    BasicOrientation.HORIZONTAL: Orientation.HORIZONTAL,
    BasicOrientation.VERTICAL: Orientation.VERTICAL,
}


class PreviewPresentation:
    """Wire presentation ownership without changing the host/renderer classes or API."""

    def __init__(self, app, board_data, *, shadows=False, antialiasing=True):
        self.camera = self.lighting = self.style = None
        self._exit_callbacks = app.finalExitCallbacks
        self._disposed = False
        try:
            self.camera = BoardCameraController(app.camera, app.camLens)
            self.camera.fit_board(board_data, app.win.getXSize(), app.win.getYSize())
            samples = app.win.getFbProperties().getMultisamples()
            self.style = SceneStyle(app.static_board_root, app.block_root, app.camera,
                                    multisamples=samples, antialiasing=antialiasing)
            self.lighting = SceneLightingController(app.scene_root, self.camera.current_fit,
                                                    shadows=shadows, gsg=app.win.getGsg())
            self._refit(self.camera.current_fit)
            self.camera.bind_window(app.win, on_refit=self._refit)
            # Existing ShowBase API: legacy callers may still dispose renderer then
            # destroy host. This callback cleans listeners/background in that path.
            self._exit_callbacks.append(self.dispose)
        except BaseException:
            self.dispose()
            raise

    def _refit(self, fit):
        self.style.update_background(fit)
        self.lighting.fit_bounds(fit)

    def dispose(self):
        """Idempotent cleanup, also safe from ShowBase.finalExitCallbacks."""
        if self._disposed:
            return
        self._disposed = True
        if self.dispose in self._exit_callbacks:
            self._exit_callbacks.remove(self.dispose)
        for component in (self.camera, self.lighting, self.style):
            if component is not None:
                component.dispose()
        self.camera = self.lighting = self.style = None
        self._exit_callbacks = None


def dispose_presentation(app):
    """Clean presentation before renderer/host without requiring a new return type."""
    presentation = getattr(app, 'presentation', None)
    if isinstance(presentation, PreviewPresentation):
        presentation.dispose()


def create_preview(
    level: str | Path = DEFAULT_LEVEL,
    *,
    pose: BasicOrientation = BasicOrientation.STANDING,
    shadows: bool = False,
    antialiasing: bool = True,
) -> tuple[BloxorzPreviewApp, BasicSceneRenderer]:
    """Create exactly one host and a static scene; caller must dispose/destroy.

    Alternative poses are inspection fixtures at the initial anchor, not moves.
    Input/adapter validation happens before opening the window. Camera/lighting
    are owned by app.presentation; the return pair remains backward compatible.
    """
    if not isinstance(pose, BasicOrientation):
        raise ValueError("pose must be BasicOrientation.")
    level = Path(level).resolve()
    board = Board(str(level))
    data = build_board_data(board, level_id=level.as_posix())
    initial = board.get_initial_state()
    state = BloxorzState(initial.r, initial.c, _CORE_ORIENTATIONS[pose], initial.bridges_state)
    snapshot = build_game_snapshot(state, board_data=data,
                                   session_id="board-preview", state_revision=0)
    # Remove the local PRC request after creation. Panda caches default framebuffer
    # properties: use a fresh process for reliable AA requests (or --no-aa).
    aa_page = loadPrcFileData('bloxorz-preview-aa',
                              f'framebuffer-multisample {int(antialiasing)}\n'
                              f'multisamples {4 if antialiasing else 0}\n')
    try:
        app = BloxorzPreviewApp()
    finally:
        unloadPrcFile(aa_page)
    renderer = None
    try:
        renderer = BasicSceneRenderer(app.static_board_root, app.block_root)
        renderer.load_board(data)
        renderer.show_snapshot(snapshot)
        app.presentation = PreviewPresentation(app, data, shadows=shadows, antialiasing=antialiasing)
    except BaseException:
        try:
            dispose_presentation(app)
        finally:
            try:
                if renderer is not None:
                    renderer.dispose()
            finally:
                app.destroy()
        raise
    return app, renderer


def main(argv: list[str] | None = None) -> None:
    """Run the existing host loop with static geometry, without gameplay controls."""
    parser = argparse.ArgumentParser(description="Bloxorz Basic geometry preview (static only).")
    parser.add_argument("--level", type=Path, default=DEFAULT_LEVEL, help="Path to a Basic JSON level.")
    parser.add_argument("--pose", choices=[value.value for value in BasicOrientation],
                        default="STANDING", help="Inspection pose at the initial anchor.")
    parser.add_argument('--shadows', action='store_true', help='Request optional shadow mapping.')
    parser.add_argument('--no-aa', action='store_true', help='Disable the preview MSAA request.')
    args = parser.parse_args(argv)
    app, renderer = create_preview(args.level, pose=BasicOrientation(args.pose),
                                   shadows=args.shadows, antialiasing=not args.no_aa)
    try:
        app.run()
    finally:
        try:
            dispose_presentation(app)
        finally:
            try:
                renderer.dispose()
            finally:
                app.destroy()


if __name__ == "__main__":
    main()
