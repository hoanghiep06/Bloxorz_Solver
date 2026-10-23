"""Standalone Advanced VISUAL DEMO DATA preview, with disabled dashboard controls."""

import argparse

from panda3d.core import (
    AntialiasAttrib, MaterialAttrib, WindowProperties, loadPrcFileData, unloadPrcFile,
)

from src.gui.app import BloxorzPreviewApp
from src.gui.advanced_contracts import AdvancedBoardData
from src.gui.advanced_fixtures import SCENARIOS, get_visual_fixture
from src.gui.advanced_renderer import AdvancedSceneRenderer
from src.gui.board_preview import PreviewPresentation, dispose_presentation
from src.gui.contracts import StaticBoardData, BasicTileKind
from src.gui.dashboard_preview import DashboardPresentation
from src.gui.hud import HudViewModel


def build_framing_data(board):
    """Dimensions-only camera carrier. Never pass this to a scene renderer.

    Full-grid camera bounds already include Z [-.18, 2.30] pitches; all Advanced
    meshes stay inside that envelope. Real tile semantics remain in schema 2.
    """
    if type(board) is not AdvancedBoardData:
        raise TypeError('Expected AdvancedBoardData for framing.')
    board.__post_init__()
    return StaticBoardData(1, 'framing-only:' + board.level_id, board.board_revision,
        board.rows, board.cols,
        tuple((BasicTileKind.VOID,) * board.cols for _ in range(board.rows)), ())


class AdvancedPreviewPresentation(PreviewPresentation):
    """Reuse presentation; extend its matte/AA state to the host's dynamic root.

    Basic presentation intentionally styles only static/block roots. Save and
    restore just these two attributes, preserving foreign state and siblings.
    """

    def __init__(self, app, board_data, **options):
        self._dynamic_states = []
        try:
            super().__init__(app, board_data, **options)
            root = app.dynamic_tile_root
            for kind in (MaterialAttrib, AntialiasAttrib):
                self._dynamic_states.append((root, kind, root.getAttrib(kind)))
                root.setAttrib(app.static_board_root.getAttrib(kind))
        except BaseException:
            self.dispose()
            raise

    def dispose(self):
        for root, kind, value in reversed(self._dynamic_states):
            if not root.isEmpty():
                if value is None:
                    root.clearAttrib(kind)
                else:
                    root.setAttrib(value)
        self._dynamic_states.clear()
        super().dispose()


def create_advanced_preview(scenario='combined', state=None, *, shadows=False, antialiasing=True):
    """Return one (app, renderer) pair; fixture selection precedes window creation."""
    fixture = get_visual_fixture(scenario)
    variant = fixture.variant(state)
    framing = build_framing_data(fixture.board)
    config = loadPrcFileData('advanced-preview-aa',
        f'framebuffer-multisample {"true" if antialiasing else "false"}\n'
        f'multisamples {4 if antialiasing else 0}')
    try:
        app = BloxorzPreviewApp()
    finally:
        unloadPrcFile(config)
    renderer = None
    try:
        renderer = AdvancedSceneRenderer(app.static_board_root, app.dynamic_tile_root, app.block_root)
        renderer.load_board(fixture.board)
        renderer.show_snapshot(variant.snapshot)
        app.presentation = AdvancedPreviewPresentation(app, framing, shadows=shadows,
                                                       antialiasing=antialiasing)
        app.dashboard = DashboardPresentation(app, HudViewModel(
            level_label='VISUAL DEMO DATA / ' + scenario.upper(), runtime_status=variant.label))
        properties = WindowProperties()
        properties.setTitle('Bloxorz Solver — Advanced Visual Preview')
        app.win.requestProperties(properties)
    except BaseException:
        dispose_advanced_preview(app, renderer)
        raise
    return app, renderer


def dispose_advanced_preview(app, renderer):
    """Cleanup in HUD, presentation, renderer, host order, even on failures."""
    try:
        dashboard = getattr(app, 'dashboard', None)
        if dashboard is not None:
            dashboard.dispose()
    finally:
        try:
            dispose_presentation(app)
        finally:
            try:
                if renderer is not None:
                    renderer.dispose()
            finally:
                app.destroy()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=SCENARIOS, default='combined')
    parser.add_argument('--state', help='Fixture state name; available states depend on scenario.')
    parser.add_argument('--shadows', action='store_true')
    parser.add_argument('--no-aa', action='store_true')
    args = parser.parse_args(argv)
    try:
        get_visual_fixture(args.scenario).variant(args.state)
    except ValueError as error:
        parser.error(str(error))
    app, renderer = create_advanced_preview(args.scenario, args.state,
        shadows=args.shadows, antialiasing=not args.no_aa)
    try:
        app.run()
    finally:
        dispose_advanced_preview(app, renderer)


if __name__ == '__main__':
    main()
