"""Tutorial overlay: a modal panel listing keyboard, mouse and HUD controls,
followed by a second page that introduces the special tiles.

Open with the HUD "Tutorial" button or H / F1. Close with the Close button,
Esc, H / F1, or by clicking the dimmed backdrop. While open, gameplay input is
suspended and restored on close. Use the Next / Back buttons to switch pages.
"""
import math

from src.gui import ui_theme as ui
from src.gui.advanced_mesh_factory import (
    PALETTES, THEMES, FLAG_POLE, FLAG_CLOTH, FLAG_GOLD,
)
from src.gui.mesh_factory import FLOOR_TOP, FLOOR_EDGE, GOAL_THEME_COLORS
from src.gui.scene_style import FLOOR_TINT

PANEL_W, PANEL_H = 800, 540
ROW_START, ROW_STEP, TEXT_SIZE = 108, 34, 18

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
    ('Guide icons', 'Open mechanics help'),
)
BUTTONS = (
    ('Back arrow', 'Exit to menu'),
    ('Circle arrow', 'Restart level'),
    ('Sparkle', 'AI Solver on/off'),
    ('Eye', 'Change camera'),
    ('Play / Step', 'Replay solution'),
)
LEFT_KEY_X, LEFT_DESC_X = 30, 150
RIGHT_KEY_X, RIGHT_DESC_X = 390, 525

# ---------------------------------------------------------------------------
# Trang 2: icon sàn đặc biệt, vẽ nhìn từ trên xuống theo đúng mesh trong game.
# Hệ toạ độ icon: ô vuông đơn vị, tâm (0, 0), x sang phải, y lên, ô rộng 0.96.
# ---------------------------------------------------------------------------
TILE_ROW_START, TILE_ROW_STEP = 100, 58
SWATCH = 44
ICON_X = 30
TILE_NAME_X = 96
PAGE_COUNT = 2
CIRCLE_POINTS = 28


def _tint(color, theme):
    t = FLOOR_TINT[theme]
    return (color[0] * t[0], color[1] * t[1], color[2] * t[2], 1.0)


def _sq(hx, hy, color, cx=0.0, cy=0.0):
    return ([(cx - hx, cy - hy), (cx + hx, cy - hy), (cx + hx, cy + hy), (cx - hx, cy + hy)], color)


def _disc(radius, color, cx=0.0, cy=0.0):
    return ([(cx + radius * math.cos(math.tau * i / CIRCLE_POINTS),
              cy + radius * math.sin(math.tau * i / CIRCLE_POINTS))
             for i in range(CIRCLE_POINTS)], color)


def _seg(a, b, width, color):
    """Đoạn thẳng dày `width` đi từ a tới b (dùng cho vết nứt)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / length * width / 2, dx / length * width / 2
    return ([(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny),
             (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)], color)


def _plate(hx, hy, edge, color, cx=0.0, cy=0.0, bevel=.02):
    return [_sq(hx, hy, edge, cx, cy), _sq(hx - bevel, hy - bevel, color, cx, cy)]


def _floor(theme):
    """Sàn thường nằm dưới các nút, có tint giống ngoài game."""
    return _plate(.48, .48, _tint(FLOOR_EDGE, theme), _tint(FLOOR_TOP, theme))


def _goal(theme):
    c = GOAL_THEME_COLORS[theme]
    polys = [_sq(.48, .48, c['rim']), _sq(.38, .38, c['wall']), _sq(.31, .31, c['floor'])]
    # Cờ: cột trắng, đỉnh vàng, vải đỏ hình tam giác (giống make_flag_mesh).
    px = -.12
    polys += [_sq(.025, .34, FLAG_POLE, px, .0),
              _sq(.06, .06, FLAG_GOLD, px, .37),
              ([(px + .025, .30), (px + .025, .06), (px + .46, .18)], FLAG_CLOTH)]
    return polys


def _fragile(theme):
    p = PALETTES[theme]
    polys = _plate(.48, .48, p['FRAGILE_EDGE'], p['FRAGILE'])
    for a, b in (((-.36, -.32), (0, -.04)), ((0, -.04), (.32, .34)),
                 ((0, -.04), (-.24, .30)), ((.12, .10), (.37, .03))):
        polys.append(_seg(a, b, .05, p['CRACK']))
    return polys


def _bridge(theme):
    p = PALETTES[theme]
    polys = _plate(.48, .48, p['BRIDGE_EDGE'], p['BRIDGE_TOP'])
    for y in (-.28, 0, .28):
        polys.append(_sq(.39, .03, p['BRIDGE_RIB'], 0, y))
    return polys


def _soft(theme):
    p = PALETTES[theme]
    return _floor(theme) + [_disc(.40, p['SWITCH_BASE']), _disc(.29, p['SOFT_COLOR'])]


def _heavy(theme):
    p = PALETTES[theme]
    return (_floor(theme) + _plate(.37, .37, p['SWITCH_BASE_EDGE'], p['SWITCH_BASE'])
            + [_sq(.085, .28, p['HEAVY_COLOR']), _sq(.28, .085, p['HEAVY_COLOR'])])


def _split(theme):
    p = PALETTES[theme]
    polys = _floor(theme) + _plate(.38, .31, p['SWITCH_BASE_EDGE'], p['SWITCH_BASE'])
    for x in (-.19, .19):
        polys.append(_sq(.12, .25, p['SPLIT_COLOR'], x, 0))
    return polys


# (tên, mô tả, hàm dựng icon theo theme)
TILES = (
    ('Goal tile (flag)',
     'Stand the block upright on the hole to finish the level.', _goal),
    ('Fragile tile',
     'Breaks if the block stands upright on it. Lying down or a 1x1 cube is safe.', _fragile),
    ('Round switch',
     'Pressed by any part of the block. Opens or closes its linked bridge.', _soft),
    ('Cross switch (+)',
     'Heavy: only works when the block stands upright on it.', _heavy),
    ('Split switch (two plates)',
     'Splits the block into two 1x1 cubes. Space swaps the active cube.', _split),
    ('Bridge',
     'Appears or disappears when its switch is pressed; some stay permanently.', _bridge),
)


def make_tile_icon(parent, polys, size, name):
    """Gộp các đa giác lồi thành một NodePath phẳng, không đèn, vẽ theo thứ tự."""
    from panda3d.core import (Geom, GeomNode, GeomTriangles, GeomVertexData,
                              GeomVertexFormat, GeomVertexWriter, TransparencyAttrib)
    count = sum(len(points) for points, _ in polys)
    data = GeomVertexData(name, GeomVertexFormat.getV3c4(), Geom.UHStatic)
    data.setNumRows(count)
    vertex, color = GeomVertexWriter(data, 'vertex'), GeomVertexWriter(data, 'color')
    triangles = GeomTriangles(Geom.UHStatic)
    base = 0
    for points, rgba in polys:
        for x, y in points:
            vertex.addData3(x * size, 0, y * size)
            color.addData4(*rgba)
        for i in range(1, len(points) - 1):
            triangles.addVertices(base, base + i, base + i + 1)
        base += len(points)
    geom = Geom(data)
    geom.addPrimitive(triangles)
    node = GeomNode(name)
    node.addGeom(geom)
    path = parent.attachNewNode(node)
    path.setTwoSided(True)
    path.setLightOff(1)
    path.setShaderOff(1)
    path.setTransparency(TransparencyAttrib.MAlpha)
    return path


class TutorialOverlay:
    def __init__(self, app, controller):
        from direct.gui import DirectGuiGlobals as DGG
        from direct.gui.DirectGui import DirectButton, DirectFrame
        self.app, self.controller = app, controller
        self._widgets = []
        self._page_items = {page: [] for page in range(PAGE_COUNT)}
        self._icons = []             # (theme, NodePath) của trang 2
        self._page = 0
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
            self._title = self._label('How to play', 32, 30, 50)

            # --- Trang 1: điều khiển
            self._label('Keyboard', 18, LEFT_KEY_X, 90, muted=True, page=0)
            self._label('Mouse', 18, RIGHT_KEY_X, 90, muted=True, page=0)
            self._rows(KEYBOARD, LEFT_KEY_X, LEFT_DESC_X, ROW_START, page=0)
            self._rows(MOUSE, RIGHT_KEY_X, RIGHT_DESC_X, ROW_START, page=0)
            buttons_y = ROW_START + len(MOUSE) * ROW_STEP + 16
            self._label('HUD buttons', 18, RIGHT_KEY_X, buttons_y - 18, muted=True, page=0)
            self._rows(BUTTONS, RIGHT_KEY_X, RIGHT_DESC_X, buttons_y + 18, page=0)

            # --- Trang 2: sàn đặc biệt
            self._build_tiles_page()

            # --- Nút điều hướng (dùng chung)
            by = PANEL_H - 70
            close = ui.make_button(self.panel, 'Close', (PANEL_W - 160) / 2, by,
                                   160, 46, self.hide, size=22, enabled=True)
            self._own(close.border)
            self._own(close)
            ui.style_button(close, primary=True)

            nxt = ui.make_button(self.panel, 'Next', PANEL_W - 190, by,
                                 160, 46, lambda: self._set_page(1), size=22, enabled=True)
            self._own(nxt.border, page=0)
            self._own(nxt, page=0)
            back = ui.make_button(self.panel, 'Back', 30, by,
                                  160, 46, lambda: self._set_page(0), size=22, enabled=True)
            self._own(back.border, page=1)
            self._own(back, page=1)

            self._indicator = self._label('1 / 2', 16, PANEL_W / 2 + 120, by + 30, muted=True)
            self._set_page(0)
        except BaseException:
            self.dispose()
            raise
        app.accept('h', self.toggle)
        app.accept('f1', self.toggle)

    # ------------------------------------------------------------ builders
    def _own(self, widget, page=None):
        self._widgets.append(widget)
        if page is not None:
            self._page_items[page].append(widget)
        return widget

    def _label(self, text, size, x, baseline, *, muted=False, page=None):
        return self._own(ui.make_label(self.panel, text, size, x, baseline,
                                       color=ui.MUTED if muted else ui.INK), page)

    def _rows(self, rows, key_x, desc_x, first_baseline, page=None):
        for index, (key, desc) in enumerate(rows):
            baseline = first_baseline + index * ROW_STEP
            self._label(key, TEXT_SIZE, key_x, baseline, page=page)
            self._label(desc, TEXT_SIZE, desc_x, baseline, muted=True, page=page)

    def _build_tiles_page(self):
        self._label('Special tiles on the map', 18, 30, 90, muted=True, page=1)
        for index, (name, desc, builder) in enumerate(TILES):
            top = TILE_ROW_START + index * TILE_ROW_STEP
            for theme in THEMES:
                icon = make_tile_icon(self.panel, builder(theme), SWATCH, f'TileIcon-{index}-{theme}')
                icon.setPos(ICON_X + SWATCH / 2, 0, -(top + SWATCH / 2))
                icon.hide()
                self._icons.append((theme, icon))
            self._label(name, TEXT_SIZE, TILE_NAME_X, top + 18, page=1)
            self._label(desc, 16, TILE_NAME_X, top + 40, muted=True, page=1)

    def _refresh_icons(self):
        """Chỉ hiện icon của trang 2 và đúng theme hiện tại."""
        theme = getattr(ui, 'CURRENT', 'light')
        if theme not in THEMES:
            theme = 'light'
        for icon_theme, icon in self._icons:
            if self._page == 1 and icon_theme == theme:
                icon.show()
            else:
                icon.hide()

    # ------------------------------------------------------------ behaviour
    def _set_page(self, page):
        self._page = max(0, min(PAGE_COUNT - 1, page))
        for index, items in self._page_items.items():
            for widget in items:
                widget.show() if index == self._page else widget.hide()
        self._title['text'] = 'How to play' if self._page == 0 else 'Special tiles'
        self._indicator['text'] = f'{self._page + 1} / {PAGE_COUNT}'
        self._refresh_icons()

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
        self._set_page(0)            # luôn mở từ trang đầu; đồng thời cập nhật theme icon
        self._visible = True
        self.root.show()

    def hide(self):
        if self._disposed or not self._visible:
            return
        self._visible = False
        self.root.hide()
        self.controller.input_enabled = self._restore_input

    def dispose(self):
        if self._disposed:
            return
        if self._visible:
            self.hide()
        self._disposed = True
        self.app.ignore('h')
        self.app.ignore('f1')
        for _, icon in self._icons:
            if not icon.isEmpty():
                icon.removeNode()
        self._icons.clear()
        for widget in reversed(self._widgets):
            widget.destroy()
        self._widgets.clear()
        self._page_items = {page: [] for page in range(PAGE_COUNT)}
        self.root.removeNode()