"""Flat vector icons for the HUD, drawn as Panda3D geometry (no font/image needed).

Every icon is built from triangles in a unit box (about -1..1 on x and z), so
the HUD only has to scale and tint it. Builders are pure math; only make_icon
touches Panda3D.
"""
import math

POINTS_PER_CIRCLE = 28


def _rect(x0, z0, x1, z1):
    return [((x0, z0), (x1, z0), (x1, z1)), ((x0, z0), (x1, z1), (x0, z1))]


def _fan(center, points):
    n = len(points)
    return [(center, points[i], points[(i + 1) % n]) for i in range(n)]


def _circle_points(radius, n=POINTS_PER_CIRCLE, cx=0.0, cz=0.0):
    return [(cx + radius * math.cos(2 * math.pi * i / n),
             cz + radius * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _disc(cx, cz, radius):
    return _fan((cx, cz), _circle_points(radius, cx=cx, cz=cz))


def _band(outer, inner):
    """Closed ring between two polygons with the same number of points."""
    n = len(outer)
    tris = []
    for i in range(n):
        j = (i + 1) % n
        tris += [(outer[i], outer[j], inner[j]), (outer[i], inner[j], inner[i])]
    return tris


def _arc_band(r_out, r_in, start_deg, end_deg, n=POINTS_PER_CIRCLE):
    tris = []
    for i in range(n):
        a0 = math.radians(start_deg + (end_deg - start_deg) * i / n)
        a1 = math.radians(start_deg + (end_deg - start_deg) * (i + 1) / n)
        o0, o1 = (r_out * math.cos(a0), r_out * math.sin(a0)), (r_out * math.cos(a1), r_out * math.sin(a1))
        i0, i1 = (r_in * math.cos(a0), r_in * math.sin(a0)), (r_in * math.cos(a1), r_in * math.sin(a1))
        tris += [(o0, o1, i1), (o0, i1, i0)]
    return tris


def _star(cx, cz, size):
    """Four-pointed sparkle."""
    waist = 0.22 * size
    points = [(cx, cz + size), (cx + waist, cz + waist), (cx + size, cz), (cx + waist, cz - waist),
              (cx, cz - size), (cx - waist, cz - waist), (cx - size, cz), (cx - waist, cz + waist)]
    return _fan((cx, cz), points)


def _exit():
    return [((-0.95, 0.0), (-0.15, 0.72), (-0.15, -0.72))] + _rect(-0.2, -0.24, 0.9, 0.24)


def _restart():
    tris = _arc_band(0.82, 0.54, 40, 325)
    theta = math.radians(325)
    cx, cz = 0.68 * math.cos(theta), 0.68 * math.sin(theta)
    tx, tz = -math.sin(theta), math.cos(theta)      # travel direction (counter-clockwise)
    nx, nz = math.cos(theta), math.sin(theta)
    tip = (cx + tx * 0.45, cz + tz * 0.45)
    base1 = (cx - tx * 0.05 + nx * 0.42, cz - tz * 0.05 + nz * 0.42)
    base2 = (cx - tx * 0.05 - nx * 0.42, cz - tz * 0.05 - nz * 0.42)
    return tris + [(tip, base1, base2)]


def _ai():
    return _star(-0.18, -0.18, 0.82) + _star(0.62, 0.62, 0.34)


def _view():
    n = POINTS_PER_CIRCLE

    def half(x):
        return 0.62 * (1 - x * x) ** 0.8

    xs = [-1 + 2 * i / n for i in range(n + 1)]
    outer = [(x, half(x)) for x in xs] + [(x, -half(x)) for x in reversed(xs[1:-1])]
    inner = [(x * 0.7, z * 0.7) for x, z in outer]
    return _band(outer, inner) + _disc(0, 0, 0.24)


def _help():
    ring = _band(_circle_points(0.95), _circle_points(0.74))
    return ring + _disc(0, 0.42, 0.12) + _rect(-0.1, -0.5, 0.1, 0.2)


def _play():
    return [((-0.5, 0.72), (0.75, 0.0), (-0.5, -0.72))]


def _pause():
    return _rect(-0.58, -0.68, -0.16, 0.68) + _rect(0.16, -0.68, 0.58, 0.68)


def _step():
    return [((-0.75, 0.68), (0.4, 0.0), (-0.75, -0.68))] + _rect(0.5, -0.68, 0.82, 0.68)


BUILDERS = {
    'exit': _exit, 'restart': _restart, 'ai': _ai, 'view': _view, 'help': _help,
    'play': _play, 'pause': _pause, 'step': _step,
}


def triangles(name):
    """Return the icon as a list of ((x, z), (x, z), (x, z)) triangles."""
    return BUILDERS[name]()


def make_icon(name):
    """Return a flat, unlit NodePath for the icon (tint it with setColor)."""
    from panda3d.core import (Geom, GeomNode, GeomTriangles, GeomVertexData,
                              GeomVertexFormat, GeomVertexWriter, NodePath,
                              TransparencyAttrib)
    tris = triangles(name)
    data = GeomVertexData(f'icon-{name}', GeomVertexFormat.getV3(), Geom.UHStatic)
    data.setNumRows(len(tris) * 3)
    vertex = GeomVertexWriter(data, 'vertex')
    primitive = GeomTriangles(Geom.UHStatic)
    index = 0
    for tri in tris:
        for x, z in tri:
            vertex.addData3(x, 0, z)
        primitive.addVertices(index, index + 1, index + 2)
        index += 3
    geom = Geom(data)
    geom.addPrimitive(primitive)
    node = GeomNode(f'icon-{name}')
    node.addGeom(geom)
    path = NodePath(node)
    path.setTwoSided(True)
    path.setLightOff(1)
    path.setShaderOff(1)
    path.setTransparency(TransparencyAttrib.MAlpha)
    return path

def _clock():
    return _band(_circle_points(.78), _circle_points(.62)) + _rect(-.08,0,.08,.58) + _rect(0,-.08,.45,.08) + _rect(-.23,.84,.23,.98)


def _graph():
    return _rect(-.8,-.8,-.45,.05)+_rect(-.2,-.8,.15,.85)+_rect(.4,-.8,.75,.42)


def _chip():
    tris=_band([(-.64,-.64),(.64,-.64),(.64,.64),(-.64,.64)], [(-.48,-.48),(.48,-.48),(.48,.48),(-.48,.48)])
    for off in (-.4,0,.4):
        tris+=_rect(off-.06,.68,off+.06,.95)+_rect(off-.06,-.95,off+.06,-.68)
        tris+=_rect(.68,off-.06,.95,off+.06)+_rect(-.95,off-.06,-.68,off+.06)
    return tris


def _nodes():
    return _rect(-.07,-.52,.07,.5)+_rect(-.6,-.5,.6,-.36)+_disc(0,.65,.23)+_disc(-.6,-.55,.23)+_disc(.6,-.55,.23)


def _steps():
    return _disc(-.42,.36,.28)+_disc(.4,-.22,.28)+_rect(-.57,-.3,-.27,.18)+_rect(.25,-.88,.55,-.4)

BUILDERS.update(clock=_clock,graph=_graph,chip=_chip,nodes=_nodes,steps=_steps)
