"""Animated menu overlay: falling stars (dark theme) or drifting leaves (light theme).

Pure 2D particles on pixel2d, drawn behind the menu widgets. Cheap: ~40 nodes.
"""
import math
import random


def _shape(points, color):
    from panda3d.core import (Geom, GeomNode, GeomTriangles, GeomVertexData,
                              GeomVertexFormat, GeomVertexWriter, NodePath,
                              TransparencyAttrib)
    data = GeomVertexData('ambient', GeomVertexFormat.getV3c4(), Geom.UHStatic)
    data.setNumRows(len(points) + 1)
    vertex, col = GeomVertexWriter(data, 'vertex'), GeomVertexWriter(data, 'color')
    vertex.addData3(0, 0, 0)
    col.addData4(*color)
    for x, z in points:
        vertex.addData3(x, 0, z)
        col.addData4(*color)
    triangles = GeomTriangles(Geom.UHStatic)
    for i in range(len(points)):
        triangles.addVertices(0, 1 + i, 1 + (i + 1) % len(points))
    geom = Geom(data)
    geom.addPrimitive(triangles)
    node = GeomNode('particle')
    node.addGeom(geom)
    path = NodePath(node)
    path.setTwoSided(True)
    path.setTransparency(TransparencyAttrib.MAlpha)
    return path


def _sparkle(r):
    pts = []
    for i in range(8):
        a = i * math.pi / 4
        k = r if i % 2 == 0 else r * .22
        pts.append((k * math.cos(a), k * math.sin(a)))
    return pts


def _leaf(r):
    return [(r * math.cos(i * math.tau / 14), r * .45 * math.sin(i * math.tau / 14))
            for i in range(14)]


NIGHT_COLORS = ((1, 1, 1, .9), (1, .95, .7, .9), (.7, .85, 1, .85))
LEAF_COLORS = ((.36, .66, .30, .85), (.55, .75, .30, .85),
               (.93, .62, .20, .85), (.85, .40, .22, .85))


class Ambient:
    def __init__(self, pixel2d, task_mgr, size_fn, count=40):
        self._task_mgr, self._size, self._count = task_mgr, size_fn, count
        self.root = pixel2d.attachNewNode('Ambient', -10)
        self.root.hide()
        self.theme = 'light'
        self._particles = []
        self._task = None
        self._time = 0.0
        self._build()

    def set_theme(self, theme):
        self.theme = theme
        self._build()

    def set_intensity(self, alpha):
        """1.0 in menus; lower while playing so the board stays readable."""
        self.root.setAlphaScale(alpha)

    def _clear(self):
        for p in self._particles:
            p['node'].removeNode()
        self._particles = []

    def _spawn(self, p, anywhere):
        w, h = self._size()
        p['x'] = random.uniform(-40, w + 40)
        p['y'] = random.uniform(-20, h) if anywhere else random.uniform(-80, -10)
        night = self.theme == 'dark'
        p['vy'] = random.uniform(70, 170) if night else random.uniform(40, 95)
        p['vx'] = random.uniform(15, 60) if night else random.uniform(-10, 35)
        p['phase'] = random.uniform(0, 6.28)
        p['spin'] = random.uniform(-60, 60) if not night else random.uniform(-20, 20)

    def _build(self):
        self._clear()
        night = self.theme == 'dark'
        for _ in range(self._count):
            r = random.uniform(3, 8) if night else random.uniform(8, 15)
            color = random.choice(NIGHT_COLORS if night else LEAF_COLORS)
            node = _shape(_sparkle(r) if night else _leaf(r), color)
            node.reparentTo(self.root)
            p = {'node': node}
            self._spawn(p, anywhere=True)
            p['node'].setR(random.uniform(0, 360))
            self._particles.append(p)

    def _update(self, task):
        from panda3d.core import ClockObject
        dt = min(ClockObject.getGlobalClock().getDt(), .05)
        self._time += dt
        w, h = self._size()
        night = self.theme == 'dark'
        for p in self._particles:
            sway = 0 if night else math.sin(self._time * 1.6 + p['phase']) * 40
            p['x'] += (p['vx'] + sway) * dt
            p['y'] += p['vy'] * dt
            if p['y'] > h + 30 or p['x'] > w + 50 or p['x'] < -50:
                self._spawn(p, anywhere=False)
            node = p['node']
            node.setPos(p['x'], 0, -p['y'])
            node.setR(node.getR() + p['spin'] * dt)
            if night:   # twinkle
                s = .6 + .4 * math.sin(self._time * 5 + p['phase'])
                node.setScale(s)
        return task.cont

    def show(self):
        self.root.show()
        if self._task is None:
            self._task = self._task_mgr.add(self._update, 'AmbientParticles')

    def hide(self):
        self.root.hide()
        if self._task is not None:
            self._task_mgr.remove(self._task)
            self._task = None

    def dispose(self):
        self.hide()
        self._clear()
        self.root.removeNode()