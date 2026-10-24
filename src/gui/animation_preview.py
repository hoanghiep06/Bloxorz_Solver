"""ANIMATION DEMO DATA — NOT AUTHORITATIVE GAMEPLAY. One host, disabled controls."""
import argparse
import math

from panda3d.core import ClockObject, WindowProperties, loadPrcFileData, unloadPrcFile

from src.gui.app import BloxorzPreviewApp
from src.gui.advanced_renderer import AdvancedSceneRenderer
from src.gui.advanced_preview import AdvancedPreviewPresentation, build_framing_data
from src.gui.board_preview import dispose_presentation
from src.gui.dashboard_preview import DashboardPresentation
from src.gui.hud import HudViewModel
from src.gui.animation_contracts import as_visual_board
from src.gui.animation_effects import AnimatedSurfaceLayer
from src.gui.animation_manager import AnimationManager
from src.gui.animation_timeline import AnimationTimeline
from src.gui.animation_fixtures import SCENARIOS, get_animation_fixture


class AnimationDemoDriver:
    """One owned task for a finite, fixed fixture storyboard; not a replay queue."""
    def __init__(self, app, manager, fixture):
        self.app, self.manager, self.fixture = app, manager, fixture
        self.index, self.wait = 0, 0.0
        self._task = app.taskMgr.add(self._update, f'AnimationDemo-{id(self)}')

    def _update(self, task):
        dt = ClockObject.getGlobalClock().getDt()
        if self.manager.is_busy:
            self.manager.advance(dt)
            self.wait = 0.0
        elif self.index < len(self.fixture.requests):
            self.wait += dt
            if self.wait >= .60:
                request = self.fixture.requests[self.index]
                self.manager.submit(request)
                self.index += 1
                self.app.dashboard.hud.update_view_model(HudViewModel(
                    level_label='ANIMATION DEMO DATA / ' + self.fixture.name.upper(),
                    runtime_status=f'DEMO {self.index}/{len(self.fixture.requests)} / NOT GAMEPLAY'))
        return task.cont

    def dispose(self):
        if self._task is not None:
            self.app.taskMgr.remove(self._task)
            self._task = None


def create_animation_preview(scenario='combined', *, speed=1.0, shadows=False,
                             antialiasing=True, autoplay=True):
    """Return (app, renderer, manager). Use dispose_animation_preview once for host."""
    fixture = get_animation_fixture(scenario)
    AnimationTimeline(1, speed)  # Validate all user options before opening a window.
    board = as_visual_board(fixture.board)
    page = loadPrcFileData('animation-preview-aa',
        f'framebuffer-multisample {int(antialiasing)}\nmultisamples {4 if antialiasing else 0}\n')
    try:
        app = BloxorzPreviewApp()
    finally:
        unloadPrcFile(page)
    renderer = manager = surfaces = None
    app.animation_demo_driver = None
    app.animation_stop_callback = None
    try:
        surfaces = AnimatedSurfaceLayer(app.dynamic_tile_root, board)
        app.animation_surface_layer = surfaces
        renderer = AdvancedSceneRenderer(app.static_board_root, surfaces.renderer_root, app.block_root)
        renderer.load_board(board)
        app.presentation = AdvancedPreviewPresentation(app, build_framing_data(board),
            shadows=shadows, antialiasing=antialiasing)
        app.dashboard = DashboardPresentation(app, HudViewModel(
            level_label='ANIMATION DEMO DATA / ' + scenario.upper(),
            runtime_status='NOT GAMEPLAY'))
        manager = AnimationManager(renderer, fixture.board, fixture.initial, app.block_root,
                                    surface_layer=surfaces)
        manager.set_playback_rate(speed)
        app.animation_fixture = fixture
        if autoplay:
            app.animation_demo_driver = AnimationDemoDriver(app, manager, fixture)

        def stop_animation():
            if app.animation_demo_driver is not None:
                app.animation_demo_driver.dispose()
            try:
                manager.dispose()
            finally:
                # Panda 1.10.16 ShowBase.destroy leaves its own BufferViewer
                # subscribed. Release only this newly created host's inspector,
                # through its public DirectObject API, never global handlers.
                app.bufferViewer.ignoreAll()

        app.animation_stop_callback = stop_animation
        app.finalExitCallbacks.insert(0, stop_animation)
        properties = WindowProperties()
        properties.setTitle(f'Bloxorz Solver — Animation Demo / {scenario} — NOT AUTHORITATIVE GAMEPLAY')
        app.win.requestProperties(properties)
    except BaseException:
        dispose_animation_preview(app, renderer, manager)
        raise
    return app, renderer, manager


def dispose_animation_preview(app, renderer, manager):
    try:
        driver = getattr(app, 'animation_demo_driver', None)
        if driver is not None:
            driver.dispose()
        callback = getattr(app, 'animation_stop_callback', None)
        if callback in app.finalExitCallbacks:
            app.finalExitCallbacks.remove(callback)
        try:
            if manager is not None:
                manager.dispose()
        finally:
            app.bufferViewer.ignoreAll()
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
                    try:
                        surfaces = getattr(app, 'animation_surface_layer', None)
                        if surfaces is not None:
                            surfaces.dispose()
                    finally:
                        app.destroy()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=SCENARIOS, default='combined')
    parser.add_argument('--speed', type=float, default=1.0)
    parser.add_argument('--shadows', action='store_true')
    parser.add_argument('--no-aa', action='store_true')
    parser.add_argument('--no-autoplay', action='store_true', help='Deterministic API inspection mode.')
    args = parser.parse_args(argv)
    if not math.isfinite(args.speed) or not .05 <= args.speed <= 8:
        parser.error('--speed must be finite in [.05, 8].')
    app, renderer, manager = create_animation_preview(args.scenario, speed=args.speed,
        shadows=args.shadows, antialiasing=not args.no_aa, autoplay=not args.no_autoplay)
    try:
        app.run()
    finally:
        dispose_animation_preview(app, renderer, manager)


if __name__ == '__main__':
    main()
