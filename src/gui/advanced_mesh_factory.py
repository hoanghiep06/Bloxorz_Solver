"""Procedural Advanced visual assets, all dimensions scaled by logical pitch.

Tiles have a supporting top at Z=0; raised markings are separated from that
plane. Broken debris remains below it. No collision or state logic lives here.
"""

import math
from panda3d.core import GeomNode, Mat4, Vec3

from src.gui.advanced_contracts import SwitchVisualKind
from src.gui.mesh_factory import (
    MeshBuilder, make_beveled_box_mesh, BLOCK_MAIN, BLOCK_DARK, BLOCK_HIGHLIGHT,
    FLOOR_SIDE,
)

FRAGILE = (214 / 255, 161 / 255, 95 / 255, 1.0)
SUCCESS = (78 / 255, 138 / 255, 114 / 255, 1.0)
CRACK = (125 / 255, 87 / 255, 49 / 255, 1.0)


def _pitch(pitch):
    if type(pitch) not in (int, float) or not math.isfinite(pitch) or pitch <= 0:
        raise ValueError('pitch must be finite and positive (not bool).')


def _box(name, dimensions, center, pitch, top, side=BLOCK_DARK, edge=BLOCK_HIGHLIGHT,
         angle=0):
    node = make_beveled_box_mesh(name=name, dimensions=tuple(v * pitch for v in dimensions),
        bevel=min(.02, min(dimensions) / 5) * pitch,
        top_color=top, side_color=side, edge_color=edge)
    transform = Mat4.rotateMat(angle, Vec3(0, 0, 1)) * Mat4.translateMat(
        *(v * pitch for v in center))
    node.modifyGeom(0).transformVertices(transform)
    return node


def _combine(name, parts):
    node = GeomNode(name)
    for part in parts:
        for index in range(part.getNumGeoms()):
            node.addGeom(part.modifyGeom(index))
    return node


def make_fragile_mesh(*, pitch=1.0, broken=False):
    _pitch(pitch)
    if type(broken) is not bool:
        raise TypeError('broken must be bool.')
    if broken:
        # Three small remnants below the vanished supporting plane; no full floor.
        return _combine('BrokenFragileMesh', [
            _box('Debris', (.18, .13, .06), center, pitch, FRAGILE, CRACK, FRAGILE, angle)
            for center, angle in (((-.32, -.30, -.14), 18),
                                  ((.29, .31, -.14), -23), ((.30, -.32, -.14), 37))])
    parts = [_box('FragileSurface', (.96, .96, .18), (0, 0, -.09), pitch,
                  FRAGILE, CRACK, FRAGILE)]
    # Thin volumetric crack strips; their bottom is .002 above the supporting top.
    for a, b in (((-.36, -.32), (0, -.04)), ((0, -.04), (.32, .34)),
                 ((0, -.04), (-.24, .30)), ((.12, .10), (.37, .03))):
        length = math.dist(a, b)
        center = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, .006)
        angle = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        parts.append(_box('Crack', (length, .025, .008), center, pitch, CRACK, CRACK, CRACK, angle))
    return _combine('IntactFragileMesh', parts)


def make_bridge_mesh(*, pitch=1.0):
    _pitch(pitch)
    return _combine('BridgePlatformMesh', [
        _box('BridgePlatform', (.96, .96, .18), (0, 0, -.09), pitch,
             BLOCK_HIGHLIGHT, BLOCK_DARK, BLOCK_MAIN),
        *[_box('BridgeRib', (.76, .035, .012), (0, y, .009), pitch,
               BLOCK_MAIN, BLOCK_DARK, BLOCK_MAIN) for y in (-.28, 0, .28)]])


def _disc(pitch, color):
    builder = MeshBuilder('SoftSwitchDisc')
    points = [(.30 * math.cos(i * math.tau / 24), .30 * math.sin(i * math.tau / 24))
              for i in range(24)]
    def point(xy, z):
        return (xy[0] * pitch, xy[1] * pitch, z * pitch)
    builder.face([point(p, .07) for p in points], (0, 0, 1), color)
    builder.face([point(p, .015) for p in points], (0, 0, -1), BLOCK_DARK)
    for i, a in enumerate(points):
        b = points[(i + 1) % len(points)]
        builder.face((point(a, .015), point(b, .015), point(b, .07), point(a, .07)),
                     (a[0] + b[0], a[1] + b[1], 0), BLOCK_DARK)
    return builder.finish()


def make_switch_mesh(kind, *, activated=False, pitch=1.0):
    _pitch(pitch)
    if type(kind) is not SwitchVisualKind or type(activated) is not bool:
        raise TypeError('Expected SwitchVisualKind and bool activated.')
    color = SUCCESS if activated else BLOCK_MAIN
    if kind is SwitchVisualKind.SOFT:
        return _disc(pitch, color)
    if kind is SwitchVisualKind.HEAVY:
        # Square plus four arms, visibly distinct from a circle or two plates.
        parts = [_box('HeavyBase', (.61, .61, .045), (0, 0, .0375), pitch,
                      BLOCK_DARK, BLOCK_DARK, BLOCK_HIGHLIGHT)]
        for dimensions, center in (((.16, .46, .035), (0, 0, .080)),
                                   ((.15, .15, .035), (-.155, 0, .080)),
                                   ((.15, .15, .035), (.155, 0, .080))):
            parts.append(_box('HeavyCross', dimensions, center, pitch, color, color, color))
        return _combine('HeavySwitchMesh', parts)
    return _combine('SplitSwitchMesh', [
        _box('SplitPlate', (.23, .52, .075), (x, 0, .0525), pitch,
             color, BLOCK_DARK, BLOCK_HIGHLIGHT) for x in (-.19, .19)])


def make_split_cube_mesh(*, pitch=1.0):
    _pitch(pitch)
    return _box('SplitCubeMesh', (1, 1, 1), (0, 0, 0), pitch,
                BLOCK_MAIN, BLOCK_MAIN, BLOCK_HIGHLIGHT)


def make_active_cube_mesh(*, pitch=1.0):
    """Four top corner brackets, inside the cube's nominal footprint; no pulse."""
    _pitch(pitch)
    parts = []
    for x in (-1, 1):
        for y in (-1, 1):
            parts.extend((
                _box('ActiveBracket', (.24, .045, .03), (x * .33, y * .425, .525),
                     pitch, SUCCESS, SUCCESS, SUCCESS),
                _box('ActiveBracket', (.045, .19, .03), (x * .425, y * .3075, .525),
                     pitch, SUCCESS, SUCCESS, SUCCESS)))
    return _combine('ActiveCubeIndicatorMesh', parts)
