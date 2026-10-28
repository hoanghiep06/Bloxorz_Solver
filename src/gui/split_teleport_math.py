"""Deterministic split choreography; consumes supplied poses, never game rules."""
from dataclasses import dataclass, replace
import math
from src.gui.animation_math import VisualPose, add, rotate, smoothstep, lerp

SPLIT_TELEPORT_DURATION = 1.65
CHARGE_END, DISASSEMBLY_END, ARRIVAL_START, MATERIALIZE_END = .24, .44, .70, .90


def ramp(t, start, end):
    return smoothstep(max(0.0, min(1.0, (t-start)/(end-start))))


def pulse(t, start, peak, end):
    return ramp(t,start,peak)*(1-ramp(t,peak,end))


@dataclass(frozen=True)
class SplitFrame:
    progress: float
    phase: str
    poses: dict
    opacity: dict
    scales: dict
    weights: dict


class SplitTeleportPlan:
    """Source cubes vanish before relocation; only energy traverses the board."""
    def __init__(self, source, targets, cube_ids, active_id, pitch=1.0):
        self.source, self.targets = source, dict(targets)
        self.cube_ids, self.active_id, self.pitch = tuple(cube_ids), active_id, pitch
        self.starts = {
            key: VisualPose(add(source.center, rotate(source.quaternion,(0,0,sign*pitch/2))),
                            source.quaternion,(pitch,)*3)
            for key,sign in zip(self.cube_ids,(-1,1))}

    def sample(self, t):
        if not math.isfinite(t) or not 0 <= t <= 1:
            raise ValueError('Split progress must be finite and in [0, 1].')
        if t < CHARGE_END:
            return SplitFrame(t,'CHARGE',{None:self.source},{None:1},{None:1},{})
        phase = ('DISASSEMBLE' if t < DISASSEMBLY_END else 'TRANSIT'
                 if t < ARRIVAL_START else 'MATERIALIZE' if t < MATERIALIZE_END else 'ACTIVE')
        opacity, scales, poses = {}, {}, {}
        for key in self.cube_ids:
            if t < .58:
                start=self.starts[key]
                # Tiny local separation exposes the fracture seam, without
                # sending solid cubes toward the distant teleport destinations.
                sign=-1 if key==self.cube_ids[0] else 1
                separation=.10*self.pitch*ramp(t,.24,.40)
                poses[key]=replace(start,center=add(start.center,rotate(
                    self.source.quaternion,(sign*separation,0,0))))
                opacity[key]=1-ramp(t,.27,.42)
                scales[key]=1-.15*ramp(t,.27,.42)
            else:
                poses[key]=self.targets[key]
                opacity[key]=ramp(t,ARRIVAL_START,.87)
                scales[key]=.82+.18*ramp(t,ARRIVAL_START,MATERIALIZE_END)
        return SplitFrame(t,phase,poses,opacity,scales,
                          {self.active_id:ramp(t,.87,1)} if self.active_id else {})

    def stream_point(self, index, u):
        """An elevated energy-only arc; ends tied to the exact supplied target."""
        start=add(self.source.center,(0,0,.35*self.pitch))
        end=add(self.targets[self.cube_ids[index]].center,(0,0,.12*self.pitch))
        distance=math.hypot(end[0]-start[0],end[1]-start[1])
        height=self.pitch*(1.3+min(1.2,distance/self.pitch*.12))
        point=lerp(start,end,u)
        # Opposed sideways bend makes the two routes readable even for nearby targets.
        dx,dy=end[0]-start[0],end[1]-start[1]
        length=max(self.pitch,math.hypot(dx,dy))
        bend=math.sin(math.pi*u)*self.pitch*.22*(-1 if index==0 else 1)
        return (point[0]-dy/length*bend,point[1]+dx/length*bend,
                point[2]+math.sin(math.pi*u)*height)


MERGE_TELEPORT_DURATION = 1.45


class MergeTeleportPlan:
    """Reverse the energy choreography: supplied cubes converge into supplied whole.

    Reuse the same pool/paths with a remapped reverse visual clock. Authoritative
    cube poses remain untouched until invisible; no new merge/adjacency rules.
    """
    def __init__(self, sources, target, cube_ids, active_id, pitch=1.0):
        self._reverse = SplitTeleportPlan(target,sources,cube_ids,active_id,pitch)
        self.source, self.targets = target, dict(sources)
        self.cube_ids, self.active_id, self.pitch = tuple(cube_ids), active_id, pitch

    @staticmethod
    def visual_progress(t):
        # Leave a readable charging beat at both cubes, then accelerate the
        # energy toward the whole and let the final aura dissipate gently.
        points=((0.,1.),(.22,.90),(.42,.70),(.66,.44),(.85,.24),(1.,0.))
        for (a,x),(b,y) in zip(points,points[1:]):
            if t<=b:return x+(y-x)*(t-a)/(b-a)
        return 0.

    def sample(self,t):
        if not math.isfinite(t) or not 0<=t<=1:
            raise ValueError('Merge progress must be finite and in [0, 1].')
        frame=self._reverse.sample(self.visual_progress(t))
        phase=('MERGE_CHARGE' if t<.22 else 'MERGE_DISSOLVE' if t<.42 else
               'MERGE_CONVERGE' if t<.66 else 'MERGE_RECONSTRUCT' if t<.85 else 'MERGE_SETTLE')
        return replace(frame,phase=phase)

    def stream_point(self,index,u):
        return self._reverse.stream_point(index,u)
