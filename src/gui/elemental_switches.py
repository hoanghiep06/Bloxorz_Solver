"""Shared sculpted switch definitions: 3D parts and readable Guide top silhouettes.

No Core, tasks, collisions, state inference, textures or global animation clock.
All raised ornament is <= .15 pitch; the existing floor remains the sole support.
"""
from functools import lru_cache
import math
from panda3d.core import GeomNode,Mat4,Vec3,NodePath
from src.gui.advanced_contracts import SwitchVisualKind as Kind
from src.gui.mesh_factory import MeshBuilder,make_beveled_box_mesh
from src.gui.switch_materials import apply


def rgb(s):return tuple(int(s[i:i+2],16)/255 for i in (0,2,4))+(1.,)


PALETTE={
    'light':dict(base=rgb('294C40'),stone=rgb('687D65'),edge=rgb('987A4D'),
        detail=rgb('496D4F'),energy=rgb('37D1AC'),highlight=rgb('A0FFE0'),shadow=rgb('235A48')),
    'dark':dict(base=rgb('17334F'),stone=rgb('244A68'),edge=rgb('3B91D1'),
        detail=rgb('A8E9FA'),energy=rgb('32D9FF'),highlight=rgb('E8FAFF'),shadow=rgb('235B83')),
}
RING_OUTER,RING_INNER=.33,.245
BAR_CENTRES=(-.18,.18)
CRYSTAL_CENTRES=(-.20,.20)
BAR_HALF=(.075,.28)
CRYSTAL_FOOTPRINT=((-1,-.72),(0,-1),(1,-.72),(1, .72),(0,1),(-1,.72))


def crystal_outline(theme):
    """One cut definition for the actual gem and its Guide reduction."""
    return CRYSTAL_FOOTPRINT if theme=='dark' else ((-1,-.65),(-.65,-1),(.65,-1),(1,-.65),(1,.65),(.65,1),(-.65,1),(-1,.65))


def combine(name,parts):
    node=GeomNode(name)
    for part in parts:
        for i in range(part.getNumGeoms()):node.addGeom(part.modifyGeom(i),part.getGeomState(i))
    holder=NodePath(node);holder.flattenStrong()
    result=holder.node();holder.detachNode()
    return result


def box(name,size,centre,pitch,top,side,edge,theme,role=0,active=False,angle=0):
    mesh=make_beveled_box_mesh(name=name,dimensions=tuple(s*pitch for s in size),
        bevel=min(.009,min(size)/4)*pitch,top_color=top,side_color=side,edge_color=edge)
    transform=Mat4.rotateMat(angle,Vec3(0,0,1))*Mat4.translateMat(*(x*pitch for x in centre))
    for i in range(mesh.getNumGeoms()):mesh.modifyGeom(i).transformVertices(transform)
    return apply(mesh,theme,role,active)


def annulus(name,inner,outer,z0,z1,pitch,colour,side,theme,role=0,active=False,segments=32):
    b=MeshBuilder(name)
    for i in range(segments):
        a,c=math.tau*i/segments,math.tau*(i+1)/segments
        def p(r,t,z):return (r*math.cos(t)*pitch,r*math.sin(t)*pitch,z*pitch)
        b.face((p(inner,a,z1),p(outer,a,z1),p(outer,c,z1),p(inner,c,z1)),(0,0,1),colour)
        b.face((p(inner,a,z0),p(outer,a,z0),p(outer,c,z0),p(inner,c,z0)),(0,0,-1),side)
        normal=(math.cos((a+c)/2),math.sin((a+c)/2),0)
        b.face((p(outer,a,z0),p(outer,c,z0),p(outer,c,z1),p(outer,a,z1)),normal,side)
        b.face((p(inner,a,z0),p(inner,c,z0),p(inner,c,z1),p(inner,a,z1)),tuple(-v for v in normal),side)
    return apply(b.finish(),theme,role,active)


def gem(name,x,pitch,palette,theme,active=False):
    b=MeshBuilder(name)
    # Emerald uses an octagonal cut; Sapphire a longer six-sided ice cut.
    outline=crystal_outline(theme)
    points=[((x+u*.105)*pitch,v*.17*pitch) for u,v in outline]
    z0,z1,peak=.055*pitch,.095*pitch,.145*pitch
    energy=palette['highlight'] if active else palette['energy']
    b.face([(u,v,z0) for u,v in points],(0,0,-1),palette['shadow'])
    for i,a in enumerate(points):
        c=points[(i+1)%len(points)]
        outer=Vec3(c[1]-a[1],a[0]-c[0],0)
        b.face(((a[0],a[1],z0),(c[0],c[1],z0),(c[0],c[1],z1),(a[0],a[1],z1)),outer,palette['edge'])
        tri=((a[0],a[1],z1),(c[0],c[1],z1),(x*pitch,0,peak))
        normal=(Vec3(*tri[1])-Vec3(*tri[0])).cross(Vec3(*tri[2])-Vec3(*tri[0]))
        b.face(tri,normal,energy if i%2 else palette['detail'] if theme=='dark' else palette['shadow'])
    return apply(b.finish(),theme,2,active)


def marks(palette,theme,pitch,kind):
    parts=[]
    if theme=='light':
        # Bronze chisel marks and small moss clumps have actual sculpted depth.
        for i in range(12 if kind is Kind.SOFT else 4):
            t=i*math.tau/(12 if kind is Kind.SOFT else 4)
            r=.365 if kind is Kind.SOFT else .33
            parts.append(box('BronzeRune',(.026,.052,.008),(r*math.cos(t),r*math.sin(t),.045),
                pitch,palette['edge'],palette['base'],palette['edge'],theme,1,angle=math.degrees(t)))
        for i in (1,4,7):
            t=i*2.1
            parts.append(box('MossCarving',(.056,.026,.009),(.34*math.cos(t),.30*math.sin(t),.037),
                pitch,palette['detail'],palette['base'],palette['detail'],theme,angle=i*41))
    else:
        # Frozen caps and short branching ice cracks are absent from Jungle.
        for i in range(6):
            t=i*math.tau/6
            r=.36 if kind is Kind.SOFT else .32
            parts.append(box('FrostCap',(.056,.033,.013),(r*math.cos(t),r*math.sin(t),.044),
                pitch,palette['highlight'],palette['edge'],palette['detail'],theme,angle=i*60))
        for x,y,angle in ((-.24,.19,35),(.26,-.20,-30),(-.24,-.23,-60),(.24,.23,60)):
            parts.append(box('FrozenFissure',(.10,.011,.004),(x,y,.039),pitch,
                palette['detail'],palette['edge'],palette['detail'],theme,2,angle=angle))
    return parts


@lru_cache(maxsize=48)
def switch_parts(kind,theme='light',active=False,pitch=1.):
    p=PALETTE[theme];base=[];moving=[]
    glow=p['highlight'] if active else p['energy']
    if kind is Kind.SOFT:
        # The filled centre is a thin decorative insert, not a new support tile.
        base.append(box('RingSocket',(.50,.50,.02),(0,0,.015),pitch,p['stone'],p['base'],p['stone'],theme))
        base.append(annulus('AncientOuterSocket',.32,.405,.005,.04,pitch,p['stone'],p['base'],theme,
                            segments=16 if theme=='dark' else 32))
        base.append(annulus('BronzeOrFrostRim',.355,.39,.041,.049,pitch,p['edge'],p['base'],theme,1,
                            segments=16 if theme=='dark' else 32))
        moving.append(combine('EnergyRing',[
            annulus('SculptedPressureRing',RING_INNER,RING_OUTER,.061,.104,pitch,p['edge'],p['shadow'],theme,1,
                    segments=16 if theme=='dark' else 32),
            annulus('EnergyInlay',.264,.306,.105,.111,pitch,glow,p['shadow'],theme,3,active,
                    segments=16 if theme=='dark' else 32)]))
    else:
        size=(.79,.73,.035) if kind is Kind.HEAVY else (.79,.64,.035)
        base.append(box('AncientSwitchPlinth',size,(0,0,.0175),pitch,p['stone'],p['base'],p['edge'],theme))
        if kind is Kind.HEAVY:
            for x in BAR_CENTRES:
                moving.append(combine('PressureBar',[
                    box('PressureHousing',(.15,.56,.068),(x,0,.094),pitch,
                        p['detail'] if theme=='dark' else p['edge'],p['shadow'],p['edge'],theme,2 if theme=='dark' else 1,active),
                    box('PressureEnergySlot',(.045,.46,.005),(x,0,.1305),pitch,glow,p['shadow'],glow,theme,3,active),
                    *[box('IceFracture' if theme=='dark' else 'BronzeLatch',(.125,.013,.004),(x,y,.134),pitch,
                          p['highlight'] if theme=='dark' else p['shadow'],p['shadow'],p['detail'],theme,2,active,angle=25 if theme=='dark' else 0)
                      for y in (-.15,.15)]]))
        else:
            moving.extend(gem('TwinElementalCrystal',x,pitch,p,theme,active) for x in CRYSTAL_CENTRES)
            base.append(box('TwinEnergyConnection',(.22,.018,.006),(0,0,.041),pitch,glow,p['base'],glow,theme,3,active))
    base.extend(marks(p,theme,pitch,kind))
    return combine(kind.value+'-ElementalBase',base),tuple(moving)


@lru_cache(maxsize=48)
def switch_mesh(kind,theme='light',active=False,pitch=1.):
    base,moving=switch_parts(kind,theme,active,pitch)
    return combine(kind.value.title()+'SwitchMesh',(base,*moving))


@lru_cache(maxsize=6)
def switch_icon_polygons(kind,theme):
    """Cache the actual idle mesh's top faces for the Rail and Help Card.

    Projecting existing triangles preserves carved runes, moss, frost, pressure
    latches and crystal facets. This is not a separate approximation of the
    switch. No render target, camera, shader or gameplay state is involved.
    """
    from panda3d.core import GeomVertexReader
    palette=PALETTE[theme]
    # Panda stores vertex colours as floats; recover the original palette tokens
    # so UI semantics do not depend on float32 roundoff or the active GSG.
    colours={tuple(round(v*255) for v in c):c for c in palette.values()}
    faces=[]
    for geom in switch_mesh(kind,theme).getGeoms():
        data=geom.getVertexData()
        vr=GeomVertexReader(data,'vertex');nr=GeomVertexReader(data,'normal')
        cr=GeomVertexReader(data,'color');vertices=[]
        while not vr.isAtEnd():
            point=tuple(vr.getData3f());normal=tuple(nr.getData3f());colour=tuple(cr.getData4f())
            colour=colours.get(tuple(round(v*255) for v in colour),colour)
            vertices.append((point,normal,colour))
        for primitive in geom.getPrimitives():
            triangles=primitive.decompose()
            for i in range(triangles.getNumPrimitives()):
                begin,end=triangles.getPrimitiveStart(i),triangles.getPrimitiveEnd(i)
                face=[vertices[triangles.getVertex(j)] for j in range(begin,end)]
                if len(face)!=3 or sum(n[2] for point,n,c in face)<=1e-6:continue
                points=tuple((p[0],p[1]) for p,n,c in face)
                area=sum(points[j][0]*points[(j+1)%3][1]-points[(j+1)%3][0]*points[j][1] for j in range(3))
                if abs(area)<1e-10:continue
                faces.append((sum(p[2] for p,n,c in face)/3,points,face[0][2]))
    # Flat GUI layers use painter order: socket first, raised details last.
    faces.sort(key=lambda face:face[0])
    return tuple((points,colour) for z,points,colour in faces)
