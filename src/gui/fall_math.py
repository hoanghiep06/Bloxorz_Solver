"""Deterministic visual loss of support, in world units (not metres).

No Core/Panda imports. An explicit FALL is required by the caller. Support squares
choose a visual contact only; they never validate a move or decide game failure.
"""
from dataclasses import dataclass,replace
import math
from src.gui.animation_math import (VisualPose,RollPlan,RollDirection,add,sub,scale,
    rotate,qmul,normalized,axis_angle,finite,vec,smoothstep)


@dataclass(frozen=True)
class FallTuning:
    gravity: float = 16.0             # pitches / second squared
    tip_time: float = .18
    partial_angle: float = .52        # radians before release
    fade_time: float = .20
    fade_depth: float = 1.1           # pitches below release centre
    angular_retention: float = .35

    def __post_init__(self):
        for name in ('gravity','tip_time','partial_angle','fade_time','fade_depth'):
            finite(getattr(self,name),name,minimum=.001)
        finite(self.angular_retention,'angular_retention')
        if self.angular_retention>1 or self.partial_angle>math.pi/2:
            raise ValueError('Angular tuning out of range.')


DEFAULT_TUNING=FallTuning()


def roll_angle(progress):
    s=smoothstep(progress)
    return math.pi/2*s*s*(2-s)


def roll_angular_velocity(progress,duration):
    s=smoothstep(progress)
    return math.pi/2*(4*s-3*s*s)*(6*progress*(1-progress))/duration


def around(pose,pivot,axis,angle):
    rotation=axis_angle(axis,angle)
    return VisualPose(add(pivot,rotate(rotation,sub(pose.center,pivot))),
                      normalized(qmul(rotation,pose.quaternion)),pose.nominal_dimensions)


def support_contact(pose,supports,pitch):
    """Return outward cardinal/contact for a *partial* supported footprint.

    Quarter-turn poses use grid-half envelopes, including the deliberate seams.
    Full support / no support have no invented pivot. Actual slabs keep their
    original .96 geometry; the .02 seam tolerance matches the rolling grid pivot.
    """
    ex,ey,ez=pose.extents;x,y,z=pose.center
    if abs(z-ez)>1e-6*pitch:return None
    hits=[(sx,sy) for sx,sy in supports
          if min(x+ex,sx+pitch/2)-max(x-ex,sx-pitch/2)>1e-6*pitch
          and min(y+ey,sy+pitch/2)-max(y-ey,sy-pitch/2)>1e-6*pitch]
    area=sum((min(x+ex,sx+pitch/2)-max(x-ex,sx-pitch/2))*
             (min(y+ey,sy+pitch/2)-max(y-ey,sy-pitch/2)) for sx,sy in hits)
    if not hits or area>=4*ex*ey-1e-6*pitch*pitch:return None
    dx=x-sum(sx for sx,sy in hits)/len(hits)
    dy=y-sum(sy for sx,sy in hits)/len(hits)
    if abs(dx)+abs(dy)<1e-8:return None
    if abs(dx)>=abs(dy):
        direction=RollDirection.RIGHT if dx>0 else RollDirection.LEFT
        edge=max(sx+pitch/2 for sx,sy in hits) if dx>0 else min(sx-pitch/2 for sx,sy in hits)
        pivot=(edge,y,0.)
    else:
        direction=RollDirection.UP if dy>0 else RollDirection.DOWN
        edge=max(sy+pitch/2 for sx,sy in hits) if dy>0 else min(sy-pitch/2 for sx,sy in hits)
        pivot=(x,edge,0.)
    return direction,pivot


def intersects_slab(pose,centre,pitch):
    """OBB vs unchanged .96 x .96 x .18 slab, using separating axes.

    Used once at plan construction to avoid tipping into a neighbour. Contact
    (including the existing tile seams) is not volume intersection.
    """
    world=((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
    basis=tuple(rotate(pose.quaternion,a) for a in world)
    x,y=centre
    delta=sub(pose.center,(x,y,-.09*pitch))
    half=tuple(v/2 for v in pose.nominal_dimensions)
    floor=(.48*pitch,.48*pitch,.09*pitch)
    def dot(a,b):return sum(x*y for x,y in zip(a,b))
    axes=list(world)+list(basis)
    for a in world:
        for b in basis:
            axes.append((a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]))
    for axis in axes:
        length=math.sqrt(dot(axis,axis))
        if length<1e-8:continue
        axis=scale(axis,1/length)
        ra=sum(abs(dot(axis,b))*h for b,h in zip(basis,half))
        rb=sum(abs(a)*h for a,h in zip(axis,floor))
        if abs(dot(axis,delta))>=ra+rb-1e-6*pitch:return False
    return True


@dataclass(frozen=True)
class FallSample:
    pose: VisualPose
    opacity: float
    phase: str


class FallPlan:
    """Sample any elapsed time: normal roll prefix -> tip -> ballistic release.

    Constructor values are frozen into a plan; sample never accumulates state.
    Existing RollPlan supplies the normal prefix and its quaternion convention.
    A flat/unsupported terminal without a reliable motion history starts at rest.
    """
    def __init__(self,start,*,duration=.9,pitch=1.,supports=(),roll_direction=None,
                 fall_distance=3.,tuning=DEFAULT_TUNING):
        if type(start) is not VisualPose:raise TypeError('Expected VisualPose.')
        finite(duration,'duration',minimum=.001);finite(pitch,'pitch',minimum=.001)
        finite(fall_distance,'fall_distance',minimum=.01)
        if type(tuning) is not FallTuning:raise TypeError('Expected FallTuning.')
        if roll_direction is not None and type(roll_direction) is not RollDirection:
            raise TypeError('Expected RollDirection.')
        for point in supports:vec(point,2,'support')
        self.start,self.duration,self.pitch,self.tuning=start,duration,pitch,tuning
        self.roll=None;self.pivot=None;self.axis=(0.,1.,0.)
        self.roll_end=self.tip_end=self.start_angle=self.start_omega=self.tip_alpha=0.
        self.case='unsupported';self.tip_start=start
        self.clearance='open'
        if roll_direction is not None:
            self.case='roll-off';self.roll=RollPlan(start,roll_direction)
            self.axis=self.roll.axis;self.pivot=self.roll.pivot
            d=roll_direction.value
            horizontal=abs(d[0])*start.extents[0]+abs(d[1])*start.extents[1]
            balance=math.atan2(horizontal,start.extents[2])
            lo,hi=0.,1.
            for _ in range(48):
                mid=(lo+hi)/2
                if roll_angle(mid)<balance:lo=mid
                else:hi=mid
            self.cut=(lo+hi)/2
            self.roll_duration=min(.35,duration*.45)
            self.roll_end=self.cut*self.roll_duration
            self.tip_start=self.roll.sample(self.cut)
            self.start_angle=balance
            self.start_omega=roll_angular_velocity(self.cut,self.roll_duration)
            tip_time=min(tuning.tip_time,duration*.22,1.8*(math.pi/2-balance)/max(self.start_omega,.001))
            self.tip_end=self.roll_end+tip_time
            delta=math.pi/2-balance
            self.tip_alpha=2*(delta-self.start_omega*tip_time)/(tip_time*tip_time)
        else:
            contact=support_contact(start,supports,pitch)
            if contact is not None:
                self.case='partial';direction,self.pivot=contact
                dx,dy,_=direction.value;self.axis=(-dy,dx,0.)
                self.tip_end=min(tuning.tip_time,duration*.24)
                self.tip_alpha=2*tuning.partial_angle/self.tip_end**2
                # Core may declare a partly supported block lost even when a
                # rigid cuboid cannot turn through the narrow opening. Never
                # force that turn through an opposing slab or invent a bounce.
                nearby=tuple((x,y) for x,y in supports if abs(x-start.center[0])<start.extents[0]+pitch
                             and abs(y-start.center[1])<start.extents[1]+pitch)
                if any(intersects_slab(around(start,self.pivot,self.axis,tuning.partial_angle*i/12),cell,pitch)
                       for i in range(1,13) for cell in nearby):
                    self.case='confined-drop';self.clearance='neighbour blocks tipping'
                    self.pivot=None;self.tip_end=0.;self.tip_alpha=0.
        self.free_time=duration-self.tip_end
        self.release=self._tip(self.tip_end) if self.pivot is not None else start
        self.omega=(self.start_omega+self.tip_alpha*(self.tip_end-self.roll_end)) if self.pivot is not None else 0.
        if self.omega < -1e-8:raise ValueError('Tip would reverse direction.')
        self.omega=max(0.,self.omega)
        # Exact tangent velocity omega x (centre - pivot), not a guessed offset.
        if self.pivot is not None:
            ax,ay,az=self.axis;rx,ry,rz=sub(self.release.center,self.pivot)
            self.velocity=scale((ay*rz-az*ry,az*rx-ax*rz,ax*ry-ay*rx),self.omega)
        else:self.velocity=(0.,0.,0.)
        self.gravity=max(tuning.gravity*pitch,2*fall_distance*pitch/self.free_time**2)
        self.angular_acceleration=-(1-tuning.angular_retention)*self.omega/self.free_time

    def _tip(self,elapsed):
        t=max(0.,elapsed-self.roll_end)
        angle=self.start_omega*t+.5*self.tip_alpha*t*t
        return around(self.tip_start,self.pivot,self.axis,angle)

    def sample(self,elapsed):
        finite(elapsed,'elapsed')
        t=min(elapsed,self.duration)
        if self.roll is not None and t<self.roll_end:
            return FallSample(self.roll.sample(t/self.roll_duration),1.,'roll')
        if self.pivot is not None and t<self.tip_end:
            return FallSample(self._tip(t),1.,'tip')
        ft=t-self.tip_end
        position=add(self.release.center,add(scale(self.velocity,ft),(0,0,-.5*self.gravity*ft*ft)))
        angle=self.omega*ft+.5*self.angular_acceleration*ft*ft
        pose=replace(self.release,center=position,
            quaternion=normalized(qmul(axis_angle(self.axis,angle),self.release.quaternion)))
        drop=self.release.center[2]-position[2]
        fade_length=min(self.tuning.fade_time,self.free_time*.45)
        fade=max(0.,min(1.,(ft-(self.free_time-fade_length))/fade_length))
        opacity=1.-smoothstep(fade) if drop>=self.tuning.fade_depth*self.pitch else 1.
        return FallSample(pose,opacity,'hidden' if opacity==0 else 'free-fall')
