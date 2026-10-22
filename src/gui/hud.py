"""Disabled DirectGUI shell and pure presentation data. No gameplay ownership."""

from dataclasses import dataclass
import math

from src.gui.layout import (PANEL_FOOTER_Y, SECTION_LABELS, SPEED_LABEL_Y,
                            SPEED_RECT, SPEED_VALUE_Y, panel_controls)


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


BG_MAIN = _color('F1F4F7')
BG_SECONDARY = _color('E7EFF5')
HUD_SURFACE = (1, 1, 1, 1)
HUD_BORDER = _color('D1DEE8')
TEXT_PRIMARY = _color('273B50')
TEXT_SECONDARY = _color('61778B')
METRIC_LABELS = ('Moves', 'Search Time', 'Expanded Nodes', 'Solution Length', 'Peak Python Memory')


class HudShell:
    """Own one pixel2d subtree. Construct widgets once; update geometry/text in place."""

    def __init__(self, pixel2d, model=HudViewModel()):
        from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel, DirectSlider
        from direct.gui import DirectGuiGlobals as DGG
        from panda3d.core import TextNode

        self._Frame, self._Label = DirectFrame, DirectLabel
        self._TextNode = TextNode
        self._widgets = []
        self._disposed = False
        self.layout = None
        self.model = model
        self.root = pixel2d.attachNewNode('DashboardHUD')
        self.surfaces, self._inners = {}, {}
        self.buttons = {}
        try:
            for name in ('header', 'panel', 'status'):
                outer = self._own(DirectFrame(parent=self.root, relief=DGG.FLAT, frameColor=HUD_BORDER))
                inner = self._own(DirectFrame(parent=outer, relief=DGG.FLAT, frameColor=HUD_SURFACE))
                self.surfaces[name], self._inners[name] = outer, inner
            header, panel, status = (self.surfaces[name] for name in ('header', 'panel', 'status'))
            self.title = self._label(header, 'Bloxorz Solver', 24, 16, 26)
            self.subtitle = self._label(header, '3D Puzzle & AI Search', 14, 16, 45, secondary=True)
            self.level = self._label(header, '', 16, 0, 33, align=TextNode.ACenter)
            self.runtime = self._label(header, '', 16, 0, 25, align=TextNode.ARight)
            self.caption = self._label(header, 'Controls not connected', 14, 0, 45,
                                       align=TextNode.ARight, secondary=True)
            for text, baseline in SECTION_LABELS:
                self._label(panel, text, 14, 16, baseline, secondary=True)
            for name, rect in panel_controls().items():
                button = self._own(DirectButton(
                    parent=panel, text=name, text_scale=16,
                    text_fg=TEXT_SECONDARY, text_align=TextNode.ACenter,
                    text_pos=(rect.width / 2, -rect.height / 2 - 5),
                    pos=(rect.x, 0, -rect.y), frameSize=(0, rect.width, -rect.height, 0),
                    frameColor=BG_SECONDARY, relief=DGG.FLAT, borderWidth=(1, 1),
                    state=DGG.DISABLED))
                self.buttons[name] = button
            self._label(panel, 'Playback Speed', 14, 16, SPEED_LABEL_Y, secondary=True)
            self.speed = self._own(DirectSlider(
                parent=panel, pos=(SPEED_RECT.x, 0, -SPEED_RECT.y),
                frameSize=(0, SPEED_RECT.width, -SPEED_RECT.height, 0),
                frameColor=BG_SECONDARY, relief=DGG.FLAT, range=(.25, 4), value=1,
                pageSize=0, state=DGG.DISABLED, thumb_state=DGG.DISABLED,
                thumb_relief=DGG.FLAT, thumb_frameColor=HUD_BORDER,
                thumb_frameSize=(-6, 6, -10, 10)))
            self._label(panel, '1.0x', 16, 141, SPEED_VALUE_Y,
                        align=TextNode.ACenter, secondary=True)
            self._label(panel, 'Controls not connected', 14, 141, PANEL_FOOTER_Y,
                        align=TextNode.ACenter, secondary=True)
            self.metric_labels = [self._label(status, text, 14, 0, 21, secondary=True)
                                  for text in METRIC_LABELS]
            self.metric_values = [self._label(status, UNKNOWN, 18, 0, 46) for _ in METRIC_LABELS]
            self.warning = self._label(self.root, 'Minimum window size: 1024 x 720',
                                       16, 0, 0, align=TextNode.ACenter)
            self.warning.hide()
            self.update_view_model(model)
        except BaseException:
            self.dispose()
            raise

    def _own(self, widget):
        self._widgets.append(widget)
        return widget

    def _label(self, parent, text, size, x, baseline, *, align=None, secondary=False):
        return self._own(self._Label(
            parent=parent, text=text, text_scale=size, text_fg=TEXT_SECONDARY if secondary else TEXT_PRIMARY,
            text_align=self._TextNode.ALeft if align is None else align,
            pos=(x, 0, -baseline), relief=None, frameColor=(0, 0, 0, 0),
            state='disabled'))

    def _fit_text(self, label, text, max_width):
        """Elide unusually long caller data; never shrink all HUD text on resize."""
        node = self._TextNode('HUDTextMeasure')
        size = label['text_scale'][0]
        if node.calcWidth(text) * size <= max_width:
            label['text'] = text
            return
        while text and node.calcWidth(text + '…') * size > max_width:
            text = text[:-1]
        label['text'] = text + '…'

    def apply_layout(self, layout):
        if self._disposed:
            return
        self.layout = layout
        for surface in self.surfaces.values():
            surface.show() if layout.supported else surface.hide()
        if not layout.supported:
            self.warning.setPos(layout.width / 2, 0, -layout.height / 2)
            self.warning.show()
            return
        self.warning.hide()
        for name, surface in self.surfaces.items():
            rect = getattr(layout, name)
            surface.setPos(rect.x, 0, -rect.y)
            surface['frameSize'] = (0, rect.width, -rect.height, 0)
            self._inners[name]['frameSize'] = (1, rect.width - 1, 1 - rect.height, -1)
        width = layout.header.width
        self.level.setX(width / 2)
        self.runtime.setX(width - 16)
        self.caption.setX(width - 16)
        self._fit_text(self.level, self.model.level_label, width - 680)
        self._fit_text(self.runtime, self.model.runtime_status, 230)
        cell = (layout.status.width - 32) / 5
        for index, (label, value, text) in enumerate(zip(
                self.metric_labels, self.metric_values, metric_values(self.model))):
            label.setX(16 + index * cell)
            value.setX(16 + index * cell)
            self._fit_text(value, text, cell - 12)

    def update_view_model(self, model):
        if not isinstance(model, HudViewModel):
            raise ValueError('Expected HudViewModel.')
        if self._disposed:
            raise RuntimeError('HUD is disposed.')
        self.model = model
        self.level['text'], self.runtime['text'] = model.level_label, model.runtime_status
        for label, value in zip(self.metric_values, metric_values(model)):
            label['text'] = value
        if self.layout is not None:
            self.apply_layout(self.layout)

    def dispose(self):
        if self._disposed:
            return
        self._disposed = True
        for widget in reversed(self._widgets):
            widget.destroy()
        self._widgets.clear()
        self.buttons.clear()
        self.root.removeNode()
