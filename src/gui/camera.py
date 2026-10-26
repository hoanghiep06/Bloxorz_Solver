"""Stable perspective framing; math remains usable without Panda3D installed."""

from dataclasses import dataclass
from itertools import product
import math

from src.gui.contracts import StaticBoardData


@dataclass(frozen=True, slots=True)
class CameraConfig:
    azimuth: float = 30.0
    elevation: float = 45.0
    vertical_fov: float = 45.0
    padding: float = 0.1  # Fraction of full viewport on EACH edge.

    def __post_init__(self):
        for name in ('azimuth', 'elevation', 'vertical_fov', 'padding'):
            _finite(getattr(self, name), name)
        if not -89 < self.elevation < 89:
            raise ValueError('elevation must be between -89 and 89 degrees.')
        if not 1 <= self.vertical_fov < 175:
            raise ValueError('vertical_fov must be in [1, 175) degrees.')
        if not 0 <= self.padding < 0.45:
            raise ValueError('padding must be in [0, 0.45).')


@dataclass(frozen=True, slots=True)
class SceneBounds:
    minimum: tuple[float, float, float]
    maximum: tuple[float, float, float]

    def __post_init__(self):
        for name, values in (('minimum', self.minimum), ('maximum', self.maximum)):
            if type(values) is not tuple or len(values) != 3:
                raise ValueError(f'{name} must be an XYZ tuple.')
            for value in values:
                _finite(value, name)
        if any(a >= b for a, b in zip(self.minimum, self.maximum)):
            raise ValueError('bounds minimum must be smaller than maximum on every axis.')

    def corners(self):
        return tuple(product(*zip(self.minimum, self.maximum)))


@dataclass(frozen=True, slots=True)
class CameraFit:
    position: tuple[float, float, float]
    target: tuple[float, float, float]
    right: tuple[float, float, float]
    up: tuple[float, float, float]
    forward: tuple[float, float, float]
    distance: float
    horizontal_fov: float
    vertical_fov: float
    near: float
    far: float
    aspect: float
    bounds: SceneBounds


def _finite(value, field):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f'{field} must be a finite number (not bool).')


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def camera_basis(config: CameraConfig = CameraConfig()):
    """Return target-to-camera, right, up and viewing-forward unit vectors."""
    azimuth, elevation = math.radians(config.azimuth), math.radians(config.elevation)
    back = (math.sin(azimuth) * math.cos(elevation),
            -math.cos(azimuth) * math.cos(elevation), math.sin(elevation))
    right = (math.cos(azimuth), math.sin(azimuth), 0.0)
    forward = tuple(-v for v in back)
    up = (-math.sin(azimuth) * math.sin(elevation),
          math.cos(azimuth) * math.sin(elevation), math.cos(elevation))
    return back, right, up, forward


def board_bounds(board_data: StaticBoardData, *, pitch: float = 1.0) -> SceneBounds:
    """Whole-level envelope, including void footprint and fixed maximum block height.

    The current goal is shallower than tile bottom -0.18s. Height +2.30s includes
    every static Basic pose and reserved headroom; no fake geometry is created.
    """
    if type(board_data) is not StaticBoardData:
        raise TypeError('board_data must be StaticBoardData.')
    _finite(pitch, 'pitch')
    if pitch <= 0:
        raise ValueError('pitch must be positive.')
    half_x, half_y = board_data.cols * pitch / 2, board_data.rows * pitch / 2
    return SceneBounds((-half_x, -half_y, -0.18 * pitch),
                       (half_x, half_y, 2.30 * pitch))


def fit_camera(board_data: StaticBoardData, width: int, height: int, *, pitch: float = 1.0,
               config: CameraConfig = CameraConfig(), bounds: SceneBounds | None = None) -> CameraFit:
    """Analytically fit all AABB corners to a padded perspective frustum."""
    for name, value in (('width', width), ('height', height)):
        if type(value) is not int or value <= 0:
            raise ValueError(f'{name} must be a positive integer.')
    envelope = board_bounds(board_data, pitch=pitch) if bounds is None else bounds
    _finite(pitch, 'pitch')
    if pitch <= 0:
        raise ValueError('pitch must be positive.')
    aspect = width / height
    tangent_v = math.tan(math.radians(config.vertical_fov) / 2)
    tangent_h = aspect * tangent_v
    horizontal = math.degrees(2 * math.atan(tangent_h))
    back, right, up, forward = camera_basis(config)
    target = ((envelope.minimum[0] + envelope.maximum[0]) / 2,
              (envelope.minimum[1] + envelope.maximum[1]) / 2, 0.4 * pitch)
    projections = []
    for corner in envelope.corners():
        delta = tuple(a - b for a, b in zip(corner, target))
        projections.append((_dot(delta, right), _dot(delta, up), _dot(delta, forward)))
    usable = 1 - 2 * config.padding
    distance = max(max(abs(x) / (usable * tangent_h) - z,
                       abs(y) / (usable * tangent_v) - z, 0.1 * pitch - z)
                   for x, y, z in projections) * (1 + 1e-12)
    depths = [distance + z for _, _, z in projections]
    near = max(0.01 * pitch, min(depths) * 0.5)
    far = max(depths) + max(2 * pitch, 0.1 * max(depths))
    position = tuple(t + distance * b for t, b in zip(target, back))
    for value in (*position, distance, near, far, horizontal, aspect):
        _finite(value, 'camera fit result')
    if not 0 < horizontal < 180 or not 0 < near < min(depths) < far:
        raise ValueError('camera inputs exceed stable perspective precision.')
    return CameraFit(position, target, right, up, forward, distance, horizontal,
                     config.vertical_fov, near, far, aspect, envelope)


def project_point(point, fit: CameraFit):
    """Return NDC x/y and forward depth, independently of engine projection."""
    delta = tuple(a - b for a, b in zip(point, fit.position))
    depth = _dot(delta, fit.forward)
    if depth <= 0:
        raise ValueError('point is behind the camera.')
    return (_dot(delta, fit.right) / (depth * math.tan(math.radians(fit.horizontal_fov) / 2)),
            _dot(delta, fit.up) / (depth * math.tan(math.radians(fit.vertical_fov) / 2)), depth)


class BoardCameraController:
    """Own camera configuration and an independent resize-event listener, not a host."""

    def __init__(self, camera, lens, *, config: CameraConfig = CameraConfig()):
        from panda3d.core import PerspectiveLens
        if not isinstance(lens, PerspectiveLens) or camera.isEmpty():
            raise ValueError('camera must be live and lens must be PerspectiveLens.')
        self.camera, self.lens, self.config = camera, lens, config
        self.current_fit = None
        self._board = None
        self._pitch = 1.0
        self._bounds = None
        self._dimensions = None
        self._window = self._provider = self._listener = None
        self._on_refit = None
        self._disposed = False

    def fit_board(self, board_data, width, height, *, pitch=1.0, bounds=None, notify=True):
        """Fit on load/configuration changes. Invalid/minimized sizes keep the previous pose.

        notify=False skips the on_refit callback (used by per-frame follow reframing).
        """
        if self._disposed:
            raise RuntimeError('Camera controller is disposed.')
        if width == 0 or height == 0:
            return False
        fit = fit_camera(board_data, width, height, pitch=pitch, config=self.config, bounds=bounds)
        self._board, self._pitch, self._bounds = board_data, pitch, bounds
        self._dimensions = (width, height)
        self.current_fit = fit
        self.lens.setFov(fit.horizontal_fov, fit.vertical_fov)
        self.lens.setNearFar(fit.near, fit.far)
        self.camera.setPos(*fit.position)
        self.camera.lookAt(*fit.target)
        if notify and self._on_refit:
            self._on_refit(fit)
        return True

    def set_viewport_size(self, width, height):
        """Apply caller-supplied viewport pixels, independent of full-window layout."""
        if self._disposed:
            raise RuntimeError('Camera controller is disposed.')
        if self._board is None:
            raise RuntimeError('fit_board must be called before resizing.')
        if width == 0 or height == 0:
            return False
        # ShowBase may have just adjusted the lens for the full window. Reassert
        # viewport FOV after that event, even if the viewport dimensions are unchanged.
        if ((width, height) == self._dimensions and self.current_fit
                and abs(self.lens.getVfov() - self.current_fit.vertical_fov) < 1e-4
                and abs(self.lens.getAspectRatio() - width / height) < 1e-5):
            return False
        return self.fit_board(self._board, width, height, pitch=self._pitch, bounds=self._bounds)

    def configure(self, config: CameraConfig):
        """Deliberately change configuration and refit the same static envelope."""
        if self._disposed:
            raise RuntimeError('Camera controller is disposed.')
        self.config = config
        if self._board is not None:
            self.fit_board(self._board, *self._dimensions, pitch=self._pitch, bounds=self._bounds)

    def set_view(self, config: CameraConfig, *, bounds=None, notify=True):
        """Switch viewing angle and refit (bounds=None frames the whole board)."""
        if self._disposed:
            raise RuntimeError('Camera controller is disposed.')
        self.config = config
        if self._board is None or self._dimensions is None:
            return False
        return self.fit_board(self._board, *self._dimensions, pitch=self._pitch,
                              bounds=bounds, notify=notify)

    def reframe(self, bounds, config: CameraConfig | None = None):
        """Per-frame reframe for follow cameras (optionally rotating); skips on_refit."""
        if self._disposed or self._board is None or self._dimensions is None:
            return False
        if config is not None:
            self.config = config
        return self.fit_board(self._board, *self._dimensions, pitch=self._pitch,
                              bounds=bounds, notify=False)

    def bind_window(self, window, *, viewport_size=None, on_refit=None):
        """Subscribe once per event with a separate DirectObject owner.

        aspectRatioChanged is sent AFTER ShowBase lens adjustment; window-event
        also covers same-aspect resizes/minimization. Neither handler replaces or
        ignores ShowBase's callbacks. No polling task is added.
        """
        from direct.showbase.DirectObject import DirectObject
        if self._disposed:
            raise RuntimeError('Camera controller is disposed.')
        if self._listener is not None:
            self._listener.ignoreAll()
        self._window, self._provider, self._on_refit = window, viewport_size, on_refit
        self._listener = DirectObject()
        self._listener.accept('window-event', self._window_event)
        self._listener.accept('aspectRatioChanged', self._aspect_event)

    def _resize(self):
        if self._window is None or self._board is None:
            return
        if self._window.getXSize() <= 0 or self._window.getYSize() <= 0:
            return
        dimensions = (self._provider(self._window) if self._provider else
                      (self._window.getXSize(), self._window.getYSize()))
        self.set_viewport_size(*dimensions)

    def _window_event(self, window):
        if window == self._window:
            self._resize()

    def _aspect_event(self):
        self._resize()

    def dispose(self):
        """Remove only owned event subscriptions and release scene/window references."""
        if self._listener:
            self._listener.ignoreAll()
        self._listener = self._window = self._provider = self._on_refit = None
        self.camera = self.lens = self._board = self.current_fit = None
        self._disposed = True