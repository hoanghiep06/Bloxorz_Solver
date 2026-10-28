"""Pooled procedural cyan teleport VFX. No assets, tasks, RNG or postprocess dependency.

Soft additive geometry supplies local glow even without bloom/GLSL. Depth testing
stays enabled: effects cannot draw through tiles or HUD, and cast no shadows.
"""
import math
from panda3d.core import (
    Geom, GeomNode, GeomTriangles, GeomVertexData, GeomVertexFormat,
    GeomVertexWriter, ColorBlendAttrib, TransparencyAttrib, Quat, Point3,
)
from src.gui.split_teleport_math import ramp, pulse

CYAN=(.08,.88,1.0)
BLUE=(.07,.30,1.0)
WHITE=(.65,1.,1.)
SEGMENTS=24


def mesh(name, vertices, colors, faces):
    data=GeomVertexData(name,GeomVertexFormat.getV3c4(),Geom.UHStatic)
    v,c=GeomVertexWriter(data,'vertex'),GeomVertexWriter(data,'color')
    for point,color in zip(vertices,colors):v.addData3(*point);c.addData4(*color)
    triangles=GeomTriangles(Geom.UHStatic)
    for face in faces:triangles.addVertices(*face)
    geom=Geom(data);geom.addPrimitive(triangles)
    node=GeomNode(name);node.addGeom(geom)
    return node


def ring_mesh():
    points,colors,faces=[],[],[]
    # Soft blue fringe, cyan core, transparent outer falloff: physical annulus,
    # not a large opaque billboard that would cover symbols on the board.
    for i in range(65):
        angle=math.tau*i/64
        for radius,color in ((.88,(*BLUE,0)),(.97,(*CYAN,.7)),
                             (1.0,(*WHITE,.95)),(1.03,(*CYAN,.7)),(1.14,(*BLUE,0))):
            points.append((radius*math.cos(angle),radius*math.sin(angle),0));colors.append(color)
    for i in range(64):
        for j in range(4):
            a=i*5+j;b=a+5
            faces.extend(((a,b,a+1),(a+1,b,b+1)))
    return mesh('CyanSoftAnnulus',points,colors,faces)


def tube_mesh():
    points,faces=[],[]
    for y in (0,1):
        points.extend((math.cos(math.tau*i/8),y,math.sin(math.tau*i/8)) for i in range(8))
    for i in range(8):
        j=(i+1)%8;faces.extend(((i,j,i+8),(j,j+8,i+8)))
    return mesh('EnergyTube',points,[(*WHITE,1)]*16,faces)


def spark_mesh():
    points=((0,0,1),(1,0,0),(0,1,0),(-1,0,0),(0,-1,0),(0,0,-1))
    faces=tuple(face for i in range(4) for face in ((0,i+1,(i+1)%4+1),(5,(i+1)%4+1,i+1)))
    return mesh('EnergyShard',points,[(*WHITE,1)]*6,faces)


class SplitTeleportVFX:
    """One bounded pool prewarmed on split-switch boards, reused by its manager."""
    def __init__(self, parent, *, pitch=1.):
        from src.gui.scene_style import SHADOW_MASK
        self.root=parent.attachNewNode('CinematicSplitTeleport')
        self.root.setLightOff(1);self.root.setShaderOff(1)
        self.root.setTransparency(TransparencyAttrib.MAlpha)
        self.root.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd,
                             ColorBlendAttrib.OIncomingAlpha,ColorBlendAttrib.OOne))
        self.root.setDepthWrite(False);self.root.setTwoSided(True)
        self.root.hide(SHADOW_MASK)
        self.pitch=pitch;self.plan=None;self.phase='IDLE';self._disposed=False
        ring,tube,spark=ring_mesh(),tube_mesh(),spark_mesh()
        def instance(name, geometry, parent=self.root):
            node=parent.attachNewNode(name);node.attachNewNode(geometry);return node
        self.source=self.root.attachNewNode('SourceCharge')
        self.rings=tuple(instance('SourceEnergyRing',ring,self.source) for _ in range(5))
        self.cage=self.source.attachNewNode('DisassemblyLattice')
        self.bands=tuple(instance('ScanBand',ring,self.cage) for _ in range(6))
        self.receivers=tuple(self.root.attachNewNode(f'Receiver-{i}') for i in range(2))
        self.receiver_rings=tuple(tuple(instance('ArrivalRing',ring,parent) for _ in range(3))
                                  for parent in self.receivers)
        self.cube_cages=tuple(self.root.attachNewNode(f'Reconstruction-{i}') for i in range(2))
        self.edges=tuple(tuple(instance('CubeEnergyEdge',tube,parent) for _ in range(12))
                         for parent in self.cube_cages)
        self.streams=tuple(tuple((instance('StreamHalo',tube),instance('StreamCore',tube))
                          for _ in range(SEGMENTS)) for _ in range(2))
        self.shards=tuple(instance('SourceShard',spark) for _ in range(28))
        self.tracers=tuple(tuple(instance('StreamTracer',spark) for _ in range(12)) for _ in range(2))
        self.arrival_sparks=tuple(tuple(instance('ArrivalSpark',spark) for _ in range(10)) for _ in range(2))
        self.release()

    def configure(self, plan):
        self.release();self.plan=plan
        source=plan.source
        self.source.setPos(*source.center)
        self.cage.setQuat(Quat(*source.quaternion))
        dimensions=source.nominal_dimensions
        for i,band in enumerate(self.bands):
            band.setPos(0,0,dimensions[2]*(i/5-.5))
            band.setScale(dimensions[0]*.68,dimensions[1]*.68,1)
        for index,key in enumerate(plan.cube_ids):
            target=plan.targets[key]
            self.receivers[index].setPos(target.center[0],target.center[1],.025*self.pitch)
            cage=self.cube_cages[index];cage.setPos(*target.center);cage.setQuat(Quat(*target.quaternion))
            from itertools import product
            edges=[]
            for axis in range(3):
                others=[j for j in range(3) if j!=axis]
                for signs in product((-1,1),repeat=2):
                    a=[0.,0.,0.];b=[0.,0.,0.]
                    a[axis],b[axis]=-.51*self.pitch,.51*self.pitch
                    for j,sign in zip(others,signs):a[j]=b[j]=sign*.51*self.pitch
                    edges.append((a,b))
            for node,(a,b) in zip(self.edges[index],edges):self._segment(node,a,b,.016*self.pitch)

    @staticmethod
    def _segment(node,a,b,radius):
        node.setPos(*a);node.lookAt(Point3(*b))
        length=math.sqrt(sum((b[i]-a[i])**2 for i in range(3)))
        node.setScale(radius,max(length,.0001),radius)

    @staticmethod
    def _alpha(node,amount,color=CYAN):
        node.setColorScale(*color,max(0,min(1,amount)))
        node.show() if amount>0 else node.hide()

    def sample(self,frame):
        if self._disposed:raise RuntimeError('Teleport VFX is disposed.')
        t=frame.progress;p=self.pitch;plan=self.plan
        self.phase=frame.phase
        if t<=0 or t>=1:
            self.root.hide();return
        self.root.show()
        from src.gui.scene_style import SHADOW_MASK
        self.root.hide(SHADOW_MASK)
        charge=pulse(t,0,.25,.56)
        self._alpha(self.source,charge)
        for i,node in enumerate(self.rings):
            # Three ascending rings and two tilted orbital rings wrap the 3D block.
            node.setPos(0,0,(-.8+((t*2.2+i*.25)%1)*2)*p)
            node.setScale((.67+.10*math.sin(t*math.tau*2+i))*p)
            node.setHpr(t*210+i*51,0 if i<3 else (42 if i==3 else -42),0)
        self.cage.setColorScale(*CYAN,pulse(t,.08,.31,.49))
        for i,node in enumerate(self.bands):
            node.setHpr(t*260+i*30,0,0)
        for i,node in enumerate(self.shards):
            angle=i*2.399963+t*5
            v=ramp(t,.24,.54)
            radius=p*(.48+.48*math.sin(math.pi*v))
            node.setPos(plan.source.center[0]+radius*math.cos(angle),
                        plan.source.center[1]+radius*math.sin(angle),
                        plan.source.center[2]+p*((i%7)/6-.5)*(1-v)+p*1.1*v)
            node.setHpr(i*31+t*210,i*19+t*180,0)
            node.setScale(p*(.025+.025*(i%3))*pulse(t,.21,.36,.58))
            self._alpha(node,pulse(t,.21,.36,.58),WHITE if i%4==0 else CYAN)
        travel=ramp(t,.38,.71)
        stream_envelope=pulse(t,.35,.53,.80)
        for index,key in enumerate(plan.cube_ids):
            for j,(halo,core) in enumerate(self.streams[index]):
                u0,u1=j/SEGMENTS,(j+1)/SEGMENTS
                a=plan.stream_point(index,u0);b=plan.stream_point(index,u1)
                lit=ramp(travel,u0,min(1,u0+1/SEGMENTS))
                pulse_width=.72+.28*math.sin(j*.8-t*36)
                self._segment(halo,a,b,p*(.07+.018*pulse_width))
                self._segment(core,a,b,p*(.012+.008*pulse_width))
                self._alpha(halo,stream_envelope*lit*.36,BLUE)
                self._alpha(core,stream_envelope*lit*.85,CYAN)
            for j,node in enumerate(self.tracers[index]):
                u=(travel-j*.037)
                on=0<u<1 and .38<t<.78
                point=plan.stream_point(index,max(0,min(1,u)))
                node.setPos(*point);node.setScale(p*(.055 if j==0 else .028))
                self._alpha(node,stream_envelope*(1-j/15) if on else 0,WHITE)
            arrival=pulse(t,.52,.79,1.)
            self._alpha(self.receivers[index],arrival)
            for j,node in enumerate(self.receiver_rings[index]):
                node.setZ(p*(.03+j*.36*(1-ramp(t,.76,1))))
                node.setScale(p*(.59+j*.14+.04*math.sin(t*24+j)))
                node.setHpr(t*(-160 if j%2 else 190),0,0)
            self._alpha(self.cube_cages[index],pulse(t,.64,.78,.98),WHITE)
            self.cube_cages[index].setScale(.83+.17*ramp(t,.70,.90))
            target=plan.targets[key].center
            for j,node in enumerate(self.arrival_sparks[index]):
                angle=math.tau*j/10-t*3
                radius=p*(.8-.2*ramp(t,.65,.90))
                node.setPos(target[0]+radius*math.cos(angle),target[1]+radius*math.sin(angle),
                            p*(.14+(j%3)*.3+.15*math.sin(t*18+j)))
                node.setScale(p*.034)
                self._alpha(node,pulse(t,.65,.80,.98))
            # Last beat resolves to the real existing active-cube indicator.
            if key==plan.active_id:
                self.receiver_rings[index][0].setColorScale(*WHITE,1.)
            else:self.receiver_rings[index][0].clearColorScale()

    def release(self):
        if self._disposed:return
        self.root.hide();self.phase='IDLE';self.plan=None

    def dispose(self):
        if self._disposed:return
        self.release();self.root.removeNode();self._disposed=True
