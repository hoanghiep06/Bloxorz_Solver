"""Immutable client-pixel layout. No engine or gameplay dependencies."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self):
        values = (self.x, self.y, self.width, self.height)
        if any(type(value) is not int for value in values):
            raise ValueError('Rectangle coordinates must be integers.')
        if self.x < 0 or self.y < 0 or self.width <= 0 or self.height <= 0:
            raise ValueError('Rectangle origin must be nonnegative and size positive.')

    @property
    def right(self):
        return self.x + self.width

    @property
    def bottom(self):
        return self.y + self.height

    def intersects(self, other):
        return (self.x < other.right and other.x < self.right
                and self.y < other.bottom and other.y < self.bottom)


@dataclass(frozen=True)
class LayoutResult:
    width: int
    height: int
    viewport: Rect
    header: Rect | None
    panel: Rect | None
    status: Rect | None
    supported: bool


MIN_WIDTH, MIN_HEIGHT = 1024, 720
PANEL_PADDING, CONTROL_GAP, CONTROL_HEIGHT = 16, 8, 32
# All panel control geometry lives here, in local top-left pixels.
CONTROL_ROWS = (
    ('Exit', 'Restart', 42), ('Guide', None, 82),
    ('BFS', 'DFS', 156), ('IDS', 'UCS', 196), ('Greedy', 'A*', 236),
    ('Play', 'Pause', 310), ('Step', 'Stop', 350),
)
GUIDE_CONTROLS = ('BFS', 'DFS', 'IDS', 'UCS', 'Greedy', 'A*', 'Play', 'Pause', 'Step', 'Stop')
SECTION_LABELS = (('GAME', 28), ('AI SOLVERS', 144), ('PLAYBACK', 296))
SPEED_RECT = Rect(16, 428, 250, 28)
SPEED_LABEL_Y, SPEED_VALUE_Y, PANEL_FOOTER_Y = 412, 478, 508


def _size(width, height):
    if any(type(value) is not int or value <= 0 for value in (width, height)):
        raise ValueError('Client width and height must be positive integers.')


def calculate_layout(width: int, height: int) -> LayoutResult:
    """Keep readable HUD sizes; below minimum return an explicit warning layout.

    A minimized (zero-size) window is handled by the viewport without calling here.
    """
    _size(width, height)
    if width < MIN_WIDTH or height < MIN_HEIGHT:
        return LayoutResult(width, height, Rect(0, 0, width, height),
                            None, None, None, False)
    return LayoutResult(width, height, Rect(24, 92, width - 346, height - 190),
                        Rect(24, 24, width - 48, 56),
                        Rect(width - 306, 92, 282, height - 190),
                        Rect(24, height - 86, width - 48, 62), True)


def normalized_region(rect: Rect, width: int, height: int) -> tuple[float, ...]:
    """Convert top-left pixels to Panda's bottom-left normalized bounds."""
    _size(width, height)
    if rect.right > width or rect.bottom > height:
        raise ValueError('Rectangle must be inside the client area.')
    return (rect.x / width, rect.right / width,
            1 - rect.bottom / height, 1 - rect.y / height)


def panel_controls(panel_width=282):
    """Stable action-name to rectangle mapping; no callbacks or action behavior."""
    available = panel_width - 2 * PANEL_PADDING
    column = (available - CONTROL_GAP) // 2
    return {
        name: Rect(PANEL_PADDING + index * (column + CONTROL_GAP), y,
                   column if second else available, CONTROL_HEIGHT)
        for first, second, y in CONTROL_ROWS
        for index, name in enumerate((first, second) if second else (first,))
    }
