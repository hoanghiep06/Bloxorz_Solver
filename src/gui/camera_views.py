"""Selectable camera views (Iso / Top / Follow) switched with the C key or HUD button.

Iso    : diagonal view from the front of the board (the original camera).
Top    : straight down.
Follow : Iso orbited 75 degrees to the LEFT and tilted higher, zoomed in and gliding after the
         block. While Follow is active the movement keys are mapped to the screen
         (W/Up away from the camera, A/Left to the screen's left, ...), which stays
         correct even if FOLLOW_ORBIT is changed to a larger angle.
"""
from dataclasses import dataclass
import math

from src.gui.action_plan import DIRECTIONS
from src.gui.camera import CameraConfig, SceneBounds
from src.gui.controller import KEY_TO_ACTION
from src.gui.geometry_math import cell_to_world
from src.gui.mouse_control import controlled_cells


@dataclass(frozen=True)
class ViewSpec:
    label: str
    config: CameraConfig
    follow: bool = False


ISO_AZIMUTH = CameraConfig().azimuth
FOLLOW_ORBIT = 75.0       # degrees the Follow camera is rotated to the left of Iso
FOLLOW_ELEVATION = 55.0   # camera pitch above the board (Iso is 45)
VIEWS = (
    ViewSpec('Iso', CameraConfig()),
    ViewSpec('Top', CameraConfig(azimuth=0.0, elevation=88.0, padding=0.10)),
    # Iso orbited to the left (negative = camera moves toward screen-left).
    ViewSpec('Follow', CameraConfig(azimuth=ISO_AZIMUTH - FOLLOW_ORBIT,
                          elevation=FOLLOW_ELEVATION, padding=0.1),
             follow=True),
)
FOLLOW_RADIUS = 2.6   # half-size (cells) of the area framed around the block
SMOOTHING = 7.0       # higher = camera catches up faster

# World (dx, dy) of each roll action, and the reverse lookup.
_VEC = {action: (round(d.value[0]), round(d.value[1])) for action, d in DIRECTIONS.items()}
_ACTION_OF = {vec: action for action, vec in _VEC.items()}
RELATIVE_KEYS = {
    'w': 'forward', 'arrow_up': 'forward', 's': 'back', 'arrow_down': 'back',
    'a': 'left', 'arrow_left': 'left', 'd': 'right', 'arrow_right': 'right',
}


def screen_heading(azimuth):
    """Cardinal roll vector that points 'up the screen' for a camera azimuth."""
    view = (-math.sin(math.radians(azimuth)), math.cos(math.radians(azimuth)))
    # Exact diagonals tie between two directions; prefer the original 'up' (W) one.
    return max(_VEC.values(), key=lambda vec: vec[0] * view[0] + vec[1] * view[1]
               + (1e-6 if vec == _VEC['U'] else 0.0))


class CameraViewController:
    def __init__(self, app, controller, camera, hud=None):
        self.app, self.controller, self.camera, self.hud = app, controller, camera, hud
        self.index = 0
        self._focus = None
        self._disposed = False
        self._set_label()
        app.accept('c', self.cycle)
        self._task = app.taskMgr.add(self._update, 'CameraViewFollow')

    @property
    def spec(self):
        return VIEWS[self.index]

    # ------------------------------------------------------------ switching
    def cycle(self):
        if self._disposed or not self.controller.input_enabled:
            return
        self.set_view((self.index + 1) % len(VIEWS))

    def set_view(self, index):
        self.index = index
        self._focus = None
        spec = self.spec
        target = self._target() if spec.follow else None
        if target is not None:
            self._focus = target
            self.camera.set_view(spec.config, bounds=self._bounds(target))
        else:
            self.camera.set_view(spec.config)   # whole board
        self._apply_keys(spec.follow)
        self._set_label()

    def on_level_loaded(self):
        """Called after the camera was refit for a new level; re-snap on next frame."""
        self._focus = None

    def _set_label(self):
        if self.hud is not None:
            self.hud.set_view_label(f'View: {self.spec.label}')

    # ------------------------------------------------------------ keys
    def _resolve(self, relative):
        hx, hy = screen_heading(self.spec.config.azimuth)
        vec = {'forward': (hx, hy), 'back': (-hx, -hy),
               'left': (-hy, hx), 'right': (hy, -hx)}[relative]
        return _ACTION_OF.get(vec)

    def _relative_key(self, relative):
        action = self._resolve(relative)
        if action is not None:
            self.controller._key_move(action)

    def _apply_keys(self, follow):
        """Follow: movement keys follow the screen. Otherwise restore the world keys."""
        for key, relative in RELATIVE_KEYS.items():
            if follow:
                self.app.accept(key, self._relative_key, [relative])
            else:
                self.app.accept(key, self.controller._key_move, [KEY_TO_ACTION[key]])

    # ------------------------------------------------------------ follow camera
    def _target(self):
        c = self.controller
        if c.state is None or c.board_data is None:
            return None
        bd = c.board_data
        points = [cell_to_world(r, col, rows=bd.rows, cols=bd.cols, pitch=1.0)
                  for r, col in controlled_cells(c.state)]
        return (sum(p[0] for p in points) / len(points),
                sum(p[1] for p in points) / len(points))

    @staticmethod
    def _bounds(focus):
        r = FOLLOW_RADIUS
        return SceneBounds((focus[0] - r, focus[1] - r, -0.18),
                           (focus[0] + r, focus[1] + r, 2.30))

    def _update(self, task):
        if self._disposed or not self.spec.follow or self.camera.current_fit is None:
            return task.cont
        target = self._target()
        if target is None:
            return task.cont
        if self._focus is None:
            self._focus = target
            self.camera.set_view(self.spec.config, bounds=self._bounds(target))
            return task.cont
        dx, dy = target[0] - self._focus[0], target[1] - self._focus[1]
        if math.hypot(dx, dy) < 1e-4:
            return task.cont
        from panda3d.core import ClockObject
        alpha = 1 - math.exp(-SMOOTHING * ClockObject.getGlobalClock().getDt())
        self._focus = (self._focus[0] + dx * alpha, self._focus[1] + dy * alpha)
        self.camera.reframe(self._bounds(self._focus))
        return task.cont

    def dispose(self):
        if self._disposed:
            return
        self._disposed = True
        self.app.ignore('c')
        for key in RELATIVE_KEYS:
            self.app.accept(key, self.controller._key_move, [KEY_TO_ACTION[key]])
        if self._task is not None:
            self.app.taskMgr.remove(self._task)
            self._task = None
        self.hud = None