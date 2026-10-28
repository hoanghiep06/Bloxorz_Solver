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

# Goal rim stays warm and legible in either theme; the cavity remains dark.
GOAL_THEME_COLORS = {
    'light': dict(rim=_rgb("FF9C24"), wall=_rgb("26362F"), floor=_rgb("101D18")),
    'dark': dict(rim=_rgb("FFAC38"), wall=_rgb("20354B"), floor=_rgb("081320")),
}
# Preserve the public light-theme constants for existing callers.
GOAL_RIM = GOAL_THEME_COLORS['light']['rim']
GOAL_WALL = GOAL_THEME_COLORS['light']['wall']
GOAL_FLOOR = GOAL_THEME_COLORS['light']['floor']
GOAL_INTERIOR = GOAL_WALL

# Legacy palette exported for compatibility; the active block uses magma (light) / ice (dark) textures.
BLOCK_THEME_COLORS = {
    'light': dict(main=_rgb("8A5A34"), dark=_rgb("5C3B22"), edge=_rgb("B98A5C"),
                  inlay=_rgb("C9A074"), spot=_rgb("5F8A2E"), spot2=_rgb("86AD43")),
    'dark': dict(main=_rgb("3F7BC8"), dark=_rgb("27508F"), edge=_rgb("9CCBF5"),
                 inlay=_rgb("B9DCF8"), spot=_rgb("F7FBFF"), spot2=_rgb("DCEBFA")),
}

# Vật liệu khối theo theme: ban ngày dung nham, ban đêm băng.
BLOCK_MATERIAL = {'light': 'magma', 'dark': 'ice'}
# Màu cạnh vát: băng sáng và lạnh hơn, dung nham giữ màu đá ấm.
BLOCK_EDGE_COLOR = {'light': (.46, .43, .36, 1), 'dark': (.80, .92, 1.0, 1)}


class _MeshBuilder:
    """Write flat-normal polygon faces, triangulated as convex fans."""

    def __init__(self, name: str):
        self.name = name
        self.data = GeomVertexData(name, GeomVertexFormat.getV3n3c4t2(), Geom.UHStatic)
        self.vertices = GeomVertexWriter(self.data, "vertex")
        self.normals = GeomVertexWriter(self.data, "normal")
        self.colors = GeomVertexWriter(self.data, "color")
        self.uvs = GeomVertexWriter(self.data, "texcoord")
        self.triangles = GeomTriangles(Geom.UHStatic)
        self.count = 0
        self.uv_offset = (0., 0.)

    def face(self, points, normal, color):
        points = list(points)
        normal = Vec3(*normal).normalized()
        cross = (Vec3(*points[1]) - Vec3(*points[0])).cross(
            Vec3(*points[2]) - Vec3(*points[0]))
        if cross.dot(normal) < 0:
            points.reverse()
        offset = self.count
        axis = max(range(3), key=lambda i: abs(normal[i]))
        axes = [i for i in range(3) if i != axis]
        for point in points:
            self.uvs.addData2f(point[axes[0]] + .5 + axis*.173 + self.uv_offset[0], point[axes[1]] + .5 + axis*.291 + self.uv_offset[1])
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


def _beveled_box(name, dimensions, bevel, face_colors, edge_color, *, inlay=False,
                 inlay_color=BLOCK_HIGHLIGHT, decorate=None):
    """Six inset faces + twelve chamfer strips + eight clipped corners.

    Outer support planes retain the nominal dimensions. Every edge/corner is
    real geometry, and all polygons share exact geometric boundary positions.
    ``decorate(builder, half)`` adds flush face markings within the cuboid.
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
                builder.face(patch, normal, inlay_color)
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
    node = builder.finish()
    if decorate is not None:
        from panda3d.core import DepthOffsetAttrib, RenderState
        decals = _MeshBuilder(name + '-Markings')
        decorate(decals, half)
        markings = decals.finish()
        for index in range(markings.getNumGeoms()):
            node.addGeom(markings.modifyGeom(index), RenderState.make(DepthOffsetAttrib.make(1)))
    return node


def make_floor_mesh(*, pitch: float = 1.0, theme='light') -> GeomNode:
    """Return a shared local tile: top 0, bottom -0.18s, width/depth 0.96s."""
    _pitch(pitch)
    colors = {(axis, sign): FLOOR_TOP if axis == 2 and sign == 1 else FLOOR_SIDE
              for axis in range(3) for sign in (-1, 1)}
    node = _beveled_box("FloorMesh", (0.96 * pitch, 0.96 * pitch, 0.18 * pitch),
                        0.02 * pitch, colors, FLOOR_EDGE)
    # Bake the tile offset into vertices; the reusable instance transform is XY only.
    from panda3d.core import Mat4
    node.modifyGeom(0).transformVertices(Mat4.translateMat(0, 0, -0.09 * pitch))
    from src.gui.visual_materials import apply
    return apply(node, "stone", theme)


def make_goal_mesh(*, pitch: float = 1.0, theme: str = 'light') -> GeomNode:
    """Open-top square recess: 0.10s rim, 0.14s cavity depth; màu theo theme."""
    _pitch(pitch)
    c = GOAL_THEME_COLORS[theme]
    builder = _MeshBuilder(f"GoalMesh-{theme}")
    outer = [(-0.48, -0.48), (0.48, -0.48), (0.48, 0.48), (-0.48, 0.48)]
    inner = [(-0.38, -0.38), (0.38, -0.38), (0.38, 0.38), (-0.38, 0.38)]
    def point(xy, z):
        return (xy[0] * pitch, xy[1] * pitch, z * pitch)
    for i in range(4):
        j = (i + 1) % 4
        builder.face((point(outer[i], 0), point(outer[j], 0),
                      point(inner[j], 0), point(inner[i], 0)), (0, 0, 1), c['rim'])
        dx, dy = outer[j][0] - outer[i][0], outer[j][1] - outer[i][1]
        builder.face((point(outer[i], 0), point(outer[j], 0),
                      point(outer[j], -0.18), point(outer[i], -0.18)),
                     (dy, -dx, 0), c['rim'])
        builder.face((point(inner[i], 0), point(inner[j], 0),
                      point(inner[j], -0.14), point(inner[i], -0.14)),
                     (-dy, dx, 0), c['wall'])
    builder.face([point(p, -0.14) for p in inner], (0, 0, 1), c['floor'])
    builder.face([point(p, -0.18) for p in outer], (0, 0, -1), FLOOR_SIDE)
    return builder.finish()


def make_block_mesh(*, pitch: float = 1.0) -> GeomNode:
    """Default magma prototype, retaining the Basic renderer's public mesh name."""
    mesh = make_themed_block_mesh('light', pitch=pitch)
    mesh.setName('MainBlockMesh')
    return mesh


def make_themed_block_mesh(theme, *, pitch: float = 1.0) -> GeomNode:
    """Rigid UV-mapped cuboid (magma ban ngày, băng ban đêm); geometry never expands beyond 1×1×2."""
    _pitch(pitch)
    if theme not in BLOCK_THEME_COLORS:
        raise ValueError('theme must be light or dark')
    from src.gui.visual_materials import apply
    colors = {(axis,sign):(1.,1.,1.,1.) for axis in range(3) for sign in (-1,1)}
    return apply(_beveled_box(f"MainBlockMesh-{theme}", (pitch,pitch,2*pitch),
        .03*pitch, colors, BLOCK_EDGE_COLOR[theme]), BLOCK_MATERIAL[theme], theme)


def make_themed_cube_mesh(theme, *, pitch: float = 1.0) -> GeomNode:
    """Split cube shares the local UV/material pipeline of the whole actor."""
    _pitch(pitch)
    if theme not in BLOCK_THEME_COLORS:
        raise ValueError('theme must be light or dark')
    from src.gui.visual_materials import apply
    colors = {(axis,sign):(1.,1.,1.,1.) for axis in range(3) for sign in (-1,1)}
    return apply(_beveled_box(f"SplitCubeMesh-{theme}", (pitch,pitch,pitch),
        .02*pitch, colors, BLOCK_EDGE_COLOR[theme]), BLOCK_MATERIAL[theme], theme)


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