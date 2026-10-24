"""Bloxorz Solver game: menus, levels with stars, solver guide, settings, audio.

Run with ``python -m src.gui.game_app``. Composition only: gameplay flow lives in
GameController, menus in screens.UIFlow, visuals in the Advanced renderer stack.
"""

import argparse
from pathlib import Path

from panda3d.core import WindowProperties, loadPrcFileData, unloadPrcFile

from src.core.board import Board
from src.gui.advanced_preview import AdvancedPreviewPresentation, build_framing_data
from src.gui.app import BloxorzPreviewApp
from src.gui.attract import AttractMode
from src.gui.audio import AudioManager
from src.gui.board_preview import dispose_presentation
from src.gui.controller import GameController, LevelCatalog
from src.gui.dashboard_preview import DashboardPresentation
from src.gui.hud import HudViewModel
from src.gui.profile import DEFAULT_SAVE, SaveData
from src.gui.game_adapter import prepare_level
from src.gui.game_scene import GameScene
from src.gui.screens import UIFlow

DEFAULT_LEVELS = Path(__file__).resolve().parents[2] / 'levels'


def create_game(levels_dir=DEFAULT_LEVELS, *, shadows=False, antialiasing=True,
                save_path=DEFAULT_SAVE):
    """Return (app, renderer, controller). Release with dispose_game exactly once."""
    catalog = LevelCatalog(levels_dir)
    first = catalog[0]
    # Fail before opening a window if the first level is unsupported.
    first_board, _, _ = prepare_level(Board(str(first.path)), level_id=first.level_id, session_id='bootstrap')
    page = loadPrcFileData('game-aa', f'framebuffer-multisample {int(antialiasing)}\n'
                                      f'multisamples {4 if antialiasing else 0}\n')
    try:
        app = BloxorzPreviewApp(audio=True)
    finally:
        unloadPrcFile(page)
    renderer = controller = flow = None
    try:
        save = SaveData(save_path)
        audio = AudioManager(app, music_volume=save.settings.music_volume,
                             sfx_volume=save.settings.sfx_volume,
                             music_enabled=save.settings.music,
                             sfx_enabled=save.settings.sfx)
        app.game_audio = audio
        app.presentation = AdvancedPreviewPresentation(
            app, build_framing_data(first_board), shadows=shadows, antialiasing=antialiasing)
        app.dashboard = DashboardPresentation(app, HudViewModel(
            level_label=first.title, runtime_status='LOADING'))

        def load_visual_board(board):
            width, height = app.win.getXSize(), app.win.getYSize()
            if width <= 0 or height <= 0:
                return
            left, right, bottom, top = app.dashboard.viewport.region.getDimensions()
            size = (max(1, round((right - left) * width)), max(1, round((top - bottom) * height)))
            # Refit also triggers background/light updates via on_refit.
            app.presentation.camera.fit_board(build_framing_data(board), *size)

        def prepare_scene(board_data, snapshot):
            return GameScene(app, board_data, snapshot, on_activate=load_visual_board)

        def on_event(name):
            if flow is not None:
                flow.on_game_event(name)

        controller = GameController(catalog=catalog, prepare_scene=prepare_scene,
                                    hud=app.dashboard.hud, task_mgr=app.taskMgr,
                                    on_event=on_event)
        controller.bind_hud()
        controller.bind_keys(app.accept)
        if not controller.start(0):
            raise ValueError(controller._status)
        renderer = controller.manager.renderer
        app.game_controller = controller
        app.game_attract = AttractMode(controller, app.taskMgr)
        flow = UIFlow(app, controller, catalog, save, audio, app.game_attract)
        app.game_flow = flow
        app.finalExitCallbacks.insert(0, controller.dispose)
        properties = WindowProperties()
        properties.setTitle('Bloxorz Solver')
        app.win.requestProperties(properties)
        flow.show('main')
    except BaseException:
        dispose_game(app, renderer, controller)
        raise
    return app, renderer, controller


def dispose_game(app, renderer, controller):
    """Menus/attract -> controller (animation) -> HUD -> presentation -> renderer -> host."""
    try:
        flow = getattr(app, 'game_flow', None)
        if flow is not None:
            flow.dispose()
        attract = getattr(app, 'game_attract', None)
        if attract is not None:
            attract.stop()
        if controller is not None:
            if controller.dispose in app.finalExitCallbacks:
                app.finalExitCallbacks.remove(controller.dispose)
            controller.dispose()
    finally:
        try:
            audio = getattr(app, 'game_audio', None)
            if audio is not None:
                audio.dispose()
            app.bufferViewer.ignoreAll()  # same Panda 1.10 workaround as animation_preview
        finally:
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
    parser = argparse.ArgumentParser(description='Bloxorz Solver — game.')
    parser.add_argument('--levels', type=Path, default=DEFAULT_LEVELS)
    parser.add_argument('--save', type=Path, default=DEFAULT_SAVE, help='Save-file path.')
    parser.add_argument('--shadows', action='store_true')
    parser.add_argument('--no-aa', action='store_true')
    args = parser.parse_args(argv)
    app, renderer, controller = create_game(
        args.levels, shadows=args.shadows, antialiasing=not args.no_aa, save_path=args.save)
    try:
        app.run()
    finally:
        dispose_game(app, renderer, controller)


if __name__ == '__main__':
    main()
