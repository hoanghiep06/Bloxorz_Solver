"""Shared look & feel for the menus, with Light / Dark themes.

Colours are module globals rewritten by set_theme(); always read them as
``ui.NAME`` (never ``from ui_theme import NAME``) so theme switches take effect.
All coordinates are client pixels on pixel2d (origin top-left, y grows down).
"""
import math


def rgba(hex_value, alpha=1.0):
    return tuple(int(hex_value[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (alpha,)


WHITE = (1, 1, 1, 1)

THEMES = {
    'light': dict(INK='273B50', MUTED='61778B', LINE='D1DEE8',
                  PAPER='FFFFFF', PAPER_HOVER='E7EFF5', PAPER_PRESSED='D1DEE8',
                  PRIMARY='273B50', PRIMARY_HOVER='3B5772', PRIMARY_PRESSED='1B2B3C',
                  ON_PRIMARY='FFFFFF', CARD='FFFFFF',
                  DISABLED='E7EFF5', DISABLED_TEXT='9FB0C0',
                  GOLD='F5B83D', GOLD_OFF='D1DEE8'),
    'dark': dict(INK='E8EEF4', MUTED='9FB0C0', LINE='3A4F63',
                 PAPER='22313F', PAPER_HOVER='2C3E50', PAPER_PRESSED='1A2631',
                 PRIMARY='5B9BE0', PRIMARY_HOVER='73ADEB', PRIMARY_PRESSED='4380C4',
                 ON_PRIMARY='FFFFFF', CARD='18222C',
                 DISABLED='1C2733', DISABLED_TEXT='5A6B7B',
                 GOLD='F5B83D', GOLD_OFF='3A4F63'),
}
CURRENT = 'light'


def set_theme(name):
    """Switch palette. Widgets already on screen must be rebuilt/restyled."""
    global CURRENT
    palette = THEMES.get(name, THEMES['light'])
    CURRENT = name if name in THEMES else 'light'
    for key, value in palette.items():
        globals()[key] = rgba(value)


set_theme('light')


def rounded_rect(width, height, radius, color):
    """Rounded rectangle NodePath, top-left at (0, 0), extends right/down (z negative)."""
    from panda3d.core import (Geom, GeomNode, GeomTriangles, GeomVertexData,
                              GeomVertexFormat, GeomVertexWriter, NodePath,
                              TransparencyAttrib)
    radius = max(0, min(radius, width / 2, height / 2))
    corners = ((width - radius, -radius, 90), (width - radius, -height + radius, 0),
               (radius, -height + radius, -90), (radius, -radius, -180))
    points = []
    for cx, cz, start in corners:
        for step in range(9):
            angle = math.radians(start - step * 10)
            points.append((cx + radius * math.cos(angle), cz + radius * math.sin(angle)))
    data = GeomVertexData('rounded', GeomVertexFormat.getV3c4(), Geom.UHStatic)
    data.setNumRows(len(points) + 1)
    vertex, col = GeomVertexWriter(data, 'vertex'), GeomVertexWriter(data, 'color')
    vertex.addData3(width / 2, 0, -height / 2)
    col.addData4(*color)
    for x, z in points:
        vertex.addData3(x, 0, z)
        col.addData4(*color)
    triangles = GeomTriangles(Geom.UHStatic)
    for i in range(len(points)):
        triangles.addVertices(0, 1 + i, 1 + (i + 1) % len(points))
    geom = Geom(data)
    geom.addPrimitive(triangles)
    node = GeomNode('rounded')
    node.addGeom(geom)
    path = NodePath(node)
    path.setTwoSided(True)
    path.setTransparency(TransparencyAttrib.MAlpha)
    return path


def _radius(height):
    return min(height * .3, 24)


def style_button(button, primary):
    width, height = button.dims
    radius = _radius(height)
    states = ((PRIMARY, PRIMARY_PRESSED, PRIMARY_HOVER, DISABLED) if primary
              else (PAPER, PAPER_PRESSED, PAPER_HOVER, DISABLED))
    button['geom'] = tuple(rounded_rect(width - 2, height - 2, radius - 1, c) for c in states)
    button['text_fg'] = ON_PRIMARY if primary else INK
    button.border['geom'] = rounded_rect(width, height, radius, PRIMARY if primary else LINE)


def make_button(parent, text, x, y, width, height, command, *, primary=False,
                size=22, enabled=True, text_y=.5):
    """Rounded button. Returns the DirectButton; its outline is ``.border``."""
    from direct.gui.DirectGui import DirectButton, DirectFrame
    from direct.gui import DirectGuiGlobals as DGG
    from panda3d.core import TextNode
    border = DirectFrame(parent=parent, relief=None, pos=(x, 0, -y),
                         geom=rounded_rect(width, height, _radius(height), LINE))
    inner_h = height - 2
    button = DirectButton(
        parent=border, text=text, text_scale=size, text_align=TextNode.ACenter,
        text_pos=(width / 2 - 1, -inner_h * text_y - size * .3),
        pos=(1, 0, -1), frameSize=(0, width - 2, -inner_h, 0), relief=None,
        geom=rounded_rect(width - 2, inner_h, _radius(height) - 1, PAPER),
        command=command, state=DGG.NORMAL if enabled else DGG.DISABLED)
    button.border, button.dims = border, (width, height)
    style_button(button, primary)
    if not enabled:
        button['text_fg'] = DISABLED_TEXT
    return button

def make_label(parent, text, size, x, y, *, color=None, align='left'):
    """y is the text baseline."""
    from direct.gui.DirectGui import DirectLabel
    from panda3d.core import TextNode
    modes = {'left': TextNode.ALeft, 'center': TextNode.ACenter, 'right': TextNode.ARight}
    return DirectLabel(parent=parent, text=text, text_scale=size,
                       text_fg=INK if color is None else color, text_align=modes[align],
                       pos=(x, 0, -y), relief=None, frameColor=(0, 0, 0, 0), state='disabled')


def make_card(parent, x, y, width, height, alpha=.94):
    from direct.gui.DirectGui import DirectFrame
    from direct.gui import DirectGuiGlobals as DGG
    border = DirectFrame(parent=parent, relief=DGG.FLAT, frameColor=LINE,
                         frameSize=(0, width, -height, 0), pos=(x, 0, -y))
    inner = DirectFrame(parent=border, relief=DGG.FLAT,
                        frameColor=(CARD[0], CARD[1], CARD[2], alpha),
                        frameSize=(1, width - 1, 1 - height, -1))
    return border, inner


def make_slider(parent, x, y, width, height, value, command):
    """Horizontal 0..1 slider whose top-left is (x, y)."""
    from direct.gui.DirectGui import DirectSlider
    from direct.gui import DirectGuiGlobals as DGG
    return DirectSlider(
        parent=parent, pos=(x + width / 2, 0, -(y + height / 2)),
        frameSize=(-width / 2, width / 2, -height / 2, height / 2),
        frameColor=LINE, relief=DGG.FLAT, range=(0, 1), value=value, pageSize=.1,
        command=command, thumb_relief=DGG.FLAT, thumb_frameColor=PRIMARY,
        thumb_frameSize=(-9, 9, -14, 14))


def make_star(parent, x, y, radius, on=True):
    """Flat 5-point star polygon centred at (x, y). Returns its NodePath."""
    from panda3d.core import (Geom, GeomNode, GeomTriangles, GeomVertexData,
                              GeomVertexFormat, GeomVertexWriter)
    color_value = GOLD if on else GOLD_OFF
    data = GeomVertexData('star', GeomVertexFormat.getV3c4(), Geom.UHStatic)
    data.setNumRows(11)
    vertex, color = GeomVertexWriter(data, 'vertex'), GeomVertexWriter(data, 'color')
    vertex.addData3(0, 0, 0)
    color.addData4(*color_value)
    for i in range(10):
        angle = math.pi / 2 + i * math.pi / 5
        r = radius if i % 2 == 0 else radius * .42
        vertex.addData3(r * math.cos(angle), 0, r * math.sin(angle))
        color.addData4(*color_value)
    triangles = GeomTriangles(Geom.UHStatic)
    for i in range(10):
        triangles.addVertices(0, 1 + i, 1 + (i + 1) % 10)
    geom = Geom(data)
    geom.addPrimitive(triangles)
    node = GeomNode('Star')
    node.addGeom(geom)
    path = parent.attachNewNode(node)
    path.setPos(x, 0, -y)
    path.setTwoSided(True)
    return path