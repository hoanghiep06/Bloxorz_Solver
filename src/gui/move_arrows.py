"""Floor arrows around the block for mouse control (one per roll direction)."""
import math

from src.gui.mouse_control import controlled_cells, pick_action

ARROW_Z = .04
COLD, HOT = (.96, .72, .24, .75), (1.0, .9, .35, 1.0)
POINTS = ((.38, 0), (.02, .3), (.02, -.3), (.02, .1), (-.3, .1), (-.3, -.1), (.02, -.1))
TRIANGLES = ((0, 1, 2), (3, 4, 5), (3, 5, 6))


def _arrow_node():
    from panda3d.core import (Geom, GeomNode, GeomTriangles, GeomVertexData,
                              GeomVertexFormat, GeomVertexWriter, NodePath,
                              TransparencyAttrib)
    data = GeomVertexData('arrow', GeomVertexFormat.getV3(), Geom.UHStatic)
    data.setNumRows(len(POINTS))
    vertex = GeomVertexWriter(data, 'vertex')
    for x, y in POINTS:
        vertex.addData3(x, y, 0)
    triangles = GeomTriangles(Geom.UHStatic)
    for tri in TRIANGLES:
        triangles.addVertices(*tri)
    geom = Geom(data)
    geom.addPrimitive(triangles)
    node = GeomNode('arrow')
    node.addGeom(geom)
    path = NodePath(node)
    path.setTwoSided(True)
    path.setLightOff(1)
    path.setShaderOff(1)
    path.setTransparency(TransparencyAttrib.MAlpha)
    path.setDepthOffset(1)
    return path


class MoveArrows:
    def __init__(self, app, controller, visible_fn):
        from src.gui.controller import ACTION_TO_ROLL
        self.app, self.controller, self._visible = app, controller, visible_fn
        self.root = app.render.attachNewNode('MoveArrows')
        self.root.hide()
        self._arrows, self._base = {}, {}
        for action, direction in ACTION_TO_ROLL.items():
            dx, dy, _ = direction.value
            node = _arrow_node()
            node.reparentTo(self.root)
            node.setH(math.degrees(math.atan2(dy, dx)))
            self._arrows[action] = (node, dx, dy)
        self._key, self._time = None, 0.0
        self._task = app.taskMgr.add(self._update, 'MoveArrows')

    def _place(self):
        from src.gui.geometry_math import cell_to_world
        c = self.controller
        bd = c.board_data
        points = [cell_to_world(r, col, rows=bd.rows, cols=bd.cols, pitch=1.0)
                  for r, col in controlled_cells(c.state)]
        for action, (_, dx, dy) in self._arrows.items():
            far = max(points, key=lambda p: p[0] * dx + p[1] * dy)
            self._base[action] = (far[0] + dx, far[1] + dy)

    def _hover(self):
        c, app = self.controller, self.app
        try:
            return pick_action(app, app.dashboard.viewport.region,
                               app.presentation.camera.current_fit,
                               controlled_cells(c.state), c.board_data.rows,
                               c.board_data.cols)
        except Exception:
            return None

    def _update(self, task):
        from panda3d.core import ClockObject
        self._time += ClockObject.getGlobalClock().getDt()
        if not self._visible():
            self.root.hide()
            return task.cont
        c = self.controller
        key = (c.session_id, c.revision)
        if key != self._key:
            self._place()
            self._key = key
        self.root.show()
        hover = self._hover()
        pulse = .06 * math.sin(self._time * 4)
        for action, (node, dx, dy) in self._arrows.items():
            bx, by = self._base[action]
            node.setPos(bx + dx * pulse, by + dy * pulse, ARROW_Z)
            hot = action == hover
            node.setColor(*(HOT if hot else COLD))
            node.setScale(1.2 if hot else 1.0)
        return task.cont

    def dispose(self):
        if self._task is not None:
            self.app.taskMgr.remove(self._task)
            self._task = None
        self.root.removeNode()
