"""Manual move assistance: Core previews, projected arrows and sparse overlays."""
import math

from src.gui.mouse_control import controlled_cells, pick_action, pointer_over_hud

ARROW_Z = .04
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


class MoveAssistLayer:
    def __init__(self, app, controller, visible_fn):
        from src.gui.controller import ACTION_TO_ROLL
        self.app, self.controller, self._visible = app, controller, visible_fn
        self.root = app.render.attachNewNode('MoveAssistLayer')
        from src.gui.scene_style import SHADOW_MASK
        self.root.hide(SHADOW_MASK)
        self.root.hide()
        self._arrows, self._base = {}, {}
        for action, direction in ACTION_TO_ROLL.items():
            dx, dy, _ = direction.value
            node = _arrow_node()
            node.reparentTo(self.root)
            node.setDepthTest(False)
            node.setDepthWrite(False)
            node.setBin('fixed', 40)
            node.setH(math.degrees(math.atan2(dy, dx)))
            self._arrows[action] = (node, dx, dy)
        from src.gui.move_assist import MovePredictor
        from panda3d.core import TextNode
        self.predictor = MovePredictor()
        self.preview = None
        self._preview_key = None
        self._overlay = self.root.attachNewNode('LandingPreview')
        self._edge = self.root.attachNewNode('ExposedEdges')
        self._labels = {}
        for action, (node, _, _) in self._arrows.items():
            text = TextNode('Safety-' + action)
            text.setAlign(TextNode.ACenter)
            label = self.root.attachNewNode(text)
            label.setBillboardPointEye()
            label.setScale(.16)
            text.setCardColor(.02,.04,.07,.8)
            text.setCardAsMargin(.15,.15,.1,.1)
            label.setLightOff(1)
            label.setDepthTest(False)
            self._labels[action] = label
        text = TextNode('MoveWarning')
        text.setAlign(TextNode.ACenter)
        text.setCardColor(.03, .05, .09, .88)
        text.setCardAsMargin(.5, .5, .22, .22)
        self.warning = app.pixel2d.attachNewNode(text)
        self.warning.setScale(18)
        self.warning.setBin('fixed', 55)
        self.warning.hide()
        self._key = None
        self._task = app.taskMgr.add(self._update, 'MoveAssistLayer')

    def _place(self):
        from src.gui.geometry_math import cell_to_world
        c = self.controller
        bd = c.board_data
        points = [cell_to_world(r, col, rows=bd.rows, cols=bd.cols, pitch=1.0)
                  for r, col in controlled_cells(c.state)]
        cx = sum(p[0] for p in points)/len(points)
        cy = sum(p[1] for p in points)/len(points)
        for action, (_, dx, dy) in self._arrows.items():
            distance = max((x-cx)*dx+(y-cy)*dy for x,y in points)+1
            self._base[action] = (cx+dx*distance, cy+dy*distance)

    def _hover(self):
        c, app = self.controller, self.app
        from direct.gui.DirectGuiBase import DirectGuiWidget
        watcher = app.mouseWatcherNode
        region = watcher.getOverRegion()
        if (region is not None and region.getName() in DirectGuiWidget.guiDict
                or pointer_over_hud(app)):
            return None
        return pick_action(app, app.dashboard.viewport.region,
                           app.presentation.camera.current_fit,
                           controlled_cells(c.state), c.board_data.rows,
                           c.board_data.cols)

    COLORS = {'safe': (.13, .78, .52, .9),
              'danger': (1, .24, .20, 1), 'blocked': (.6, .64, .7, .9)}
    SYMBOLS = {'safe': 'OK', 'danger': '!', 'blocked': 'X'}

    def _xy(self, cell):
        # Assist-only mapping deliberately accepts cells outside the board.
        bd = self.controller.board_data
        r, c = cell
        return c - (bd.cols - 1) / 2, (bd.rows - 1) / 2 - r

    def _draw_edges(self):
        from panda3d.core import LineSegs
        self._edge.node().removeAllChildren()
        lines = LineSegs('NearEdge')
        lines.setColor(1, .72, .12, 1)
        lines.setThickness(3)
        for cell, action in self.preview.edges:
            x, y = self._xy(cell)
            _, dx, dy = self._arrows[action]
            cx, cy = x + .48*dx, y + .48*dy
            lines.moveTo(cx-.46*dy, cy+.46*dx, .025)
            lines.drawTo(cx+.46*dy, cy-.46*dx, .025)
        node = self._edge.attachNewNode(lines.create())
        node.setLightOff(1)

    def _draw_landing(self, hover):
        from panda3d.core import LineSegs, CardMaker, TransparencyAttrib
        self._overlay.node().removeAllChildren()
        if hover is None:
            return
        move = self.preview.for_action(hover)
        color = self.COLORS[move.severity.value]
        bd = self.controller.board_data
        markers = tuple((cell, False) for cell in move.landing_cells) + tuple(
            (cell, True) for cell in move.markers if cell not in move.landing_cells)
        for cell, secondary in markers:
            x, y = self._xy(cell)
            lines = LineSegs('TeleportTarget' if secondary else 'LandingFootprint')
            lines.setColor(*color)
            lines.setThickness(2 if secondary else 3)
            half = .35 if secondary else .46
            for index, (dx, dy) in enumerate(((-half,-half),(half,-half),
                                              (half,half),(-half,half),(-half,-half))):
                (lines.moveTo if index == 0 else lines.drawTo)(x+dx, y+dy, .045)
            line = self._overlay.attachNewNode(lines.create())
            line.setLightOff(1)
            # Off-map cells receive an outline only. A translucent inset keeps
            # surface symbols visible and cannot be mistaken for a floor tile.
            if 0 <= cell[0] < bd.rows and 0 <= cell[1] < bd.cols:
                card = CardMaker('LandingTint')
                card.setFrame(-half, half, -half, half)
                node = self._overlay.attachNewNode(card.generate())
                node.setP(-90)
                node.setPos(x, y, .026)
                node.setColor(*color[:3], .12)
                node.setTransparency(TransparencyAttrib.MAlpha)
                node.setLightOff(1)
                node.setDepthWrite(False)

    def _present_arrow(self, action):
        """Keep four floor markers outside the projected actor silhouette.

        A tall block otherwise hides the rear arrows in Iso/Follow. Camera
        changes only reproject these positions, never recompute Core previews.
        """
        from src.gui.camera import project_point
        fit = self.app.presentation.camera.current_fit
        bx, by = self._base[action]
        _,dx,dy = self._arrows[action]
        if fit is None:
            return bx,by,.16
        points = [self._xy(cell) for cell in controlled_cells(self.controller.state)]
        xs,ys = zip(*points)
        height = 1 if self.controller.state.is_split() else (2 if self.controller.state.is_standing() else 1)
        corners = [project_point((x,y,z),fit)[:2] for x in (min(xs)-.5,max(xs)+.5)
                   for y in (min(ys)-.5,max(ys)+.5) for z in (0,height)]
        left,right,bottom,top = self.app.dashboard.viewport.region.getDimensions()
        vw=(right-left)*self.app.win.getXSize()
        vh=(top-bottom)*self.app.win.getYSize()
        margin_x,margin_y = 24/max(1,vw),24/max(1,vh)
        xmin,xmax=min(p[0] for p in corners)-margin_x,max(p[0] for p in corners)+margin_x
        ymin,ymax=min(p[1] for p in corners)-margin_y,max(p[1] for p in corners)+margin_y
        for step in range(9):
            x,y=bx+dx*.25*step,by+dy*.25*step
            px,py,_=project_point((x,y,.5),fit)
            if not (xmin<px<xmax and ymin<py<ymax):
                # Do not trade occlusion for a marker outside the viewport.
                if abs(px)<.94 and abs(py)<.94:
                    bx,by=x,y
                break
        # Mouse control measures direction in the actor's mid-height plane.
        # Intersect that projected anchor's ray with the guide plane so clicking
        # the visible arrow agrees with hover, including a lying two-cell block.
        px,py,_ = project_point((bx,by,.5),fit)
        ray = tuple(fit.forward[i] + px*math.tan(math.radians(fit.horizontal_fov)/2)*fit.right[i]
                    + py*math.tan(math.radians(fit.vertical_fov)/2)*fit.up[i] for i in range(3))
        distance = (ARROW_Z-fit.position[2])/ray[2]
        bx,by = fit.position[0]+distance*ray[0],fit.position[1]+distance*ray[1]
        depth=sum((p-q)*v for p,q,v in zip((bx,by,.24),fit.position,fit.forward))
        unit=2*depth*math.tan(math.radians(fit.vertical_fov)/2)/max(1,vh)
        return bx,by,max(.10,12*unit)

    def _update(self, task):
        if not self._visible():
            self.root.hide()
            self.warning.hide()
            self._preview_key = None
            self._overlay.node().removeAllChildren()
            return task.cont
        c = self.controller
        key = (c.session_id, c.revision, c.state)
        if key != self._key:
            self._place()
            self.preview = self.predictor.get(c.board, c.state, c.session_id)
            self._draw_edges()
            self._key = key
        self.root.show()
        from src.gui.scene_style import SHADOW_MASK
        self.root.hide(SHADOW_MASK)
        hover = self._hover()
        if (key, hover) != self._preview_key:
            self._draw_landing(hover)
            self._preview_key = (key, hover)
        message = self.preview.for_action(hover).message if hover else (
            'Near edge' if self.preview.edges else '')
        self.warning.node().setText(message)
        self.warning.node().setTextColor(*(self.COLORS[
            self.preview.for_action(hover).severity.value] if hover else (1, .75, .2, 1)))
        self.warning.setPos(self.app.win.getXSize()/2, 0, -self.app.win.getYSize()+112)
        self.warning.show() if message else self.warning.hide()
        for action, (node, dx, dy) in self._arrows.items():
            bx, by, text_scale = self._present_arrow(action)
            move = self.preview.for_action(action)
            color = self.COLORS[move.severity.value]
            node.setPos(bx, by, ARROW_Z)
            node.setColor(*color)
            node.setScale(.85 if action == hover else .72)
            label = self._labels[action]
            label.node().setText(self.SYMBOLS[move.severity.value])
            label.node().setTextColor(*color)
            label.setPos(bx, by, .24)
            label.setScale(text_scale)
        return task.cont

    def dispose(self):
        if self._task is not None:
            self.app.taskMgr.remove(self._task)
            self._task = None
        self.warning.removeNode()
        self.predictor.clear()
        self.preview = self._key = self._preview_key = None
        self._overlay.removeNode()
        self._edge.removeNode()
        self._arrows.clear()
        self._labels.clear()
        self.root.removeNode()


# Compatibility for hosts importing the former arrow-only component.
MoveArrows = MoveAssistLayer
