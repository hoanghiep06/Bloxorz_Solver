"""Pure rigid-body rolling math. Quaternions are Hamilton (w,x,y,z).

qmul(world_rotation, local_orientation) composes a world-space rotation. Runtime
converts components directly to Panda Quat; tests verify transformed basis vectors.
"""
from dataclasses import dataclass
from enum import Enum
import math


class RollDirection(Enum):
    RIGHT = (1, 0, 0)
    LEFT = (-1, 0, 0)
    UP = (0, 1, 0)
    DOWN = (0, -1, 0)


def finite(value, name, *, minimum=0):
    if type(value) not in (int, float) or not math.isfinite(value) or value < minimum:
        raise ValueError(f'{name} must be finite and >= {minimum} (not bool).')


def vec(value, size, name):
    if type(value) is not tuple or len(value) != size:
        raise TypeError(f'{name} must be an immutable {size}-tuple.')
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in value):
        raise ValueError(f'{name} must contain finite numbers.')


def add(a, b):
    return tuple(x+y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def scale(a, s):
    return tuple(x*s for x in a)


def lerp(a, b, t):
    return add(a, scale(sub(b, a), t))


def normalized(q):
    vec(q, 4, 'quaternion')
    length = math.sqrt(sum(v*v for v in q))
    if length < 1e-12:
        raise ValueError('Quaternion has zero length.')
    return tuple(v/length for v in q)


def qmul(a, b):
    w, x, y, z = a
    v, i, j, k = b
    return (w*v-x*i-y*j-z*k, w*i+x*v+y*k-z*j,
            w*j-x*k+y*v+z*i, w*k+x*j-y*i+z*v)


def axis_angle(axis, angle):
    length = math.sqrt(sum(v*v for v in axis))
    if length < 1e-12:
        raise ValueError('Rotation axis is zero.')
    s = math.sin(angle/2) / length
    return (math.cos(angle/2), *(v*s for v in axis))


def rotate(q, point):
    w, x, y, z = q
    return qmul(qmul(q, (0, *point)), (w, -x, -y, -z))[1:]


def slerp(a, b, t):
    a, b = normalized(a), normalized(b)
    dot = sum(x*y for x, y in zip(a, b))
    if dot < 0:
        b, dot = scale(b, -1), -dot
    if dot > .9995:
        return normalized(lerp(a, b, t))
    angle = math.acos(min(1, dot))
    return normalized(add(scale(a, math.sin((1-t)*angle)/math.sin(angle)),
                          scale(b, math.sin(t*angle)/math.sin(angle))))


def smoothstep(progress):
    finite(progress, 'progress')
    if progress > 1:
        raise ValueError('progress must be <=1.')
    return progress*progress*(3-2*progress)


@dataclass(frozen=True, slots=True)
class VisualPose:
    center: tuple[float, float, float]
    quaternion: tuple[float, float, float, float]
    nominal_dimensions: tuple[float, float, float]

    def __post_init__(self):
        vec(self.center, 3, 'center')
        vec(self.nominal_dimensions, 3, 'nominal_dimensions')
        if any(v <= 0 for v in self.nominal_dimensions):
            raise ValueError('Dimensions must be positive.')
        normalized(self.quaternion)
        if abs(sum(v*v for v in self.quaternion)-1) > 1e-6:
            raise ValueError('Visual orientation must be normalized.')

    @property
    def extents(self):
        basis = [rotate(self.quaternion, tuple(1 if i == j else 0 for i in range(3))) for j in range(3)]
        return tuple(sum(abs(basis[j][i])*self.nominal_dimensions[j]/2 for j in range(3)) for i in range(3))

    def corners(self):
        from itertools import product
        return tuple(add(self.center, rotate(self.quaternion,
            tuple(sign*self.nominal_dimensions[i]/2 for i, sign in enumerate(signs))))
            for signs in product((-1, 1), repeat=3))


@dataclass(frozen=True, slots=True)
class RollPlan:
    start: VisualPose
    direction: RollDirection

    def __post_init__(self):
        if type(self.start) is not VisualPose or type(self.direction) is not RollDirection:
            raise TypeError('Expected VisualPose and RollDirection.')
        self.start.__post_init__()
        if abs(self.start.center[2]-self.start.extents[2]) > 1e-6*max(self.start.nominal_dimensions):
            raise ValueError('A roll must start on the support plane Z=0.')
        # A supported roll starts axis-aligned, including any face-history basis.
        for axis in range(3):
            p = rotate(self.start.quaternion, tuple(int(i == axis) for i in range(3)))
            if sum(abs(abs(v)-1) < 1e-6 for v in p) != 1:
                raise ValueError('Start orientation must be a quarter-turn basis.')

    @property
    def pivot(self):
        d, h = self.direction.value, self.start.extents
        return add(self.start.center, (d[0]*h[0], d[1]*h[1], -h[2]))

    @property
    def axis(self):
        x, y, _ = self.direction.value
        return (-y, x, 0)

    def sample(self, progress):
        # Deliberate lift, faster weight transfer after the balance point,
        # firm landing without bounce. The exact edge pivot never changes.
        t = smoothstep(progress)
        angle = math.pi/2*(t*t*(2-t))
        q = axis_angle(self.axis, angle)
        return VisualPose(add(self.pivot, rotate(q, sub(self.start.center, self.pivot))),
                          normalized(qmul(q, self.start.quaternion)), self.start.nominal_dimensions)

    def validate_target(self, target):
        predicted = self.sample(1)
        tolerance = 1e-6*max(self.start.nominal_dimensions)
        if any(abs(x-y) > tolerance for x, y in zip(predicted.center, target.center)) or any(
            abs(x-y) > tolerance for x, y in zip(predicted.extents, target.extents)
        ):
            raise ValueError('Supplied after pose does not match one physical 90-degree roll.')


def canonical_poses(snapshot, board, *, pitch=1.0):
    """Intentional resync basis only; successful rolling never calls this to reset Q."""
    from src.gui.animation_contracts import as_visual_snapshot
    from src.gui.geometry_math import block_pose, cell_to_world
    snapshot = as_visual_snapshot(snapshot)
    if snapshot.whole_pose is not None:
        pose = block_pose(*snapshot.whole_pose.anchor_cell, snapshot.whole_pose.orientation,
                          rows=board.rows, cols=board.cols, pitch=pitch)
        q = axis_angle(pose.rotation_axis, math.radians(pose.angle_degrees))
        return {None: VisualPose(pose.center, q, (pitch, pitch, 2*pitch))}
    return {cube.cube_id: VisualPose(
        (*cell_to_world(*cube.cell, rows=board.rows, cols=board.cols, pitch=pitch), pitch/2),
        (1, 0, 0, 0), (pitch, pitch, pitch)) for cube in snapshot.cubes}
