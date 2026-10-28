"""Stage 3.5 composition: existing static 3D preview plus a disabled HUD."""

import argparse
from pathlib import Path

from src.gui.board_preview import DEFAULT_LEVEL, create_preview, dispose_presentation
from src.gui.contracts import BasicOrientation
from src.gui.hud import HudShell, HudViewModel
from src.gui.viewport import DashboardViewport


class DashboardPresentation:
    """Own only HUD/viewport; existing presentation owns camera/lights/style."""

    def __init__(self, app, model):
        self.hud = self.viewport = self.bloom = None
        self._disposed = False
        self._callbacks = app.finalExitCallbacks
        self._scene_root = app.scene_root
        self._app = app
        try:
            self.hud = HudShell(app.pixel2d, model)
            self.viewport = DashboardViewport(
                app.win, app.cam, app.presentation.camera,
                on_refit=app.presentation._refit, on_layout=self.hud.apply_layout)
            from src.gui.cinematic_bloom import CinematicBloom
            self.bloom = CinematicBloom(app)
            # Run before PreviewPresentation even when caller only destroys host.
            self._callbacks.insert(0, self.dispose)
        except BaseException:
            self.dispose()
            raise

    def set_quality(self, choice):
        from src.gui.visual_materials import set_quality
        from src.gui.cinematic_bloom import CinematicBloom
        set_quality(choice)
        if self.bloom is not None:self.bloom.dispose()
        self.bloom=CinematicBloom(self._app)

    def dispose(self):
        if self._disposed:
            return
        self._disposed = True
        if self.dispose in self._callbacks:
            self._callbacks.remove(self.dispose)
        try:
            if self.bloom is not None:
                self.bloom.dispose()
            if self.viewport is not None:
                self.viewport.dispose(refit=not self._scene_root.isEmpty())
        finally:
            if self.hud is not None:
                self.hud.dispose()
            self._callbacks = None
            self._scene_root = None
            self._app = None


def create_dashboard(level=DEFAULT_LEVEL, *, pose=BasicOrientation.STANDING,
                     shadows=False, antialiasing=True):
    """Return the existing (app, renderer) pair; app.dashboard owns the new shell."""
    app, renderer = create_preview(level, pose=pose, shadows=shadows, antialiasing=antialiasing)
    try:
        from panda3d.core import WindowProperties
        properties = WindowProperties()
        properties.setTitle('Bloxorz Solver — 3D Preview')
        app.win.requestProperties(properties)
        label = Path(level).stem.replace('_', ' ').replace('-', ' ').title()
        app.dashboard = DashboardPresentation(app, HudViewModel(level_label=label))
    except BaseException:
        try:
            dispose_presentation(app)
        finally:
            try:
                renderer.dispose()
            finally:
                app.destroy()
        raise
    return app, renderer


def main(argv=None):
    parser = argparse.ArgumentParser(description='Bloxorz responsive dashboard (disabled controls).')
    parser.add_argument('--level', type=Path, default=DEFAULT_LEVEL)
    parser.add_argument('--pose', choices=[value.value for value in BasicOrientation], default='STANDING')
    parser.add_argument('--shadows', action='store_true')
    parser.add_argument('--no-aa', action='store_true')
    args = parser.parse_args(argv)
    app, renderer = create_dashboard(args.level, pose=BasicOrientation(args.pose),
                                     shadows=args.shadows, antialiasing=not args.no_aa)
    try:
        app.run()
    finally:
        try:
            app.dashboard.dispose()
        finally:
            try:
                dispose_presentation(app)
            finally:
                try:
                    renderer.dispose()
                finally:
                    app.destroy()


if __name__ == '__main__':
    main()
