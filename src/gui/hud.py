"""DirectGUI HUD: icon toolbar at the top-left and the level name at the top-right.

Row 1: square icon buttons (Exit | Restart, Solver, View, Help). Hovering an
icon shows its name next to the toolbar.
Row 2 (only while Solver is open): algorithm chips, then Play/Step icons and
the speed slider once an algorithm is chosen. There is no "Hide Solution"
button: pressing the Solver icon again closes the solver and its solution.
Controls are bound by the host (bind_action/bind_speed).
"""

from dataclasses import dataclass
import math
import re

from src.gui import icons
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


def display_level_label(label: str) -> str:
    """'level_01' / 'Level 01 (1/18)' -> 'Level 01'."""
    label = re.sub(r'\s*\(\s*\d+\s*/\s*\d+\s*\)\s*$', '', label.strip())
    match = re.match(r'(?i)^level[_\s-]*(\d+)', label)
    return f'Level {match.group(1)}' if match else label


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
SQ = BTN_H                 # icon buttons are squares
ICON_HALF = 12             # 24px toolbar vectors; robot keeps a 26px portrait
DIVIDER = 24               # extra space separating Exit from the other tools
TOP_ROW = (('Exit', 104), ('Restart', 134), ('Guide', 166), ('View', SQ), ('Tutorial', SQ))
SOLVERS = ('BFS', 'DFS', 'IDS', 'UCS', 'Greedy', 'A*')
PLAYBACK = (('Play', SQ), ('Step', SQ))
SOLVER_W = 84
ROW2_Y = MARGIN + BTN_H + GAP
LEVEL_SIZE, STATUS_SIZE = 24, 17
TIP_SPACE = 0            # room reserved for the hover name next to the toolbar
INFO_PAD, INFO_MIN_W = 36, 110   # padding (both sides) and min width of the level-name frame


def _top_positions():
    xs, x = [], MARGIN
    for index, (_, width) in enumerate(TOP_ROW):
        xs.append(x)
        x += width + (DIVIDER if index == 0 else GAP)
    return xs


TOP_X = _top_positions()
LEFT_END = TOP_X[-1] + TOP_ROW[-1][1]

# Button name -> icon variants (first one is shown by default).
ICONS = {
    'Exit': ('exit',), 'Restart': ('restart',), 'Guide': ('ai',), 'View': ('view',),
    'Tutorial': ('help',), 'Play': ('play', 'pause'), 'Step': ('step',),
}
TIPS = {
    'Exit': 'Exit', 'Restart': 'Restart (R)', 'Guide': 'Solver', 'View': 'View: Iso (C)',
    'Tutorial': 'Help (H)', 'Play': 'Play / Pause', 'Step': 'Step',
}


class HudShell:
    """Own one pixel2d subtree. Construct widgets once; update text in place."""

    def __init__(self, pixel2d, model=HudViewModel()):
        from direct.gui.DirectGui import DirectSlider
        from direct.gui import DirectGuiGlobals as DGG
        from panda3d.core import TextNode

        self._TextNode = TextNode
        self._widgets = []
        self._solvers = []        # row 2: algorithm chips
        self._playback = []       # row 2: Play/Step icons + speed slider
        self._holders = {}        # button name -> icon holder NodePath
        self._variants = {}       # button name -> {icon key: NodePath}
        self._tips = dict(TIPS)
        self.on_ui_audio = None
        self._close_callback = None
        self._guide_open = False
        self._selected = None
        self._guide_mode = False
        self._disposed = False
        self.layout = None
        self.model = model
        self.surfaces = {}
        self.buttons = {}
        self.root = pixel2d.attachNewNode('DashboardHUD')
        self.bar = self.root.attachNewNode('HUDBar')
        try:
            from direct.gui.DirectGui import DirectFrame
            self.metrics = self._own(DirectFrame(parent=self.root, relief=DGG.FLAT,
                frameColor=(0,0,0,0), frameSize=(0, 1, -76, 0)))
            self.surfaces = {'controls': self.bar, 'metrics': self.metrics}
            self.metric_labels = [self._label(text, 14, 0, 0, muted=True, parent=self.metrics)
                                  for text in METRIC_LABELS]
            self.metric_values = [self._label(UNKNOWN, 20, 0, 0, parent=self.metrics)
                                  for _ in METRIC_LABELS]
            self.metric_icons=[]
            self.metric_dividers=[]
            for index,key in enumerate(('steps','clock','nodes','graph','chip')):
                icon=icons.make_icon(key);icon.reparentTo(self.metrics)
                icon.setScale(14);icon.setColor(*ui.GOLD)
                self.metric_icons.append(icon)
                if index:
                    divider=ui.rounded_rect(1,48,0,ui.LINE);divider.reparentTo(self.metrics)
                    self.metric_dividers.append(divider)
            for (name, width), x in zip(TOP_ROW, TOP_X):
                self._add_button(name, x, MARGIN, width)
            for i, name in enumerate(SOLVERS):
                self._add_button(name, MARGIN + i * (SOLVER_W + GAP), ROW2_Y, SOLVER_W,
                                 group=self._solvers)
            x = MARGIN + len(SOLVERS) * (SOLVER_W + GAP) + 8
            for name, width in PLAYBACK:
                self._add_button(name, x, ROW2_Y, width, group=self._playback)
                x += width + GAP

            sx = x + 8
            sw, sh = 150, 14
            self.speed = self._own(DirectSlider(
                parent=self.bar, pos=(sx + sw / 2, 0, -(ROW2_Y + BTN_H / 2)),
                frameSize=(-sw / 2, sw / 2, -sh / 2, sh / 2),
                frameColor=ui.LINE, relief=DGG.FLAT, range=(.25, 4), value=1,
                pageSize=0, state=DGG.DISABLED, thumb_state=DGG.DISABLED,
                thumb_relief=DGG.FLAT, thumb_frameColor=ui.PRIMARY,
                thumb_frameSize=(-9, 9, -15, 15)))
            self._playback.append(self.speed)
            self.speed_text = self._label('1.0x', 20, sx + sw + 18, ROW2_Y + BTN_H / 2 + 7,
                                          muted=True)
            self._playback.append(self.speed_text)

            self.tip = self._label('', 14, MARGIN, ROW2_Y + BTN_H + 20, muted=True)
            self.info = self._own(DirectFrame(parent=self.bar,relief=None))
            self.level = self._label('', LEVEL_SIZE, 0, MARGIN + 24, align='center')
            self.runtime = self._label('', STATUS_SIZE, 0, MARGIN + 46, align='center', muted=True)
            self.warning = self._label('Minimum window size: 1024 x 720', 16, 0, 0, align='center',
                                       parent=self.root)
            # The 3D region is disabled below minimum size; the host clear is
            # pale in either theme, so this fallback needs a fixed dark ink.
            self.warning['text_fg'] = TEXT_PRIMARY
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
        has_icon = name in ICONS
        caption = {'Exit':'Exit','Restart':'Restart','Guide':'Solver'}.get(name, '' if has_icon else name)
        button = ui.make_button(self.bar, caption, x, y, width, BTN_H,
                                None, size=19 if has_icon else TEXT, enabled=False)
        self._own(button.border)
        self._own(button)
        self.buttons[name] = button
        if has_icon:
            self._add_icon(name, x + (25 if caption else width / 2), y + BTN_H / 2)
            if caption:
                button['text_pos'] = (width/2 + 13, -BTN_H/2 - 5)
        self._bind_tip(name, button)
        if group is not None:
            group.append(button.border)
            if has_icon:
                group.append(self._holders[name])

    def _add_icon(self, name, cx, cy):
        holder = self.bar.attachNewNode(f'Icon-{name}')
        holder.setPos(cx, 0, -cy)
        holder.setScale(ICON_HALF)
        variants = {}
        for index, key in enumerate(ICONS[name]):
            node = icons.make_robot_icon() if name=='Guide' else icons.make_icon(key)
            node.reparentTo(holder)
            if index:
                node.hide()
            variants[key] = node
        self._holders[name] = holder
        self._variants[name] = variants

    def _bind_tip(self, name, button):
        from direct.gui import DirectGuiGlobals as DGG
        try:
            button.bind(DGG.ENTER, lambda _event, n=name: self._show_tip(n))
            button.bind(DGG.EXIT, lambda _event: self._show_tip(None))
        except Exception:
            pass  # tooltips are optional

    def _show_tip(self, name):
        if not self._disposed:
            self.tip['text'] = '' if name is None else self._tips.get(name, '')

    def _show_variant(self, name, key):
        for variant, node in self._variants.get(name, {}).items():
            node.show() if variant == key else node.hide()

    def _tint_icons(self):
        """Icons follow the button's text colour (normal, primary or disabled)."""
        for name, holder in self._holders.items():
            color = ui.INK
            try:
                color = tuple(self.buttons[name]['text_fg'])
            except Exception:
                pass
            if name=='Guide':
                from direct.gui import DirectGuiGlobals as DGG
                holder.setColorScale(1,1,1,1 if self.buttons[name]['state']==DGG.NORMAL else .45)
            else:holder.setColor(*color)

    def _set_visible(self, name, visible):
        widgets = [self.buttons[name].border]
        if name in self._holders:
            widgets.append(self._holders[name])
        for widget in widgets:
            widget.show() if visible else widget.hide()

    # ------------------------------------------------------------ host wiring
    def bind_action(self, name, callback):
        """Enable one button and run callback() when it is clicked.

        'Close' has no button any more: its callback runs when the Solver
        icon is pressed while the solver is open.
        """
        from direct.gui import DirectGuiGlobals as DGG
        if name == 'Close':
            self._close_callback = callback
            return
        button = self.buttons.get(name)
        if button is None:
            return
        original = callback
        if name in SOLVERS:
            def callback():
                if original() is not False:
                    self.select_solver(name)
        elif name == 'Guide':
            def callback():
                if self._guide_open:
                    if self._close_callback is not None:
                        self._close_callback()
                    self.set_guide_visible(False)
                else:
                    original()
        def clicked():
            if self.on_ui_audio:self.on_ui_audio('ui_back' if name=='Exit' else 'ui_click')
            callback()
        button['command'] = clicked
        button['state'] = DGG.NORMAL
        ui.style_button(button, primary=False)
        self._style_dynamic()

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
        """Solver toggled: show the algorithm row. Closing clears everything."""
        self._guide_open = bool(visible)
        for widget in self._solvers:
            widget.show() if visible else widget.hide()
        self._sync_metrics()
        if not visible:
            self._selected = None
            self._set_playback(False)
        self._style_dynamic()

    def _sync_metrics(self):
        """Metric frames (Moves / Search Time / ...) only show while Solver is open."""
        supported = self.layout is None or self.layout.supported
        if self._guide_open and supported:
            self.metrics.show()
        else:
            self.metrics.hide()

    def select_solver(self, name):
        """Algorithm chosen: highlight it and reveal Play/Step and the speed slider."""
        self._selected = name
        self._set_playback(True)
        self._style_dynamic()

    def set_playing(self, playing):
        self._show_variant('Play', 'pause' if playing else 'play')

    def set_view_label(self, text):
        """Camera view changed: the View icon's hover name shows the current view."""
        self._tips['View'] = f'{text} (C)'

    def set_guide_mode(self, active):
        """While a solution runs, hide Restart. The Solver icon stays as the way out."""
        self._guide_mode = bool(active)
        self._refresh_top()

    def _refresh_top(self):
        self._set_visible('Restart', not self._guide_mode)

    def _set_playback(self, visible):
        for widget in self._playback:
            widget.show() if visible else widget.hide()

    def _style_dynamic(self):
        ui.style_button(self.buttons['Guide'], primary=True)
        for name in SOLVERS:
            ui.style_button(self.buttons[name], primary=name == self._selected)
        self._tint_icons()

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
        self.tip['text_fg'] = ui.MUTED
        self.speed_text['text_fg'] = ui.MUTED
        self.warning['text_fg'] = TEXT_PRIMARY
        self.speed['frameColor'] = ui.LINE
        self.speed.thumb['frameColor'] = ui.PRIMARY
        self._style_metrics()
        self._layout_info()   # the info frame is rebuilt with the new PAPER colour
        for icon in self.metric_icons:
            icon.setColor(*ui.GOLD)
        for label in self.metric_labels:
            label['text_fg'] = ui.MUTED
        for label in self.metric_values:
            label['text_fg'] = ui.INK

    # ------------------------------------------------------------ layout/data
    def _fit_text(self, label, text, size, max_width, suffix=''):
        node = self._TextNode('HUDTextMeasure')
        if node.calcWidth(text) * size <= max_width:
            label['text'] = text
            return
        if suffix and text.endswith(suffix):
            text=text[:-len(suffix)]
        while text and node.calcWidth(text + '…' + suffix) * size > max_width:
            text = text[:-1]
        label['text'] = text + '…' + suffix

    def _refresh_texts(self):
        width = self.layout.width if self.layout else 1024
        title = display_level_label(self.model.level_label)
        self._fit_text(self.level, title, LEVEL_SIZE,
                       max(80, width - LEFT_END - 3 * MARGIN - TIP_SPACE))
        # The compact title intentionally omits the catalog fraction. Keep it
        # visible in the status line, including when a long title is elided.
        counter = re.search(r'\(\s*(\d+\s*/\s*\d+)\s*\)\s*$', self.model.level_label)
        suffix = f' | {counter.group(1)}' if counter else ''
        self._fit_text(self.runtime, self.model.runtime_status + suffix, STATUS_SIZE, 300, suffix=suffix)
        cell = (width - 40) / 5
        for label, value in zip(self.metric_values, metric_values(self.model)):
            self._fit_text(label, value, 20, cell - 56)
        self._layout_info()

    def _layout_info(self):
        """Level-name frame shrinks to the text width and hugs the right edge."""
        if self._disposed or self.layout is None or not self.layout.supported:
            return
        node = self._TextNode('HUDTextMeasure')
        level_w = node.calcWidth(self.level['text']) * LEVEL_SIZE
        run_w = node.calcWidth(self.runtime['text']) * STATUS_SIZE
        info_width = max(INFO_MIN_W, max(level_w, run_w) + INFO_PAD)
        self.info.setPos(self.layout.width - info_width - MARGIN, 0, -MARGIN)
        self.info['geom'] = ui.rounded_rect(info_width, 52, 10, ui.PAPER)
        center_x = self.layout.width - MARGIN - info_width / 2
        self.level.setX(center_x)
        self.runtime.setX(center_x)

    def apply_layout(self, layout):
        if self._disposed:
            return
        self.layout = layout
        if not layout.supported:
            self.bar.hide()
            self.metrics.hide()
            self.warning.setPos(layout.width / 2, 0, -layout.height / 2)
            self.warning.show()
            return
        self.warning.hide()
        self.bar.show()
        self._sync_metrics()
        self.metrics.setPos(20, 0, -(layout.height - 94))
        self.metrics['frameSize'] = (0, layout.width - 40, -76, 0)
        self._style_metrics()
        cell = (layout.width - 40) / 5
        for index, (label, value) in enumerate(zip(self.metric_labels, self.metric_values)):
            label.setPos(index * cell + 46, 0, -24)
            self.metric_icons[index].setPos(index*cell+24,0,-30)
            if index:
                self.metric_dividers[index-1].setPos(index*cell,0,-14)
            value.setPos(index * cell + 46, 0, -55)
        self._refresh_texts()   # also sizes/positions the info frame

    def _style_metrics(self):
        width = self.layout.width-40 if self.layout else 1240
        # Two nested rounded meshes provide a luminous one-pixel frame.
        border = ui.rounded_outline(width,76,12,ui.LINE)
        fill = ui.rounded_rect(width-2,74,11,ui.PAPER)
        fill.reparentTo(border); fill.setPos(1,-.01,-1)
        self.metrics['geom'] = border

    def contains_pointer_pixels(self, x, y):
        """Reserve visible toolbar/status and metric bands for the HUD."""
        if self.layout is None or not self.layout.supported:
            return True
        if not (0 <= x <= self.layout.width and 0 <= y <= self.layout.height):
            return False
        top = ROW2_Y + BTN_H + GAP if self._guide_open else 92
        return y <= top or (self._guide_open and y >= self.layout.height - 94)

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
        self.on_ui_audio = None
        for widget in reversed(self._widgets):
            widget.destroy()
        self._widgets.clear()
        self._solvers.clear()
        self._playback.clear()
        self._holders.clear()
        self._variants.clear()
        self.buttons.clear()
        self.root.removeNode()