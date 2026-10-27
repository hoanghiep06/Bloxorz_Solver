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
    'light': dict(GUIDE_PANEL='EFF6FD', GUIDE_BORDER='B7D0E8',
                  GUIDE_INK='17324D', GUIDE_BODY='294763', GUIDE_MUTED='405E78', INK='F1F7F1', MUTED='BDCEC7', LINE='779D91',
                  PAPER='102C29', PAPER_HOVER='23443C', PAPER_PRESSED='081D1B',
                  PRIMARY='85440C', PRIMARY_HOVER='AA5B13', PRIMARY_PRESSED='633107',
                  ON_PRIMARY='FFD06D', CARD='102722',
                  DISABLED='1B302B', DISABLED_TEXT='758B82',
                  GOLD='FFB82E', GOLD_OFF='40574B'),
    'dark': dict(GUIDE_PANEL='0B1D35', GUIDE_BORDER='355574',
                 GUIDE_INK='F4F8FF', GUIDE_BODY='E2ECF7', GUIDE_MUTED='BFD0E3', INK='F1F6FF', MUTED='AEC6DE', LINE='617F9F',
                 PAPER='0B1D35', PAPER_HOVER='1D3655', PAPER_PRESSED='071326',
                 PRIMARY='85400A', PRIMARY_HOVER='A95713', PRIMARY_PRESSED='602D08',
                 ON_PRIMARY='FFD06D', CARD='0A172D',
                 DISABLED='14243A', DISABLED_TEXT='6D829C',
                 GOLD='FFB82E', GOLD_OFF='3D516B'),
}
CURRENT = 'light'


def set_theme(name):
    """Switch palette. Widgets already on screen must be rebuilt/restyled."""
    global CURRENT
    palette = THEMES.get(name, THEMES['light'])
    CURRENT = name if name in THEMES else 'light'
    for key, value in palette.items():
        globals()[key] = rgba(value, .90 if key in ('PAPER','CARD') else 1.)


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
        shade = 1.07 if z > -height*.45 else .92
        col.addData4(*(min(1,c*shade) for c in color[:3]), color[3])
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


def rounded_outline(width, height, radius, color, thickness=1):
    """True hollow frame, leaving the translucent fill visible over scenery."""
    from panda3d.core import (Geom,GeomNode,GeomTriangles,GeomVertexData,
        GeomVertexFormat,GeomVertexWriter,NodePath,TransparencyAttrib)
    def boundary(w,h,r,ox=0,oz=0):
        points=[]
        for cx,cz,start in ((w-r,-r,90),(w-r,-h+r,0),(r,-h+r,-90),(r,-r,-180)):
            for step in range(9):
                angle=math.radians(start-step*10)
                points.append((cx+r*math.cos(angle)+ox,cz+r*math.sin(angle)+oz))
        return points
    outer=boundary(width,height,radius)
    inner=boundary(width-2*thickness,height-2*thickness,max(0,radius-thickness),thickness,-thickness)
    data=GeomVertexData('GlassOutline',GeomVertexFormat.getV3c4(),Geom.UHStatic)
    v,c=GeomVertexWriter(data,'vertex'),GeomVertexWriter(data,'color')
    for ring in (outer,inner):
        for x,z in ring:v.addData3f(x,0,z);c.addData4f(*color)
    triangles=GeomTriangles(Geom.UHStatic);n=len(outer)
    for i in range(n):
        j=(i+1)%n
        triangles.addVertices(i,j,n+j);triangles.addVertices(i,n+j,n+i)
    geom=Geom(data);geom.addPrimitive(triangles)
    node=GeomNode('GlassOutline');node.addGeom(geom)
    path=NodePath(node);path.setTwoSided(True);path.setTransparency(TransparencyAttrib.MAlpha)
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
    button.border['geom'] = rounded_outline(width, height, radius, GOLD if primary else LINE)


def make_button(parent, text, x, y, width, height, command, *, primary=False,
                size=22, enabled=True, text_y=.5):
    """Rounded button. Returns the DirectButton; its outline is ``.border``."""
    from direct.gui.DirectGui import DirectButton, DirectFrame
    from direct.gui import DirectGuiGlobals as DGG
    from panda3d.core import TextNode
    border = DirectFrame(parent=parent, relief=None, pos=(x, 0, -y),
                         geom=rounded_outline(width, height, _radius(height), LINE))
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
                       text_shadow=(0.01,0.025,0.025,.85), text_shadowOffset=(.05,.06),
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
