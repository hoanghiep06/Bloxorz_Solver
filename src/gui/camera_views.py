"""Selectable camera views (Iso / Top / Follow) plus free orbit and zoom.

Views are switched with the C key or the HUD button:
Iso    : diagonal view from the front of the board (the original camera).
Top    : straight down.
Follow : Iso orbited 75 degrees to the LEFT and tilted higher, zoomed in and gliding after the
         block. While Follow is active the movement keys are mapped to the screen
         (W/Up away from the camera, A/Left to the screen's left, ...), which stays
         correct even if FOLLOW_ORBIT is changed to a larger angle.

On top of every view the player can:
  * scroll the mouse wheel to zoom in / out,
  * hold the left mouse button and drag to orbit in any direction.
Pressing the View button / C while the camera has been moved returns it to the
current view's exact position; pressing again goes on to the next view.
A drag is not a click: `drag_happened` tells the mouse-control code to ignore it.
"""
from dataclasses import dataclass, replace
import math

from src.gui.action_plan import DIRECTIONS
from src.gui.camera import CameraConfig, SceneBounds
from src.gui.controller import KEY_TO_ACTION
from src.gui.geometry_math import cell_to_world
from src.gui.mouse_control import controlled_cells, pointer_over_hud


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

# ---- free orbit / zoom tuning ----
ORBIT_YAW_PER_PX = 0.30      # degrees of azimuth per pixel dragged horizontally
ORBIT_PITCH_PER_PX = 0.25    # degrees of elevation per pixel dragged vertically
INVERT_YAW = False           # True: dragging right orbits the other way
INVERT_PITCH = False         # True: dragging down looks from lower instead of higher
MIN_ELEVATION, MAX_ELEVATION = 8.0, 88.0
ZOOM_MIN, ZOOM_MAX = 0.30, 2.20   # multiplier of the fitted camera distance
ZOOM_STEP = 0.88                  # per wheel notch (smaller = faster zoom)
ZOOM_SMOOTHING = 12.0             # higher = zoom settles faster
DRAG_THRESHOLD_PX = 5             # moving less than this is still a click

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


def _wrap_degrees(value):
    return (value + 180.0) % 360.0 - 180.0


class CameraViewController:
    def __init__(self, app, controller, camera, hud=None):
        from direct.showbase.DirectObject import DirectObject
        self.app, self.controller, self.camera, self.hud = app, controller, camera, hud
        self.index = 0
        self._focus = None
        self._disposed = False
        # User offsets on top of the current view.
        self._yaw = self._pitch = 0.0
        self._zoom = self._zoom_target = 1.0
        # Drag state. drag_happened stays True until the NEXT press so that the
        # click handler (mouse1-up) can read it regardless of handler order.
        self._press = self._last = None
        self._dragging = False
        self.drag_happened = False
        self._keys_relative = False
        self._set_label()
        app.accept('c', self.cycle)
        self._listener = DirectObject()
        self._listener.accept('mouse1', self._press_event)
        self._listener.accept('mouse1-up', self._release_event)
        self._listener.accept('wheel_up', self._wheel, [1])
        self._listener.accept('wheel_down', self._wheel, [-1])
        self._task = app.taskMgr.add(self._update, 'CameraViewFollow')

    @property
    def spec(self):
        return VIEWS[self.index]

    @property
    def user_modified(self):
        """True while the camera is rotated/zoomed away from the current view."""
        return (abs(self._yaw) >= .5 or abs(self._pitch) >= .5
                or abs(self._zoom_target - 1) > .01 or abs(self._zoom - 1) > .01)

    # ------------------------------------------------------------ switching
    def cycle(self):
        """View button / C: first return to the current view if it was moved, else go next."""
        if self._disposed or not self.controller.input_enabled:
            return
        if self.user_modified:
            self.set_view(self.index)
        else:
            self.set_view((self.index + 1) % len(VIEWS))

    def set_view(self, index):
        self.index = index
        self._focus = None
        self._clear_user()
        spec = self.spec
        target = self._target() if spec.follow else None
        if target is not None:
            self._focus = target
            self.camera.set_view(spec.config, bounds=self._bounds(target), zoom=1.0)
        else:
            from src.gui.temple_environment import visible_board_bounds
            board = self.controller.board_data
            self.camera.set_view(spec.config, zoom=1.0,
                                 bounds=visible_board_bounds(board) if board is not None else None)
        self._sync_keys(force=True)
        self._set_label()

    def on_level_loaded(self):
        """Called after the camera was refit for a new level; re-snap on next frame."""
        self._focus = None
        if self.user_modified:
            self._clear_user()
            self._apply_user()

    def _set_label(self):
        if self.hud is not None:
            self.hud.set_view_label('Reset view' if self.user_modified
                                    else f'View: {self.spec.label}')

    # ------------------------------------------------------------ user orbit / zoom
    def _clear_user(self):
        self._yaw = self._pitch = 0.0
        self._zoom = self._zoom_target = 1.0

    def _current_config(self):
        """Spec config plus the user's yaw/pitch (pitch clamped to a sane range)."""
        base = self.spec.config
        elevation = min(MAX_ELEVATION, max(MIN_ELEVATION, base.elevation + self._pitch))
        self._pitch = elevation - base.elevation
        return replace(base, azimuth=base.azimuth + self._yaw, elevation=elevation)

    def _apply_user(self):
        self.camera.orbit(self._current_config(), self._zoom)
        self._sync_keys()
        self._set_label()

    def _can_interact(self):
        flow = getattr(self.app, 'game_flow', None)
        if flow is None or flow.name != 'game' or flow.intro.active:
            return False
        tutorial = getattr(self.app, 'game_tutorial', None)
        return not (tutorial is not None and tutorial.visible)

    def _pointer_ok(self):
        """Mouse is over the 3D area (not over any HUD / menu widget)."""
        if not self._can_interact():
            return False
        watcher = self.app.mouseWatcherNode
        if not watcher.hasMouse():
            return False
        from direct.gui.DirectGuiBase import DirectGuiWidget
        region = watcher.getOverRegion()
        if region is not None and region.getName() in DirectGuiWidget.guiDict:
            return False
        if pointer_over_hud(self.app):
            return False
        mouse = watcher.getMouse()
        left, right, bottom, top = self.app.dashboard.viewport.region.getDimensions()
        u, v = (mouse[0] + 1) / 2, (mouse[1] + 1) / 2
        return left <= u <= right and bottom <= v <= top

    def _press_event(self):
        self._press = self._last = None
        self._dragging = False
        self.drag_happened = False
        if self._disposed or not self._pointer_ok():
            return
        mouse = self.app.mouseWatcherNode.getMouse()
        self._press = self._last = (mouse[0], mouse[1])

    def _release_event(self):
        self._press = self._last = None
        self._dragging = False

    def _wheel(self, direction):
        if self._disposed or not self._pointer_ok():
            return
        factor = ZOOM_STEP if direction > 0 else 1 / ZOOM_STEP
        self._zoom_target = min(ZOOM_MAX, max(ZOOM_MIN, self._zoom_target * factor))

    def _poll_drag(self):
        """Turn mouse movement while the button is held into yaw/pitch changes."""
        if self._press is None:
            return False
        watcher = self.app.mouseWatcherNode
        if not watcher.hasMouse():
            return False
        mouse = watcher.getMouse()
        mx, my = mouse[0], mouse[1]
        half_w, half_h = self.app.win.getXSize() / 2, self.app.win.getYSize() / 2
        if not self._dragging:
            moved = math.hypot((mx - self._press[0]) * half_w, (my - self._press[1]) * half_h)
            if moved < DRAG_THRESHOLD_PX:
                return False
            self._dragging = True
            self.drag_happened = True
        dx = (mx - self._last[0]) * half_w          # pixels, right = positive
        dy = -(my - self._last[1]) * half_h         # pixels, down = positive
        self._last = (mx, my)
        if dx == 0 and dy == 0:
            return False
        self._yaw = _wrap_degrees(self._yaw - dx * ORBIT_YAW_PER_PX * (-1 if INVERT_YAW else 1))
        self._pitch += dy * ORBIT_PITCH_PER_PX * (-1 if INVERT_PITCH else 1)
        return True

    def _ease_zoom(self, dt):
        diff = self._zoom_target - self._zoom
        if abs(diff) < 1e-4:
            if diff != 0:
                self._zoom = self._zoom_target
                return True
            return False
        self._zoom += diff * (1 - math.exp(-ZOOM_SMOOTHING * dt))
        return True

    # ------------------------------------------------------------ keys
    def _resolve(self, relative):
        hx, hy = screen_heading(self.camera.config.azimuth)
        vec = {'forward': (hx, hy), 'back': (-hx, -hy),
               'left': (-hy, hx), 'right': (hy, -hx)}[relative]
        return _ACTION_OF.get(vec)

    def _relative_key(self, relative):
        action = self._resolve(relative)
        if action is not None:
            self.controller._key_move(action)

    def _apply_keys(self, relative):
        """Relative: movement keys follow the screen. Otherwise restore the world keys."""
        for key, rel in RELATIVE_KEYS.items():
            if relative:
                self.app.accept(key, self._relative_key, [rel])
            else:
                self.app.accept(key, self.controller._key_move, [KEY_TO_ACTION[key]])

    def _sync_keys(self, force=False):
        """Screen-relative keys in Follow, or whenever the player rotated the camera."""
        relative = self.spec.follow or abs(self._yaw) >= .5
        if force or relative != self._keys_relative:
            self._apply_keys(relative)
            self._keys_relative = relative

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
        if self._disposed or self.camera.current_fit is None:
            return task.cont
        from panda3d.core import ClockObject
        dt = min(ClockObject.getGlobalClock().getDt(), .05)
        flow = getattr(self.app, 'game_flow', None)
        if flow is not None and flow.name != 'game' and self.user_modified:
            self._clear_user()           # leaving the level: menus use the plain view
            self._press = self._last = None
            self._dragging = False
            self._apply_user()
        changed = self._poll_drag()
        changed = self._ease_zoom(dt) or changed
        if changed:
            self._apply_user()
        if not self.spec.follow:
            return task.cont
        target = self._target()
        if target is None:
            return task.cont
        if self._focus is None:
            self._focus = target
            self.camera.set_view(self._current_config(), bounds=self._bounds(target),
                                 zoom=self._zoom)
            return task.cont
        dx, dy = target[0] - self._focus[0], target[1] - self._focus[1]
        if math.hypot(dx, dy) < 1e-4:
            return task.cont
        alpha = 1 - math.exp(-SMOOTHING * dt)
        self._focus = (self._focus[0] + dx * alpha, self._focus[1] + dy * alpha)
        self.camera.reframe(self._bounds(self._focus))
        return task.cont

    def dispose(self):
        if self._disposed:
            return
        self._disposed = True
        self.app.ignore('c')
        self._listener.ignoreAll()
        for key in RELATIVE_KEYS:
            self.app.accept(key, self.controller._key_move, [KEY_TO_ACTION[key]])
        if self._task is not None:
            self.app.taskMgr.remove(self._task)
            self._task = None
        self.hud = None