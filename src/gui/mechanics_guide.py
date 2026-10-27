"""One small DirectGUI rail and one reusable help card; no gameplay bindings/tasks."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from panda3d.core import (CardMaker, Filename, Geom, GeomNode, GeomTriangles,
    GeomVertexData, GeomVertexFormat, GeomVertexWriter, NodePath, TextNode,
    TexturePool, TextureStage)
from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel
from direct.gui import DirectGuiGlobals as DGG
from src.gui import ui_theme as ui, icons
from src.gui.layout import Rect, MIN_WIDTH, MIN_HEIGHT
from src.gui.mechanics_guide_data import MECHANICS, BY_ID

RAIL_WIDTH, BUTTON_SIZE, STEP, CARD_WIDTH = 58, 40, 48, 260


@lru_cache(maxsize=2)
def _guide_font(semibold=False):
    """Private copies of Panda's bundled face; never alter the global UI font.

    A small same-colour outline supplies synthetic medium/semibold weight
    without another asset. Outline units are points, not screen pixels.
    """
    font=TextNode.getDefaultFont().makeCopy()
    font.clear()
    font.setPixelsPerUnit(64)
    font.setScaleFactor(4)
    font.setOutline((1,1,1,1),.16 if semibold else .055,.1)
    return font


@dataclass(frozen=True)
class GuideLayout:
    rail: Rect
    card: Rect | None
    reserved: int


def guide_layout(width, height, selected=None, card_height=230):
    """Client pixels; header ends at 132, metrics start at height-94."""
    if width < MIN_WIDTH or height < MIN_HEIGHT:
        return None
    rail_height=24+7*STEP+8
    top=136+max(0,(height-94-136-rail_height)//2)
    rail=Rect(width-20-RAIL_WIDTH,top,RAIL_WIDTH,rail_height)
    card=None
    if selected is not None:
        index=next(i for i,m in enumerate(MECHANICS) if m.id==selected)
        y=min(max(136,top+24+index*STEP),height-104-card_height)
        card=Rect(rail.x-12-CARD_WIDTH,y,CARD_WIDTH,card_height)
    return GuideLayout(rail,card,width-(card.x if card else rail.x)+12)


def mechanic_icon(mechanic_id):
    """Vector silhouettes match the live 3D flag, ribs and switch glyphs."""
    rect,band,circle=icons._rect,icons._band,icons._circle_points
    square=[(-.8,-.8),(.8,-.8),(.8,.8),(-.8,.8)]
    inside=[(-.64,-.64),(.64,-.64),(.64,.64),(-.64,.64)]
    if mechanic_id=='goal':
        tris=rect(-.66,-.85,-.49,.9)+[((-.49,.82),(.85,.33),(-.49,-.05))]+rect(-.85,-.9,-.25,-.78)
    elif mechanic_id=='bridge':
        tris=rect(-.88,-.82,-.72,.82)+rect(.72,-.82,.88,.82)
        for z in (-.6,0,.6):tris+=rect(-.72,z-.14,.72,z+.14)
    elif mechanic_id=='soft_switch':
        tris=band(circle(.82),circle(.59))
    elif mechanic_id=='heavy_switch':
        tris=rect(-.65,-.8,-.24,.8)+rect(.24,-.8,.65,.8)
    elif mechanic_id=='split_switch':
        tris=rect(-.9,-.5,-.15,.5)+rect(.15,-.5,.9,.5)
        tris+=[((-.9,.5),(-.65,.78),(-.15,.5)),((.15,.5),(.4,.78),(.9,.5))]
    elif mechanic_id=='fragile':
        tris=band(square,inside)
        points=[(-.28,.7),(.12,.22),(-.16,-.18),(.24,-.7)]
        for (x,z),(xx,zz) in zip(points,points[1:]):
            tris += [((x-.08,z),(x+.08,z),(xx+.08,zz)),((x-.08,z),(xx+.08,zz),(xx-.08,zz))]
        tris += [((-.04,.1),(.55,.33),(.05,.25))]
    else:
        tris=band(square,inside)+rect(-.6,-.56,.6,-.43)
    data=GeomVertexData('MechanicIcon-'+mechanic_id,GeomVertexFormat.getV3(),Geom.UHStatic)
    writer=GeomVertexWriter(data,'vertex');primitive=GeomTriangles(Geom.UHStatic)
    for i,tri in enumerate(tris):
        for x,z in tri:writer.addData3f(x,0,z)
        primitive.addVertices(i*3,i*3+1,i*3+2)
    geom=Geom(data);geom.addPrimitive(primitive)
    node=GeomNode('MechanicIcon-'+mechanic_id);node.addGeom(geom)
    path=NodePath(node);path.setTwoSided(True);path.setLightOff(1);path.setShaderOff(1)
    return path


class MechanicsGuide:
    def __init__(self, parent, *, on_change=None):
        self.root=parent.attachNewNode('MechanicsGuide',-10)
        self._on_change=on_change
        self._widgets=[];self._disposed=False;self._visible=False
        self.selected=None;self.layout=None;self._size=None;self._card_height=230
        self.root.hide()
        # Continue the existing panorama in the area reserved by the viewport.
        # This is a GUI crop of an existing asset, not another camera or window.
        cm=CardMaker('GuideBackdrop');cm.setFrame(0,1,-1,0)
        self.backdrop=self.root.attachNewNode(cm.generate())
        self.backdrop.setLightOff(1);self.backdrop.setShaderOff(1)
        self.rail=self._own(DirectFrame(parent=self.root,relief=None,state=DGG.NORMAL))
        self.heading=self._label(self.rail,'GUIDE',12,RAIL_WIDTH/2,17,center=True,semibold=True)
        self.buttons={};self._icons={}
        for i,item in enumerate(MECHANICS):
            button=self._own(DirectButton(parent=self.rail,relief=None,
                frameSize=(0,40,-40,0),pos=(9,0,-(24+i*STEP)),pressEffect=0,
                command=lambda key=item.id:self.show_mechanic(key)))
            self.buttons[item.id]=button
            icon=mechanic_icon(item.id);icon.reparentTo(button)
            icon.setPos(20,-.02,-20);icon.setScale(12)
            self._icons[item.id]=icon
        self.shadow=self.root.attachNewNode('GuideCardShadow')
        self.card=self._own(DirectFrame(parent=self.root,relief=None,state=DGG.NORMAL))
        self.card_border=self.card.attachNewNode('GuideCardBorder')
        self.large_icon=self.card.attachNewNode('LargeMechanicIcon')
        self.large_icon.setPos(34,-.03,-36);self.large_icon.setScale(18)
        self.title=self._label(self.card,'',18,62,42,semibold=True)
        self.body=self._label(self.card,'',16,16,82)
        self.body['text_wordwrap']=(CARD_WIDTH-32)/16
        self.note=self._label(self.card,'',14,16,150)
        self.note['text_wordwrap']=(CARD_WIDTH-32)/14
        self.close_button=self._own(DirectButton(parent=self.card,text='X',text_scale=14,
            text_font=_guide_font(True),
            text_pos=(13,-18),frameSize=(0,26,-26,0),pos=(CARD_WIDTH-34,-.05,-8),
            relief=None,pressEffect=0,command=self.close_card))
        self.card.hide();self.shadow.hide()
        self.apply_theme(ui.CURRENT)

    def _own(self, widget):
        self._widgets.append(widget);return widget

    def _label(self,parent,text,size,x,y,center=False,semibold=False):
        return self._own(DirectLabel(parent=parent,text=text,text_scale=size,
            text_font=_guide_font(semibold),
            text_align=TextNode.ACenter if center else TextNode.ALeft,
            pos=(x,-.03,-y),frameColor=(0,0,0,0),relief=None,state=DGG.DISABLED))

    @staticmethod
    def _rows(text,size):
        node=TextNode('GuideMeasure');node.setFont(_guide_font())
        node.setWordwrap((CARD_WIDTH-32)/size);node.setText(text)
        return node.getNumRows()

    def show_mechanic(self, mechanic_id):
        if self._disposed:return
        item=BY_ID[mechanic_id]
        if self.selected==mechanic_id:
            self.close_card();return
        self.selected=mechanic_id
        self.title['text']=item.name
        self.body['text']=item.description
        self.note['text']=item.note
        note_y=82+self._rows(item.description,16)*20+16
        self.note.setZ(-note_y)
        self._card_height=note_y+self._rows(item.note,14)*18+16
        for child in self.large_icon.getChildren():child.removeNode()
        icon=mechanic_icon(mechanic_id);icon.reparentTo(self.large_icon)
        icon.setColor(*ui.rgba(item.accent))
        self._restyle()
        if self._size:self.apply_layout(*self._size)
        if self._on_change:self._on_change()

    def close_card(self):
        if self._disposed:return
        self.selected=None
        self.card.hide();self.shadow.hide()
        self._restyle()
        if self._size:self.apply_layout(*self._size)
        if self._on_change:self._on_change()

    def apply_theme(self, theme):
        """Use existing ui_theme tokens; no separate theme manager/listener."""
        if self._disposed:return
        self._theme=theme if theme in ui.THEMES else 'light'
        palette=ui.THEMES[self._theme]
        self._panel=ui.rgba(palette['GUIDE_PANEL'],.94)
        self._border=ui.rgba(palette['GUIDE_BORDER'])
        self._ink=ui.rgba(palette['GUIDE_INK'])
        self._body_ink=ui.rgba(palette['GUIDE_BODY'])
        self._muted=ui.rgba(palette['GUIDE_MUTED'])
        self.heading['text_fg']=self.title['text_fg']=self._ink
        self.body['text_fg']=self._body_ink
        self.note['text_fg']=self._muted
        self.close_button['text_fg']=self._ink
        self._restyle()
        root=Path(__file__).resolve().parents[2]/'assets/backgrounds'
        name='winter-temple.png' if self._theme=='dark' else 'jungle-temple.png'
        texture=TexturePool.loadTexture(Filename.fromOsSpecific(str(root/name)))
        if texture is not None:
            self.backdrop.setTexture(texture,1)
            self._image_aspect=texture.getXSize()/texture.getYSize()
        if self._size:self.apply_layout(*self._size)

    def _restyle(self):
        self.rail['geom']=ui.rounded_rect(RAIL_WIDTH,24+7*STEP+8,12,self._panel)
        self.card['geom']=ui.rounded_rect(CARD_WIDTH,self._card_height,12,self._panel)
        self.card['frameSize']=(0,CARD_WIDTH,-self._card_height,0)
        for node in self.card_border.getChildren():node.removeNode()
        ui.rounded_outline(CARD_WIDTH,self._card_height,12,self._border).reparentTo(self.card_border)
        for node in self.shadow.getChildren():node.removeNode()
        ui.rounded_rect(CARD_WIDTH+4,self._card_height+4,13,(0,0,0,.18)).reparentTo(self.shadow)
        for item in MECHANICS:
            accent=ui.rgba(item.accent);button=self.buttons[item.id]
            selected=self.selected==item.id
            outline=accent if selected else self._border
            states=[]
            for i in range(4):
                fill=tuple(self._panel[j]*.86+accent[j]*.14 for j in range(3))+(1.,) if selected or i in (1,2) else self._panel
                geom=ui.rounded_rect(40,40,8,fill)
                ui.rounded_outline(40,40,8,outline,2 if selected else 1).reparentTo(geom)
                states.append(geom)
            button['geom']=tuple(states)
            self._icons[item.id].setColor(*accent)
        self.close_button['geom']=tuple(ui.rounded_rect(26,26,6,c) for c in (self._panel,self._border,self._border,self._panel))

    def apply_layout(self,width,height):
        if self._disposed:return
        self._size=(width,height)
        self.layout=guide_layout(width,height,self.selected,self._card_height)
        if self.layout is None:
            self.root.hide();return
        r=self.layout.rail
        self.rail.setPos(r.x,0,-r.y)
        self.rail['frameSize']=(0,r.width,-r.height,0)
        start=width-self.layout.reserved
        self.backdrop.setPos(start,.05,0)
        self.backdrop.setScale(self.layout.reserved,1,height)
        stage=TextureStage.getDefault()
        aspect=width/height;image=getattr(self,'_image_aspect',aspect)
        su,sv=(1.,image/aspect) if aspect>image else (aspect/image,1.)
        self.backdrop.setTexScale(stage,su*self.layout.reserved/width,sv)
        self.backdrop.setTexOffset(stage,(1-su)/2+su*start/width,(1-sv)/2)
        if self.layout.card:
            c=self.layout.card
            self.card.setPos(c.x,-.02,-c.y);self.shadow.setPos(c.x+3,0,-c.y-4)
            self.card.show();self.shadow.show()
        else:self.card.hide();self.shadow.hide()
        self.root.show() if self._visible else self.root.hide()

    @property
    def reserved_width(self):
        return self.layout.reserved if self.layout else 0

    def set_visible(self,visible):
        self._visible=visible
        if self._size:self.apply_layout(*self._size)

    def contains_pointer_pixels(self,x,y):
        if not self._visible or self.layout is None or self._disposed:return False
        # The entire reserved strip is outside the gameplay viewport.
        return self._size[0]-self.reserved_width<=x<=self._size[0] and 0<=y<=self._size[1]

    def dispose(self):
        if self._disposed:return
        self._disposed=True
        for widget in reversed(self._widgets):widget.destroy()
        self._widgets.clear();self.buttons.clear();self._icons.clear()
        self.root.removeNode()
        self._on_change=None
