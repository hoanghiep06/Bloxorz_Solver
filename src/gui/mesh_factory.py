"""Procedural, outward-wound Panda3D meshes; no window, assets or gameplay."""

from itertools import combinations, product
import math

from panda3d.core import (
    Geom, GeomNode, GeomTriangles, GeomVertexData, GeomVertexFormat,
    GeomVertexWriter, Vec3,
)


def _rgb(hex_color: str) -> tuple[float, float, float, float]:
    return (*tuple(int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4)), 1.0)


FLOOR_TOP = _rgb("DCE5ED")
FLOOR_SIDE = _rgb("A8BBCD")
FLOOR_EDGE = _rgb("91A8BB")
BLOCK_MAIN = _rgb("527B9C")
BLOCK_DARK = _rgb("354F68")
BLOCK_HIGHLIGHT = _rgb("91ADC3")
GOAL_RIM = _rgb("527B9C")
GOAL_INTERIOR = _rgb("273B50")


class _MeshBuilder:
    """Write flat-normal polygon faces, triangulated as convex fans."""

    def __init__(self, name: str):
        self.name = name
        self.data = GeomVertexData(name, GeomVertexFormat.getV3n3c4(), Geom.UHStatic)
        self.vertices = GeomVertexWriter(self.data, "vertex")
        self.normals = GeomVertexWriter(self.data, "normal")
        self.colors = GeomVertexWriter(self.data, "color")
        self.triangles = GeomTriangles(Geom.UHStatic)
        self.count = 0

    def face(self, points, normal, color):
        points = list(points)
        normal = Vec3(*normal).normalized()
        cross = (Vec3(*points[1]) - Vec3(*points[0])).cross(
            Vec3(*points[2]) - Vec3(*points[0]))
        if cross.dot(normal) < 0:
            points.reverse()
        offset = self.count
        for point in points:
            self.vertices.addData3f(*point)
            self.normals.addData3f(normal)
            self.colors.addData4f(*color)
            self.count += 1
        for index in range(1, len(points) - 1):
            self.triangles.addVertices(offset, offset + index, offset + index + 1)
            self.triangles.closePrimitive()

    def finish(self) -> GeomNode:
        geom = Geom(self.data)
        geom.addPrimitive(self.triangles)
        node = GeomNode(self.name)
        node.addGeom(geom)
        return node


def _pitch(value: float) -> None:
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError("pitch must be finite and positive (not bool).")


def _beveled_box(name, dimensions, bevel, face_colors, edge_color, *, inlay=False):
    """Six inset faces + twelve chamfer strips + eight clipped corners.

    Outer support planes retain the nominal dimensions. Every edge/corner is
    real geometry, and all polygons share exact geometric boundary positions.
    """
    half = [dimension / 2 for dimension in dimensions]
    inset = [extent - bevel for extent in half]
    builder = _MeshBuilder(name)
    for axis in range(3):
        others = [a for a in range(3) if a != axis]
        for sign in (-1, 1):
            normal = [0, 0, 0]
            normal[axis] = sign
            points = []
            for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                point = [0.0] * 3
                point[axis] = sign * half[axis]
                point[others[0]] = a * inset[others[0]]
                point[others[1]] = b * inset[others[1]]
                points.append(point)
            color = face_colors[(axis, sign)]
            if inlay and axis == 1 and sign == -1:
                # Flush off-center rectangle: partition the existing face,
                # never overlay a coplanar decal or expand the nominal bounds.
                patch = [(-0.44, -0.5, 0.32), (-0.28, -0.5, 0.32),
                         (-0.28, -0.5, 0.70), (-0.44, -0.5, 0.70)]
                scale = dimensions[0]
                patch = [tuple(v * scale for v in p) for p in patch]
                for i in range(4):
                    j = (i + 1) % 4
                    builder.face((points[i], points[j], patch[j], patch[i]), normal, color)
                builder.face(patch, normal, BLOCK_HIGHLIGHT)
            else:
                builder.face(points, normal, color)
    for axis_a, axis_b in combinations(range(3), 2):
        along = next(a for a in range(3) if a not in (axis_a, axis_b))
        for sign_a, sign_b in product((-1, 1), repeat=2):
            normal = [0, 0, 0]
            normal[axis_a], normal[axis_b] = sign_a, sign_b
            points = []
            for end, outer_a in ((-1, True), (1, True), (1, False), (-1, False)):
                point = [0.0] * 3
                point[along] = end * inset[along]
                point[axis_a] = sign_a * (half[axis_a] if outer_a else inset[axis_a])
                point[axis_b] = sign_b * (inset[axis_b] if outer_a else half[axis_b])
                points.append(point)
            builder.face(points, normal, edge_color)
    for signs in product((-1, 1), repeat=3):
        points = []
        for axis in range(3):
            points.append([signs[a] * (half[a] if a == axis else inset[a])
                           for a in range(3)])
        builder.face(points, signs, edge_color)
    return builder.finish()


def make_floor_mesh(*, pitch: float = 1.0) -> GeomNode:
    """Return a shared local tile: top 0, bottom -0.18s, width/depth 0.96s."""
    _pitch(pitch)
    colors = {(axis, sign): FLOOR_TOP if axis == 2 and sign == 1 else FLOOR_SIDE
              for axis in range(3) for sign in (-1, 1)}
    node = _beveled_box("FloorMesh", (0.96 * pitch, 0.96 * pitch, 0.18 * pitch),
                        0.02 * pitch, colors, FLOOR_EDGE)
    # Bake the tile offset into vertices; the reusable instance transform is XY only.
    from panda3d.core import Mat4
    node.modifyGeom(0).transformVertices(Mat4.translateMat(0, 0, -0.09 * pitch))
    return node


def make_goal_mesh(*, pitch: float = 1.0) -> GeomNode:
    """Return a real open-top square recess: 0.10s rim, 0.14s cavity depth."""
    _pitch(pitch)
    builder = _MeshBuilder("GoalMesh")
    outer = [(-0.48, -0.48), (0.48, -0.48), (0.48, 0.48), (-0.48, 0.48)]
    inner = [(-0.38, -0.38), (0.38, -0.38), (0.38, 0.38), (-0.38, 0.38)]
    def point(xy, z):
        return (xy[0] * pitch, xy[1] * pitch, z * pitch)
    for i in range(4):
        j = (i + 1) % 4
        builder.face((point(outer[i], 0), point(outer[j], 0),
                      point(inner[j], 0), point(inner[i], 0)), (0, 0, 1), GOAL_RIM)
        dx, dy = outer[j][0] - outer[i][0], outer[j][1] - outer[i][1]
        builder.face((point(outer[i], 0), point(outer[j], 0),
                      point(outer[j], -0.18), point(outer[i], -0.18)),
                     (dy, -dx, 0), GOAL_RIM)
        builder.face((point(inner[i], 0), point(inner[j], 0),
                      point(inner[j], -0.14), point(inner[i], -0.14)),
                     (-dy, dx, 0), GOAL_INTERIOR)
    builder.face([point(p, -0.14) for p in inner], (0, 0, 1), GOAL_INTERIOR)
    builder.face([point(p, -0.18) for p in outer], (0, 0, -1), FLOOR_SIDE)
    return builder.finish()


def make_block_mesh(*, pitch: float = 1.0) -> GeomNode:
    """Return one centered nominal s×s×2s prototype with a flush asymmetric inlay."""
    _pitch(pitch)
    colors = {(axis, sign): (BLOCK_DARK if (axis, sign) in ((0, -1), (2, -1))
                             else BLOCK_MAIN)
              for axis in range(3) for sign in (-1, 1)}
    return _beveled_box("MainBlockMesh", (pitch, pitch, 2 * pitch), 0.03 * pitch,
                        colors, BLOCK_HIGHLIGHT, inlay=True)


class MeshBuilder(_MeshBuilder):
    """Public flat-normal convex-face builder for additional procedural assets."""


def make_beveled_box_mesh(*, name, dimensions, bevel, top_color, side_color, edge_color):
    """Public reusable box primitive; dimensions are centered nominal extents.

    Stage 4 extension point; existing Basic mesh factories retain their geometry.
    """
    if type(name) is not str or not name.strip():
        raise ValueError('name must be nonempty text.')
    if type(dimensions) is not tuple or len(dimensions) != 3:
        raise ValueError('dimensions must be a tuple of three positive extents.')
    for value in (*dimensions, bevel):
        _pitch(value)
    if bevel >= min(dimensions) / 2:
        raise ValueError('bevel must be less than every half extent.')
    for color in (top_color, side_color, edge_color):
        if type(color) is not tuple or len(color) != 4 or any(
            type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in color
        ):
            raise ValueError('colors must be finite RGBA tuples in [0, 1].')
    colors = {(axis, sign): top_color if (axis, sign) == (2, 1) else side_color
              for axis in range(3) for sign in (-1, 1)}
    return _beveled_box(name, dimensions, bevel, colors, edge_color)
