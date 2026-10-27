"""Level intro: tiles rise in a diagonal wave, then the block drops in."""


def _back(u):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (u - 1) ** 3 + c1 * (u - 1) ** 2


class LevelIntro:
    TILE_TIME, WAVE, DROP_TIME, DEPTH, DROP_HEIGHT = .5, .8, .45, 5.0, 5.0

    def __init__(self, app, on_done=None):
        self.app, self.on_done = app, on_done
        self.active = False
        self._hidden_growth = []
        self._items, self._t, self._task, self._block_z = [], 0.0, None, 0.0

    @staticmethod
    def _cell(node):
        tag = node.getTag('cell')
        if not tag:
            found = node.find('**/=cell')
            tag = found.getTag('cell') if not found.isEmpty() else ''
        try:
            r, c = tag.split(',')
            return int(r), int(c)
        except ValueError:
            return 0, 0

    def play(self, rows, cols):
        self.finish(notify=False)
        app = self.app
        for node in app.static_board_root.findAllMatches('**/TempleEdgeGrowth'):
            if not node.isHidden():
                node.hide()
                self._hidden_growth.append(node)
        span = max(1, rows + cols - 2)
        for root in (app.static_board_root, app.dynamic_tile_root):
            for node in root.findAllMatches('**/=cell'):
                r, c = self._cell(node)
                self._items.append((node, node.getPos(), (r + c) / span * self.WAVE))
        for node, pos, _ in self._items:
            node.setPos(pos[0], pos[1], pos[2] - self.DEPTH)
            node.setScale(.01)
        self._block_z = app.block_root.getZ()
        app.block_root.hide()
        self._t, self.active = 0.0, True
        self._task = app.taskMgr.add(self._update, 'LevelIntro')

    def _update(self, task):
        from panda3d.core import ClockObject
        self._t += min(ClockObject.getGlobalClock().getDt(), .05)
        t = self._t
        for node, pos, delay in self._items:
            if node.isEmpty():
                continue
            u = min(1.0, max(0.0, (t - delay) / self.TILE_TIME))
            node.setPos(pos[0], pos[1], pos[2] - self.DEPTH * (1 - _back(u)))
            node.setScale(.01 + .99 * (1 - (1 - u) ** 3))
        tb = (t - (self.WAVE + self.TILE_TIME)) / self.DROP_TIME
        block = self.app.block_root
        if tb > 0:
            block.show()
            block.setZ(self._block_z + self.DROP_HEIGHT * (1 - min(1.0, tb)) ** 2)
        if tb >= 1:
            self.finish()
            return task.done
        return task.cont

    def finish(self, notify=True):
        if self._task is not None:
            self.app.taskMgr.remove(self._task)
            self._task = None
        for node, pos, _ in self._items:
            if not node.isEmpty():
                node.setPos(pos)
                node.setScale(1)
        self._items = []
        for node in self._hidden_growth:
            if not node.isEmpty():node.show()
        self._hidden_growth=[]
        block = self.app.block_root
        if not block.isEmpty():
            block.setZ(self._block_z)
            block.show()
        was_active, self.active = self.active, False
        if notify and was_active and self.on_done:
            self.on_done()