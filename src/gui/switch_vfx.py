"""Presentation-only switch rigs and one bounded, timeline-sampled elemental VFX pool.

No tasks, timers, transitions, lights, RNG, bridge inference or teleport actors.
"""
from dataclasses import dataclass
from functools import lru_cache
import math
import weakref
from panda3d.core import NodePath,TransparencyAttrib,ShaderInput,LVecBase4f
from src.gui.advanced_contracts import SwitchVisualKind as Kind
from src.gui.animation_math import smoothstep
from src.gui.animation_contracts import EventKind as E
from src.gui.elemental_switches import switch_parts,PALETTE,annulus
from src.gui.mesh_factory import MeshBuilder
from src.gui.geometry_math import cell_to_world


_POOLS=weakref.WeakSet()


def clear_transients_for_theme(root,theme):
    for pool in tuple(_POOLS):
        if not pool.root.isEmpty() and root.isAncestorOf(pool.root):pool.theme_changed(theme)


def ramp(t,a,b):return smoothstep(max(0.,min(1.,(t-a)/(b-a))))


@dataclass(frozen=True)
class SwitchFrame:
    press: float
    pulse: float
    spread: float


def switch_frame(kind,u):
    """Different pressure/charge profiles normalized to the supplied event window."""
    if kind is Kind.SOFT:
        return SwitchFrame(ramp(u,0,.20)*(1-ramp(u,.52,1)),math.sin(math.pi*u)**2,0.)
    if kind is Kind.HEAVY:
        return SwitchFrame(ramp(u,0,.25)*(1-ramp(u,.72,1)),ramp(u,.18,.48)*(1-ramp(u,.65,1)),0.)
    return SwitchFrame(.5*math.sin(math.pi*u)**2,ramp(u,0,.4)*(1-ramp(u,.72,1)),
                       ramp(u,.18,.6)*(1-ramp(u,.76,1)))


class SwitchVisualRig:
    def __init__(self,parent,definition,rows,cols,pitch):
        self.kind=definition.kind;self.pitch=pitch
        self.variants=[];self.actuators=[]
        self.roots=tuple(parent.attachNewNode('ElementalSwitch-'+definition.switch_id+('-on' if on else '-off')) for on in (False,True))
        xy=cell_to_world(*definition.cell,rows=rows,cols=cols,pitch=pitch)
        for active,root in zip((False,True),self.roots):
            root.setPos(*xy,0)
            for theme in ('light','dark'):
                holder=root.attachNewNode('TileTheme-'+theme);self.variants.append((theme,holder))
                base,moving=switch_parts(self.kind,theme,active,pitch)
                holder.attachNewNode(base)
                for i,mesh in enumerate(moving):
                    actor=holder.attachNewNode('SwitchActuator-'+str(i));actor.attachNewNode(mesh)
                    self.actuators.append((holder,actor,i))

    def pose(self,active,frame=SwitchFrame(0,0,0)):
        self.roots[0].hide() if active else self.roots[0].show()
        self.roots[1].show() if active else self.roots[1].hide()
        for holder,actor,i in self.actuators:
            # Only the inset actuator moves; the socket never sinks into the floor.
            actor.setPos(((-1 if i==0 else 1)*.035*self.pitch*frame.spread) if self.kind is Kind.SPLIT else 0,
                         0,-.018*self.pitch*frame.press)
            actor.setShaderInput(ShaderInput('elemental_pulse',LVecBase4f(frame.pulse,0,0,0),10))


@lru_cache(maxsize=4)
def particle_mesh(theme):
    p=PALETTE[theme];b=MeshBuilder('IceChip' if theme=='dark' else 'EmeraldLeaf')
    if theme=='light':
        # A folded leaf silhouette, not a recoloured crystal shard.
        points=((-1,0,0),(0,-.5,.16),(1,0,0),(0,.5,.16))
        b.face(points,(0,0,1),p['energy']);b.face(tuple(reversed(points)),(0,0,-1),p['detail'])
    else:
        points=((0,0,1),(1,0,0),(0,1,0),(-1,0,0),(0,-1,0),(0,0,-1))
        for i in range(4):
            for indices in ((0,i+1,(i+1)%4+1),(5,(i+1)%4+1,i+1)):
                tri=[points[j] for j in indices]
                from panda3d.core import Vec3
                normal=(Vec3(*tri[1])-Vec3(*tri[0])).cross(Vec3(*tri[2])-Vec3(*tri[0]))
                b.face(tri,normal,p['highlight'] if i%2 else p['energy'])
    return b.finish()


@lru_cache(maxsize=4)
def pulse_mesh(theme):
    p=PALETTE[theme]
    return annulus('ElementalPulse',.96,1.,0,.008,1.,p['highlight'],p['energy'],theme,3,segments=32)


class SwitchEffectPool:
    """At most 3 live local effects × 16 particles. All nodes allocated on load."""
    def __init__(self,parent,count,pitch):
        from src.gui.scene_style import SHADOW_MASK
        self.root=parent.attachNewNode('ElementalSwitchEffects')
        self.root.setLightOff(1);self.root.setShaderOff(10)
        self.root.setTransparency(TransparencyAttrib.MAlpha)
        self.root.setDepthWrite(False);self.root.setTwoSided(True)
        self.root.hide(SHADOW_MASK)
        self.pitch=pitch;self.slots=[];self.active=0;self.theme=None
        self._context=None;self._suppressed=False;_POOLS.add(self)
        for _ in range(min(3,count)):
            root=self.root.attachNewNode('SwitchPulseSlot');root.hide();variants={}
            for theme in ('light','dark'):
                skin=root.attachNewNode('TileTheme-'+theme)
                rings=tuple(skin.attachNewNode(pulse_mesh(theme)) for _ in range(2))
                particles=tuple(skin.attachNewNode(particle_mesh(theme)) for _ in range(16))
                variants[theme]=(skin,rings,particles)
            self.slots.append((root,variants))

    def theme_changed(self,theme):
        if self.theme is not None and theme!=self.theme:
            context=self._context
            self.release();self._context=context;self._suppressed=True
        self.theme=theme

    def reset(self,theme,context):
        if context!=self._context:self._suppressed=False
        self._context=context
        self.active=0;self.theme=theme
        for root,variants in self.slots:
            root.hide()
            for key,(skin,rings,particles) in variants.items():
                skin.show() if key==theme else skin.hide()

    def sample(self,kind,cell,u,rows,cols,*,handoff=False):
        if self._suppressed or self.active>=len(self.slots) or u<=0 or u>=1:return
        root,variants=self.slots[self.active];self.active+=1
        root.show();xy=cell_to_world(*cell,rows=rows,cols=cols,pitch=self.pitch)
        root.setPos(*xy,0)
        skin,rings,particles=variants[self.theme]
        p=PALETTE[self.theme];pulse=math.sin(math.pi*u)**2
        colour=p['energy']
        if handoff and self.theme=='light':
            blend=ramp(u,.45,.85);colour=tuple(a+(b-a)*blend for a,b in zip(colour,(.12,.87,1.,1.)))
        for i,ring in enumerate(rings):
            radius=(.42+.40*u+i*.035)*self.pitch
            if kind is Kind.HEAVY:radius*=.9
            ring.setScale(radius,radius,.25*self.pitch)
            ring.setZ((.09+i*.018)*self.pitch)
            ring.setX(((-1 if i==0 else 1)*.16*(1-u)*self.pitch) if kind is Kind.SPLIT else 0)
            ring.setColorScale(*colour[:3],pulse*(.45 if i==0 else .18))
        count=8 if kind is Kind.SOFT else 12 if kind is Kind.HEAVY else 16
        for i,particle in enumerate(particles):
            if i>=count:particle.hide();continue
            particle.show();t=math.tau*i/count+.17
            radius=(.48+.36*u)*self.pitch
            lift=(.10+(.24 if kind is Kind.SPLIT else .16)*math.sin(math.pi*u)) * self.pitch
            particle.setPos(math.cos(t)*radius,math.sin(t)*radius,lift+.035*(i%3)*self.pitch)
            particle.setHpr(i*41+u*100,i*27+u*90,u*180)
            size=(.014+.009*(i%3))*self.pitch
            particle.setScale(size*(1.5 if self.theme=='light' else .8),size,size)
            particle.setColorScale(*colour[:3],pulse*.7)

    def release(self):
        self.active=0;self._context=None;self._suppressed=False
        for root,variants in self.slots:
            root.hide()
            for skin,rings,particles in variants.values():
                for node in (*rings,*particles):node.setPos(0,0,0);node.setHpr(0,0,0);node.setScale(1);node.clearColorScale()

    def dispose(self):
        self.release();_POOLS.discard(self);self.root.removeNode();self.slots.clear()
