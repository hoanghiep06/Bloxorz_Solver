"""Tutorial overlay: a modal panel listing keyboard, mouse and HUD controls.

Open with the HUD "Tutorial" button or H / F1. Close with the Close button,
Esc, H / F1, or by clicking the dimmed backdrop. While open, gameplay input is
suspended and restored on close.
"""
from src.gui import ui_theme as ui

PANEL_W, PANEL_H = 760, 480
ROW_START, ROW_STEP, TEXT_SIZE = 108, 34, 20

KEYBOARD = (
    ('W / Up', 'Roll up'),
    ('S / Down', 'Roll down'),
    ('A / Left', 'Roll left'),
    ('D / Right', 'Roll right'),
    ('Space', 'Switch cube (split)'),
    ('R', 'Restart level'),
    ('C', 'Change camera view'),
    ('Enter / P', 'Play / pause solution'),
    ('H / F1', 'Show / hide help'),
)
MOUSE = (
    ('Click', 'Roll toward click'),
    ('Hover', 'Arrow lights up'),
    ('Hover icon', 'Shows its name'),
)
BUTTONS = (
    ('Back arrow', 'Exit to menu'),
    ('Circle arrow', 'Restart level'),
    ('Sparkle', 'AI Solver on/off'),
    ('Eye', 'Change camera'),
    ('Play / Step', 'Replay solution'),
)
LEFT_KEY_X, LEFT_DESC_X = 30, 150
RIGHT_KEY_X, RIGHT_DESC_X = 400, 540


class TutorialOverlay:
    def __init__(self, app, controller):
        from direct.gui import DirectGuiGlobals as DGG
        from direct.gui.DirectGui import DirectButton, DirectFrame
        self.app, self.controller = app, controller
        self._widgets = []
        self._visible = False
        self._restore_input = True
        self._disposed = False
        self.root = app.pixel2d.attachNewNode('TutorialOverlay')
        self.root.setBin('gui-popup', 50)
        self.root.hide()
        try:
            self.backdrop = self._own(DirectButton(
                parent=self.root, relief=DGG.FLAT, frameColor=(0, 0, 0, 0.55),
                frameSize=(0, 1, -1, 0), pressEffect=0, command=self.hide))
            self.panel = self._own(DirectFrame(
                parent=self.root, relief=DGG.FLAT, frameColor=ui.PAPER,
                frameSize=(0, PANEL_W, -PANEL_H, 0)))
            self._label('How to play', 32, 30, 50)
            self._label('Keyboard', 18, LEFT_KEY_X, 90, muted=True)
            self._label('Mouse', 18, RIGHT_KEY_X, 90, muted=True)
            self._rows(KEYBOARD, LEFT_KEY_X, LEFT_DESC_X, ROW_START)
            self._rows(MOUSE, RIGHT_KEY_X, RIGHT_DESC_X, ROW_START)
            buttons_y = ROW_START + len(MOUSE) * ROW_STEP + 16
            self._label('HUD buttons', 18, RIGHT_KEY_X, buttons_y - 18, muted=True)
            self._rows(BUTTONS, RIGHT_KEY_X, RIGHT_DESC_X, buttons_y + 18)
            close = ui.make_button(self.panel, 'Close', (PANEL_W - 160) / 2, PANEL_H - 70,
                                   160, 46, self.hide, size=22, enabled=True)
            self._own(close.border)
            self._own(close)
            ui.style_button(close, primary=True)
        except BaseException:
            self.dispose()
            raise
        app.accept('h', self.toggle)
        app.accept('f1', self.toggle)

    # ------------------------------------------------------------ builders
    def _own(self, widget):
        self._widgets.append(widget)
        return widget

    def _label(self, text, size, x, baseline, *, muted=False):
        return self._own(ui.make_label(self.panel, text, size, x, baseline,
                                       color=ui.MUTED if muted else ui.INK))

    def _rows(self, rows, key_x, desc_x, first_baseline):
        for index, (key, desc) in enumerate(rows):
            baseline = first_baseline + index * ROW_STEP
            self._label(key, TEXT_SIZE, key_x, baseline)
            self._label(desc, TEXT_SIZE, desc_x, baseline, muted=True)

    # ------------------------------------------------------------ behaviour
    @property
    def visible(self):
        return self._visible

    def toggle(self):
        if self._disposed:
            return
        if self._visible:
            self.hide()
        elif self.controller.input_enabled:
            self.show()

    def show(self):
        if self._disposed or self._visible:
            return
        width, height = self.app.win.getXSize(), self.app.win.getYSize()
        if width <= 0 or height <= 0:
            return
        self.backdrop['frameSize'] = (0, width, -height, 0)
        self.panel.setPos((width - PANEL_W) / 2, 0, -(height - PANEL_H) / 2)
        self._restore_input = self.controller.input_enabled
        self.controller.input_enabled = False
        self._visible = True
        self.root.show()
        self.app.accept('escape', self.hide)

    def hide(self):
        if self._disposed or not self._visible:
            return
        self._visible = False
        self.root.hide()
        self.app.ignore('escape')
        self.controller.input_enabled = self._restore_input

    def dispose(self):
        if self._disposed:
            return
        if self._visible:
            self.hide()
        self._disposed = True
        self.app.ignore('h')
        self.app.ignore('f1')
        for widget in reversed(self._widgets):
            widget.destroy()
        self._widgets.clear()
        self.root.removeNode()