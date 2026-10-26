"""Animated menu overlay: falling snow (dark theme) or drifting leaves + light motes (light theme).

Pure 2D particles on pixel2d, drawn behind the menu widgets. Cheap: ~60 nodes.
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


def _circle(r, segments=10):
    return [(r * math.cos(i * math.tau / segments), r * math.sin(i * math.tau / segments))
            for i in range(segments)]


def _leaf(r):
    return [(r * math.cos(i * math.tau / 14), r * .45 * math.sin(i * math.tau / 14))
            for i in range(14)]


SNOW_COLORS = ((1, 1, 1, .9), (.85, .93, 1, .8), (.75, .88, 1, .7))
MOTE_COLORS = ((1, .95, .6, .7), (1, 1, .85, .6))
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
        kind = p['kind']
        p['x'] = random.uniform(-40, w + 40)
        p['phase'] = random.uniform(0, 6.28)
        if kind == 'mote':                      # bụi sáng bay lên chậm
            p['y'] = random.uniform(-20, h) if anywhere else random.uniform(h + 10, h + 60)
            p['vy'] = -random.uniform(8, 25)
            p['vx'] = random.uniform(-6, 12)
            p['spin'] = 0
        elif kind == 'snow':                    # tuyết rơi chậm, lắc nhẹ
            p['y'] = random.uniform(-20, h) if anywhere else random.uniform(-80, -10)
            p['vy'] = random.uniform(35, 90)
            p['vx'] = random.uniform(-12, 8)
            p['spin'] = 0
        else:                                   # lá
            p['y'] = random.uniform(-20, h) if anywhere else random.uniform(-80, -10)
            p['vy'] = random.uniform(40, 95)
            p['vx'] = random.uniform(-10, 35)
            p['spin'] = random.uniform(-60, 60)

    def _plan(self):
        if self.theme == 'dark':
            return [('snow', self._count * 3 // 2)]
        return [('leaf', self._count // 2), ('mote', self._count)]

    def _build(self):
        self._clear()
        for kind, number in self._plan():
            for _ in range(number):
                if kind == 'snow':
                    shape, color = _circle(random.uniform(1.8, 4.5)), random.choice(SNOW_COLORS)
                elif kind == 'mote':
                    shape, color = _circle(random.uniform(2, 4.5)), random.choice(MOTE_COLORS)
                else:
                    shape, color = _leaf(random.uniform(8, 15)), random.choice(LEAF_COLORS)
                node = _shape(shape, color)
                node.reparentTo(self.root)
                p = {'node': node, 'kind': kind}
                self._spawn(p, anywhere=True)
                if kind == 'leaf':
                    node.setR(random.uniform(0, 360))
                self._particles.append(p)

    def _update(self, task):
        from panda3d.core import ClockObject
        dt = min(ClockObject.getGlobalClock().getDt(), .05)
        self._time += dt
        w, h = self._size()
        for p in self._particles:
            kind = p['kind']
            amp = {'snow': 18, 'leaf': 40, 'mote': 10}[kind]
            freq = {'snow': .9, 'leaf': 1.6, 'mote': .7}[kind]
            sway = math.sin(self._time * freq + p['phase']) * amp
            p['x'] += (p['vx'] + sway) * dt
            p['y'] += p['vy'] * dt
            gone = (p['y'] < -30) if kind == 'mote' else (p['y'] > h + 30)
            if gone or p['x'] > w + 50 or p['x'] < -50:
                self._spawn(p, anywhere=False)
            node = p['node']
            node.setPos(p['x'], 0, -p['y'])
            if kind == 'leaf':
                node.setR(node.getR() + p['spin'] * dt)
            elif kind == 'mote':                # lấp lánh
                node.setScale(.6 + .4 * math.sin(self._time * 3 + p['phase']))
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