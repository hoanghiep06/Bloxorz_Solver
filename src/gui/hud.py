"""DirectGUI HUD: a row of buttons at the top-left and the level name at the top-right.

No side panel. Controls are bound by the host (bind_action/bind_speed). The
solver/playback rows are collapsible (set_guide_visible).
"""

from dataclasses import dataclass
import math

from src.gui import ui_theme as ui

UNKNOWN = '—'


@dataclass(frozen=True)
class HudViewModel:
    level_label: str = 'Level 01'
    runtime_status: str = 'PREVIEW'
    move_count: int | None = None
    search_time_ms: float | None = None
    expanded_nodes: int | None = None
    solution_length: int | None = None
    peak_python_memory_bytes: int | None = None

    def __post_init__(self):
        for value in (self.level_label, self.runtime_status):
            if not isinstance(value, str) or not value.strip():
                raise ValueError('HUD identity/status must be nonempty strings.')
        for value in (self.move_count, self.expanded_nodes, self.solution_length,
                      self.peak_python_memory_bytes):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError('Counts and memory bytes must be nonnegative integers or None.')
        value = self.search_time_ms
        if value is not None and (type(value) not in (int, float)
                                  or not math.isfinite(value) or value < 0):
            raise ValueError('Search time must be finite nonnegative milliseconds or None.')


def metric_values(model: HudViewModel) -> tuple[str, ...]:
    """Format supplied data only; memory uses binary units, never GPU/RSS estimates."""
    def count(value):
        return UNKNOWN if value is None else str(value)

    time = model.search_time_ms
    time_text = UNKNOWN if time is None else (f'{time:.2f} ms' if time < 1000 else f'{time / 1000:.2f} s')
    memory = model.peak_python_memory_bytes
    memory_text = (UNKNOWN if memory is None else f'{memory / 1048576:.2f} MiB'
                   if memory >= 1048576 else f'{memory / 1024:.2f} KiB'
                   if memory >= 1024 else f'{memory} B')
    return (count(model.move_count), time_text, count(model.expanded_nodes),
            count(model.solution_length), memory_text)


def _color(hex_value):
    return tuple(int(hex_value[index:index + 2], 16) / 255 for index in (0, 2, 4)) + (1,)


# Kept for modules/tests that still import them.
BG_MAIN = _color('F1F4F7')
BG_SECONDARY = _color('E7EFF5')
HUD_SURFACE = (1, 1, 1, 1)
HUD_BORDER = _color('D1DEE8')
TEXT_PRIMARY = _color('273B50')
TEXT_SECONDARY = _color('61778B')
METRIC_LABELS = ('Moves', 'Search Time', 'Expanded Nodes', 'Solution Length', 'Peak Python Memory')

# ---- layout constants (pixels) ----
MARGIN, GAP, BTN_H, TEXT = 20, 10, 46, 22
TOP_ROW = (('Exit', 90), ('Restart', 110), ('Guide', 130))
SOLVERS = ('BFS', 'DFS', 'IDS', 'UCS', 'Greedy', 'A*')
PLAYBACK = (('Play', 110), ('Step', 110), ('Close', 190))
SOLVER_W = 100
ROW2_Y, ROW3_Y = MARGIN + BTN_H + GAP, MARGIN + 2 * (BTN_H + GAP)
LEFT_END = MARGIN + sum(w for _, w in TOP_ROW) + GAP * (len(TOP_ROW) - 1)
DISPLAY = {'Guide': 'AI Solver', 'Close': 'Hide Solution'}
LEVEL_SIZE, STATUS_SIZE = 30, 18


class HudShell:
    """Own one pixel2d subtree. Construct widgets once; update text in place."""

    def __init__(self, pixel2d, model=HudViewModel()):
        from direct.gui.DirectGui import DirectSlider
        from direct.gui import DirectGuiGlobals as DGG
        from panda3d.core import TextNode

        self._TextNode = TextNode
        self._widgets = []
        self._solvers = []        # row 2: algorithm buttons
        self._playback = []       # row 3: Play/Step/Hide Solution + speed
        self._guide_open = False
        self._selected = None
        self._hint_ready = False
        self._guide_mode = False
        self._disposed = False
        self.layout = None
        self.model = model
        self.surfaces = {}        # legacy attribute, intentionally empty
        self.buttons = {}
        self.root = pixel2d.attachNewNode('DashboardHUD')
        self.bar = self.root.attachNewNode('HUDBar')
        try:
            x = MARGIN
            for name, width in TOP_ROW:
                self._add_button(name, x, MARGIN, width)
                x += width + GAP
            for i, name in enumerate(SOLVERS):
                self._add_button(name, MARGIN + i * (SOLVER_W + GAP), ROW2_Y, SOLVER_W,
                                 group=self._solvers)
            x = MARGIN
            for name, width in PLAYBACK:
                self._add_button(name, x, ROW3_Y, width, group=self._playback)
                x += width + GAP

            sx = x + 10
            base = ROW3_Y + BTN_H / 2 + 7
            self.speed_label = self._label('Speed', 20, sx, base, muted=True)
            self._playback.append(self.speed_label)
            sw, sh, sx2 = 180, 14, sx + 80
            self.speed = self._own(DirectSlider(
                parent=self.bar, pos=(sx2 + sw / 2, 0, -(ROW3_Y + BTN_H / 2)),
                frameSize=(-sw / 2, sw / 2, -sh / 2, sh / 2),
                frameColor=ui.LINE, relief=DGG.FLAT, range=(.25, 4), value=1,
                pageSize=0, state=DGG.DISABLED, thumb_state=DGG.DISABLED,
                thumb_relief=DGG.FLAT, thumb_frameColor=ui.PRIMARY,
                thumb_frameSize=(-9, 9, -15, 15)))
            self._playback.append(self.speed)
            self.speed_text = self._label('1.0x', 20, sx2 + sw + 20, base, muted=True)
            self._playback.append(self.speed_text)

            self.level = self._label('', LEVEL_SIZE, 0, MARGIN + 30, align='right')
            self.runtime = self._label('', STATUS_SIZE, 0, MARGIN + 52, align='right', muted=True)
            self.warning = self._label('Minimum window size: 1024 x 720', 16, 0, 0, align='center',
                                       parent=self.root)
            self.warning.hide()
            self.set_guide_visible(False)
            self.update_view_model(model)
        except BaseException:
            self.dispose()
            raise

    # ------------------------------------------------------------ builders
    def _own(self, widget):
        self._widgets.append(widget)
        return widget

    def _label(self, text, size, x, baseline, *, align='left', muted=False, parent=None):
        return self._own(ui.make_label(parent or self.bar, text, size, x, baseline,
                                       color=ui.MUTED if muted else ui.INK, align=align))

    def _add_button(self, name, x, y, width, group=None):
        button = ui.make_button(self.bar, DISPLAY.get(name, name), x, y, width, BTN_H,
                                lambda: None, size=TEXT, enabled=False)
        self._own(button.border)
        self._own(button)
        self.buttons[name] = button
        if group is not None:
            group.append(button.border)

    # ------------------------------------------------------------ host wiring
    def bind_action(self, name, callback):
        """Enable one button and run callback() when it is clicked."""
        from direct.gui import DirectGuiGlobals as DGG
        button = self.buttons[name]
        original = callback
        if name in SOLVERS:
            def callback():
                if original() is not False:
                    self.select_solver(name)
        elif name == 'Close':
            def callback():
                original()
                self.set_guide_visible(False)
        button['command'] = callback
        button['state'] = DGG.NORMAL
        ui.style_button(button, primary=False)

    def bind_speed(self, callback):
        """Enable the playback-speed slider; callback(value) gets 0.25..4.0."""
        from direct.gui import DirectGuiGlobals as DGG

        def changed():
            value = float(self.speed['value'])
            self.speed_text['text'] = f'{value:.1f}x'
            callback(value)

        self.speed['command'] = changed
        self.speed['state'] = DGG.NORMAL
        self.speed.thumb['state'] = DGG.NORMAL

    # ------------------------------------------------------------ guide UI state
    @property
    def guide_open(self):
        return self._guide_open

    def set_guide_visible(self, visible):
        """AI Solver toggled: show the algorithm row. Closing clears everything."""
        self._guide_open = bool(visible)
        for widget in self._solvers:
            widget.show() if visible else widget.hide()
        if not visible:
            self._selected = None
            self._set_playback(False)
        self._style_dynamic()

    def select_solver(self, name):
        """Algorithm chosen: highlight it and reveal Play/Step/Hide Solution."""
        self._selected = name
        self._set_playback(True)
        self._style_dynamic()

    def set_playing(self, playing):
        self.buttons['Play']['text'] = 'Pause' if playing else 'Play'

    def set_guide_mode(self, active):
        """While a solution runs, hide Restart and AI Solver."""
        self._guide_mode = bool(active)
        self._refresh_top()

    def set_hint_ready(self, ready):
        """AI Solver only appears after the player has been idle for a while."""
        self._hint_ready = bool(ready)
        self._refresh_top()

    def _refresh_top(self):
        restart, guide = self.buttons['Restart'].border, self.buttons['Guide'].border
        restart.hide() if self._guide_mode else restart.show()
        show_guide = not self._guide_mode and (self._hint_ready or self._guide_open)
        guide.show() if show_guide else guide.hide()
    def _set_playback(self, visible):
        for widget in self._playback:
            widget.show() if visible else widget.hide()

    def _style_dynamic(self):
        ui.style_button(self.buttons['Guide'], primary=self._guide_open)
        for name in SOLVERS:
            ui.style_button(self.buttons[name], primary=name == self._selected)

    def restyle(self):
        """Re-apply the current ui_theme palette to already-built widgets."""
        if self._disposed:
            return
        from direct.gui import DirectGuiGlobals as DGG
        for button in self.buttons.values():
            enabled = button['state'] == DGG.NORMAL
            ui.style_button(button, primary=False)
            if not enabled:
                button['text_fg'] = ui.DISABLED_TEXT
        self._style_dynamic()
        self.level['text_fg'] = ui.INK
        self.runtime['text_fg'] = ui.MUTED
        self.speed_label['text_fg'] = ui.MUTED
        self.speed_text['text_fg'] = ui.MUTED
        self.warning['text_fg'] = ui.INK
        self.speed['frameColor'] = ui.LINE
        self.speed.thumb['frameColor'] = ui.PRIMARY

    # ------------------------------------------------------------ layout/data
    def _fit_text(self, label, text, size, max_width):
        node = self._TextNode('HUDTextMeasure')
        if node.calcWidth(text) * size <= max_width:
            label['text'] = text
            return
        while text and node.calcWidth(text + '…') * size > max_width:
            text = text[:-1]
        label['text'] = text + '…'

    def _refresh_texts(self):
        width = self.layout.width if self.layout else 1024
        self._fit_text(self.level, self.model.level_label, LEVEL_SIZE,
                       max(80, width - LEFT_END - 3 * MARGIN))
        self._fit_text(self.runtime, self.model.runtime_status, STATUS_SIZE, 300)

    def apply_layout(self, layout):
        if self._disposed:
            return
        self.layout = layout
        if not layout.supported:
            self.bar.hide()
            self.warning.setPos(layout.width / 2, 0, -layout.height / 2)
            self.warning.show()
            return
        self.warning.hide()
        self.bar.show()
        self.level.setX(layout.width - MARGIN)
        self.runtime.setX(layout.width - MARGIN)
        self._refresh_texts()

    def update_view_model(self, model):
        if not isinstance(model, HudViewModel):
            raise ValueError('Expected HudViewModel.')
        if self._disposed:
            raise RuntimeError('HUD is disposed.')
        self.model = model
        self._refresh_texts()

    def dispose(self):
        if self._disposed:
            return
        self._disposed = True
        for widget in reversed(self._widgets):
            widget.destroy()
        self._widgets.clear()
        self._solvers.clear()
        self._playback.clear()
        self.buttons.clear()
        self.root.removeNode()