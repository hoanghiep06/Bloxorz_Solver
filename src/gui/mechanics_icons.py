"""Guide-only top-view glyphs matching actual mesh dimensions and materials.

Cached geometry stores vertex colours; Fragile also reuses the game's stone
texture. No offscreen cameras or per-frame rendering are needed.
"""
from functools import lru_cache
import math
from panda3d.core import (Geom,GeomNode,GeomTriangles,GeomVertexData,
    GeomVertexFormat,GeomVertexWriter,NodePath,Filename,PNMImage,Texture,
    RenderState,TextureAttrib)
from src.gui.advanced_mesh_factory import PALETTES,FLAG_POLE,FLAG_CLOTH,FLAG_GOLD
from src.gui.mesh_factory import GOAL_THEME_COLORS

IDS=('goal','bridge','soft_switch','heavy_switch','split_switch','fragile','void')


def rect(x,y,hx,hy,color):
    return (( (x-hx,y-hy),(x+hx,y-hy),(x+hx,y+hy),(x-hx,y+hy)),color)


def segment(a,b,width,color):
    dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
    nx,ny=-dy/length*width/2,dx/length*width/2
    return (((a[0]+nx,a[1]+ny),(a[0]-nx,a[1]-ny),
             (b[0]-nx,b[1]-ny),(b[0]+nx,b[1]+ny)),color)


def icon_polygons(key,theme='light'):
    if key not in IDS:raise KeyError(key)
    p=PALETTES[theme];out=[]
    def plate(hx,hy,fill,edge):
        out.extend((rect(0,0,hx,hy,edge),rect(0,0,hx-.025,hy-.025,fill)))
    if key=='goal':
        c=GOAL_THEME_COLORS[theme]
        out.extend((rect(0,-.10,.48,.48,c['rim']),rect(0,-.10,.38,.38,c['floor']),
                    rect(-.40,.19,.025,.40,FLAG_POLE),rect(-.40,.61,.055,.045,FLAG_GOLD),
                    (((-.375,.55),(.35,.32),(-.375,.10)),FLAG_CLOTH)))
    elif key=='bridge':
        plate(.48,.48,p['BRIDGE_TOP'],p['BRIDGE_EDGE'])
        for y in (-.28,0,.28):out.append(rect(0,y,.39,.03,p['BRIDGE_RIB']))
    elif key=='soft_switch':
        # Real mesh: .40 dark base; cyan annulus .30/.23, not a filled button.
        for i in range(48):
            a,b=math.tau*i/48,math.tau*(i+1)/48
            out.append((((0,0),(.40*math.cos(a),.40*math.sin(a)),(.40*math.cos(b),.40*math.sin(b))),p['SWITCH_BASE']))
            out.append((tuple((r*math.cos(t),r*math.sin(t)) for r,t in ((.30,a),(.30,b),(.23,b),(.23,a))),p['SOFT_COLOR']))
    elif key=='heavy_switch':
        plate(.37,.37,p['SWITCH_BASE'],p['SWITCH_BASE_EDGE'])
        for x in (-.15,.15):out.append(rect(x,0,.06,.26,p['HEAVY_COLOR']))
    elif key=='split_switch':
        plate(.38,.31,p['SWITCH_BASE'],p['SWITCH_BASE_EDGE'])
        for x in (-.19,.19):out.append(rect(x,0,.12,.17,p['SPLIT_COLOR']))
    elif key=='fragile':
        plate(.48,.48,p['FRAGILE'],p['FRAGILE_EDGE'])
        for a,b in (((-.36,-.32),(0,-.04)),((0,-.04),(.32,.34)),
                    ((0,-.04),(-.24,.30)),((.12,.10),(.37,.03))):
            out.append(segment(a,b,.045,p['CRACK']))
    else:
        # Open gap with edge only: no floor polygon in its centre.
        color=(.28,.39,.48,1) if theme=='light' else (.68,.78,.88,1)
        for a,b in (((-.46,-.46),(.46,-.46)),((.46,-.46),(.46,.46)),
                    ((.46,.46),(-.46,.46)),((-.46,.46),(-.46,-.46))):
            out.append(segment(a,b,.05,color))
    return tuple(out)


@lru_cache(maxsize=1)
def _fragile_texture():
    from src.gui.visual_materials import ROOT
    image=PNMImage()
    if not image.read(Filename.fromOsSpecific(str(ROOT/'materials/fragile.png'))):
        raise RuntimeError('Missing visual material asset: fragile')
    # The material's alpha encodes emission, NOT transparency. UI has no temple
    # shader, so use opaque RGB regardless of the current 3D shader/fallback.
    image.removeAlpha()
    texture=Texture('GuideFragileRGB');texture.load(image)
    texture.setMinfilter(Texture.FTLinearMipmapLinear)
    texture.setMagfilter(Texture.FTLinear)
    texture.setWrapU(Texture.WMClamp);texture.setWrapV(Texture.WMClamp)
    return texture


def _geometry(key,polygons,*,textured=False):
    format=GeomVertexFormat.getV3c4t2() if textured else GeomVertexFormat.getV3c4()
    data=GeomVertexData('GuideGlyph-'+key,format,Geom.UHStatic)
    vertex,color=GeomVertexWriter(data,'vertex'),GeomVertexWriter(data,'color')
    uv=GeomVertexWriter(data,'texcoord') if textured else None
    primitive=GeomTriangles(Geom.UHStatic);count=0
    for points,rgba in polygons:
        for x,y in points:
            vertex.addData3(x*1.65,0,y*1.65);color.addData4(*rgba)
            if uv is not None:uv.addData2(x/.91+.5,y/.91+.5)
        for i in range(1,len(points)-1):primitive.addVertices(count,count+i,count+i+1)
        count+=len(points)
    geom=Geom(data);geom.addPrimitive(primitive)
    return geom


@lru_cache(maxsize=14)
def _mesh(key,theme):
    polygons=icon_polygons(key,theme)
    node=GeomNode('MechanicIcon-'+key)
    if key=='fragile':
        node.addGeom(_geometry(key,polygons[:1])) # existing tile rim
        # Replace the flat palette fill with the very same orange stone and hot
        # branching fissures used by FragileSurface. Raised mesh cracks remain.
        surface=(rect(0,0,.455,.455,(1,1,1,1)),)
        node.addGeom(_geometry(key,surface,textured=True),
                     RenderState.make(TextureAttrib.make(_fragile_texture())))
        node.addGeom(_geometry(key,polygons[2:]))
    else:
        node.addGeom(_geometry(key,polygons))
    return node


def mechanic_icon(key,theme='light'):
    path=NodePath('MechanicIcon-'+key)
    path.attachNewNode(_mesh(key,theme))
    path.setTwoSided(True)
    path.setLightOff(1);path.setShaderOff(1)
    # Polygons form flat graphic layers in insertion order, independent of depth.
    path.setDepthTest(False);path.setDepthWrite(False)
    return path
