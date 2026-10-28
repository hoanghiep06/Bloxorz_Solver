"""Level intro: tiles rise in a diagonal wave, then the block slams down.

The drop is a real free fall (accelerating), followed by an impact:
  * the block squashes and springs back (scaled around its footprint),
  * a ring of dust puffs bursts out of the landing tiles,
  * stone chips fly off and cracks are drawn on the landing tiles,
  * the landing tiles sag then recover, a small ripple runs through the floor,
  * the board shakes briefly.
Input stays locked until the settle phase is over (on_done is called then).
Dust/chips are pure visuals that keep running after the intro has finished;
cracks stay on the floor until the level is left or the intro is replayed.
"""
import math
import random

from panda3d.core import (CardMaker, ClockObject, Geom, GeomNode, GeomTriangles,
                          GeomVertexData, GeomVertexFormat, GeomVertexWriter,
                          LineSegs, PNMImage, Texture, TransparencyAttrib, Vec3)


def _back(u):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (u - 1) ** 3 + c1 * (u - 1) ** 2


# ---------------------------------------------------------------- fx assets
_PUFF_TEXTURE = None


def _puff_texture():
    """Soft round white blob with a smooth alpha falloff (built once)."""
    global _PUFF_TEXTURE
    if _PUFF_TEXTURE is None:
        n = 64
        image = PNMImage(n, n, 4)
        for y in range(n):
            for x in range(n):
                r = math.hypot((x + .5) / n * 2 - 1, (y + .5) / n * 2 - 1)
                a = max(0.0, 1 - r)
                a = a * a * (3 - 2 * a)
                image.setXelA(x, y, 1, 1, 1, a)
        texture = Texture('IntroDust')
        texture.load(image)
        texture.setMinfilter(Texture.FTLinear)
        texture.setMagfilter(Texture.FTLinear)
        texture.setWrapU(Texture.WMClamp)
        texture.setWrapV(Texture.WMClamp)
        _PUFF_TEXTURE = texture
    return _PUFF_TEXTURE


def _chip_mesh():
    """Unit cube with baked per-face shading (drawn unlit, two-sided)."""
    data = GeomVertexData('IntroChip', GeomVertexFormat.getV3c4(), Geom.UHStatic)
    vertex, color = GeomVertexWriter(data, 'vertex'), GeomVertexWriter(data, 'color')
    triangles = GeomTriangles(Geom.UHStatic)
    h = .5
    faces = (
        (((-h, -h, h), (h, -h, h), (h, h, h), (-h, h, h)), 1.0),
        (((-h, -h, -h), (-h, h, -h), (h, h, -h), (h, -h, -h)), .45),
        (((-h, -h, -h), (h, -h, -h), (h, -h, h), (-h, -h, h)), .75),
        (((h, -h, -h), (h, h, -h), (h, h, h), (h, -h, h)), .62),
        (((h, h, -h), (-h, h, -h), (-h, h, h), (h, h, h)), .75),
        (((-h, h, -h), (-h, -h, -h), (-h, -h, h), (-h, h, h)), .62),
    )
    base = 0
    for corners, shade in faces:
        for point in corners:
            vertex.addData3(*point)
            color.addData4(shade, shade, shade, 1)
        triangles.addVertices(base, base + 1, base + 2)
        triangles.addVertices(base, base + 2, base + 3)
        base += 4
    geom = Geom(data)
    geom.addPrimitive(triangles)
    node = GeomNode('IntroChip')
    node.addGeom(geom)
    return node


class _ImpactFx:
    """Dust puffs, stone chips and floor cracks for the landing tiles."""
    GRAVITY = 16.0
    CHIP_LIFE = 1.3

    def __init__(self, render, centers, floor_z, pitch, theme, seed=7):
        self.age = 0.0
        self.floor, self.pitch = floor_z, pitch
        self.root = render.attachNewNode('LevelIntroFx')
        self.root.setLightOff(1)
        self.root.setShaderOff(1)
        rng = random.Random(seed)
        light = theme != 'dark'
        dust = (.82, .78, .72) if light else (.62, .63, .68)
        stone = (.66, .63, .58) if light else (.42, .42, .46)
        crack_color = (.07, .06, .05, 1) if light else (.02, .02, .03, 1)
        card = CardMaker('IntroPuff')
        card.setFrame(-.5, .5, -.5, .5)
        card_node = card.generate()
        chip_node = _chip_mesh()
        texture = _puff_texture()
        self.puffs, self.chips, self.cracks = [], [], []

        for cx, cy in centers:
            for i in range(14):
                angle = math.tau * (i + rng.random() * .6) / 14
                holder = self.root.attachNewNode('Puff')
                holder.setBillboardPointEye()
                holder.attachNewNode(card_node)
                holder.setTexture(texture)
                holder.setTransparency(TransparencyAttrib.MAlpha)
                holder.setDepthWrite(False)
                holder.setColorScale(*dust, 1)
                holder.setAlphaScale(0)
                self.puffs.append(dict(
                    node=holder, origin=(cx, cy),
                    direction=(math.cos(angle), math.sin(angle)),
                    speed=(.7 + rng.random() * 1.1) * pitch,
                    life=.8 + rng.random() * .7,
                    size0=(.30 + rng.random() * .20) * pitch,
                    size1=(.90 + rng.random() * .70) * pitch,
                    rise=(.25 + rng.random() * .40) * pitch))
            for _ in range(9):
                angle = rng.random() * math.tau
                speed = (1.2 + rng.random() * 2.0) * pitch
                node = self.root.attachNewNode('Chip')
                node.attachNewNode(chip_node)
                node.setTwoSided(True)
                shade = .8 + rng.random() * .3
                node.setColorScale(stone[0] * shade, stone[1] * shade, stone[2] * shade, 1)
                node.setScale((.07 + rng.random() * .09) * pitch,
                              (.07 + rng.random() * .09) * pitch,
                              (.04 + rng.random() * .06) * pitch)
                node.setTransparency(TransparencyAttrib.MAlpha)
                self.chips.append(dict(
                    node=node,
                    pos=Vec3(cx + (rng.random() - .5) * .3 * pitch,
                             cy + (rng.random() - .5) * .3 * pitch, floor_z + .05 * pitch),
                    vel=Vec3(math.cos(angle) * speed, math.sin(angle) * speed,
                             (2.5 + rng.random() * 3.0) * pitch),
                    spin=Vec3((rng.random() - .5) * 720, (rng.random() - .5) * 720,
                              (rng.random() - .5) * 720),
                    hpr=Vec3(rng.random() * 360, rng.random() * 360, rng.random() * 360),
                    resting=False))
            self.cracks.append(self._make_crack(cx, cy, pitch, crack_color, rng))

    def _make_crack(self, cx, cy, pitch, color, rng):
        segs = LineSegs('Crack')
        segs.setThickness(2.5)
        segs.setColor(*color)
        main = 7
        for k in range(main):
            angle = math.tau * (k + rng.random() * .5) / main
            radius = 0.0
            x, y = cx, cy
            segs.moveTo(x, y, 0)
            for step in range(3):
                radius += (.12 + rng.random() * .10) * pitch
                angle += (rng.random() - .5) * .7
                x, y = cx + math.cos(angle) * radius, cy + math.sin(angle) * radius
                segs.drawTo(x, y, 0)
                if step == 1 and rng.random() < .6:
                    branch = angle + (1 if rng.random() < .5 else -1) * (.5 + rng.random() * .5)
                    segs.moveTo(x, y, 0)
                    segs.drawTo(x + math.cos(branch) * .14 * pitch,
                                y + math.sin(branch) * .14 * pitch, 0)
                    segs.moveTo(x, y, 0)
        node = self.root.attachNewNode(segs.create())
        node.setPos(0, 0, self.floor + .015 * pitch)
        node.setTransparency(TransparencyAttrib.MAlpha)
        node.setAlphaScale(0)
        return node

    def update(self, dt):
        """Advance particles; returns True while dust/chips are still alive."""
        self.age += dt
        t = self.age
        alive = False
        for crack in self.cracks:
            crack.setAlphaScale(min(1.0, t / .06))
        for p in self.puffs:
            u = t / p['life']
            if u >= 1:
                p['node'].hide()
                continue
            alive = True
            e = 1 - (1 - u) ** 2
            dist = p['speed'] * p['life'] * .55 * e
            node = p['node']
            node.setPos(p['origin'][0] + p['direction'][0] * dist,
                        p['origin'][1] + p['direction'][1] * dist,
                        self.floor + .06 * self.pitch + p['rise'] * e)
            node.setScale(p['size0'] + (p['size1'] - p['size0']) * e)
            node.setAlphaScale(.6 * (1 - u) ** 1.5 * min(1.0, t / .05))
        ground = self.floor + .02 * self.pitch
        for c in self.chips:
            node = c['node']
            if t >= self.CHIP_LIFE:
                node.hide()
                continue
            alive = True
            if not c['resting']:
                c['vel'].setZ(c['vel'].getZ() - self.GRAVITY * self.pitch * dt)
                c['pos'] += c['vel'] * dt
                c['hpr'] += c['spin'] * dt
                if c['pos'].getZ() <= ground:
                    c['pos'].setZ(ground)
                    c['resting'] = True
                node.setPos(c['pos'])
                node.setHpr(c['hpr'])
            node.setAlphaScale(min(1.0, (self.CHIP_LIFE - t) / .4))
        return alive

    def dispose(self):
        if not self.root.isEmpty():
            self.root.removeNode()


class LevelIntro:
    TILE_TIME, WAVE, DROP_TIME, DEPTH, DROP_HEIGHT = .5, .8, .5, 5.0, 4.0
    SETTLE = .5          # impact recovery before input unlocks
    SHAKE = .05          # board shake amplitude (in tile sizes); 0 disables
    TILE_DIP = .15       # how far the landing tiles sag (in tile sizes)

    def __init__(self, app, on_done=None):
        self.app, self.on_done = app, on_done
        self.active = False
        self._hidden_growth = []
        self._items, self._t, self._task = [], 0.0, None
        self._pos0 = self._scale0 = None
        self._dropping = self._landed = False
        self._pivot = None
        self._centers, self._dists = [], []
        self._pitch, self._floor_z = 1.0, 0.0
        self._fx = self._fx_task = None

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

    # ------------------------------------------------------------------ play
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
                self._items.append((node, node.getPos(), (r + c) / span * self.WAVE,
                                    node.getPos(app.render)))
        self._pitch = self._estimate_pitch([item[3] for item in self._items])
        for node, pos, _, _ in self._items:
            node.setPos(pos[0], pos[1], pos[2] - self.DEPTH)
            node.setScale(.01)
        block = app.block_root
        self._pos0, self._scale0 = block.getPos(), block.getScale()
        block.hide()
        self._dropping = self._landed = False
        self._pivot, self._centers, self._dists = None, [], []
        self._t, self.active = 0.0, True
        self._task = app.taskMgr.add(self._update, 'LevelIntro')

    @staticmethod
    def _estimate_pitch(points):
        best = None
        for axis in (0, 1):
            values = sorted({round(p[axis], 3) for p in points})
            for a, b in zip(values, values[1:]):
                if b - a > .2 and (best is None or b - a < best):
                    best = b - a
        return best or 1.0

    # ------------------------------------------------------------ impact setup
    def _measure(self):
        """Footprint of the visible block(s) in world space, at rest."""
        render, block = self.app.render, self.app.block_root
        boxes = []
        for node in block.findAllMatches('**/=actor_id'):
            if not node.isHidden():
                bounds = node.getTightBounds(render)
                if bounds:
                    boxes.append(bounds)
        if not boxes:
            bounds = block.getTightBounds(render)
            if bounds:
                boxes.append(bounds)
        if not boxes:
            return
        eps = .12 * self._pitch
        centers = []
        for lo, hi in boxes:
            found = False
            for _, _, _, w in self._items:
                if lo[0] - eps <= w[0] <= hi[0] + eps and lo[1] - eps <= w[1] <= hi[1] + eps:
                    key = (round(w[0], 2), round(w[1], 2))
                    if key not in [(round(a, 2), round(b, 2)) for a, b in centers]:
                        centers.append((w[0], w[1]))
                    found = True
            if not found:
                centers.append(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2))
        self._centers = centers[:4]
        lo_x = min(b[0][0] for b in boxes); hi_x = max(b[1][0] for b in boxes)
        lo_y = min(b[0][1] for b in boxes); hi_y = max(b[1][1] for b in boxes)
        self._floor_z = min(b[0][2] for b in boxes)
        self._pivot = Vec3((lo_x + hi_x) / 2, (lo_y + hi_y) / 2, self._floor_z)

    def _begin_drop(self):
        self._dropping = True
        self.app.block_root.show()
        self._measure()

    def _land(self):
        self._landed = True
        self._dists = [min((math.hypot(w[0] - cx, w[1] - cy) for cx, cy in self._centers),
                           default=99.0) / self._pitch
                       for _, _, _, w in self._items]
        if not self._centers:
            return
        try:
            from src.gui import scene_style
            theme = getattr(scene_style, 'TILE_THEME', 'light')
        except Exception:
            theme = 'light'
        self._kill_fx()
        self._fx = _ImpactFx(self.app.render, self._centers, self._floor_z,
                             self._pitch, theme)
        self._fx_task = self.app.taskMgr.add(self._fx_update, 'LevelIntroFx')

    # ---------------------------------------------------------------- frames
    def _shake(self, ts):
        a = self.SHAKE * self._pitch * math.exp(-7 * ts)
        return (a * math.sin(ts * 71), a * math.cos(ts * 83), a * .6 * math.sin(ts * 97))

    def _tile_dip(self, index, ts):
        if index >= len(self._dists):
            return 0.0
        d = self._dists[index]
        dip = 0.0
        if d < .6:
            dip += self.TILE_DIP * self._pitch * max(0.0, 1 - ts / .7) ** 2
        tau = ts - d * .06
        if 0 < tau < .4:
            dip += .05 * self._pitch * math.exp(-d / 1.8) * math.sin(math.pi * tau / .4)
        return dip

    def _place_block(self, sz, sxy, dz, shake=(0, 0, 0)):
        """Scale the block around its footprint centre and lift it by dz."""
        block = self.app.block_root
        p0 = self._pos0
        if self._pivot is not None:
            p = self._pivot
            pos = (p[0] + sxy * (p0[0] - p[0]), p[1] + sxy * (p0[1] - p[1]),
                   p[2] + sz * (p0[2] - p[2]))
        else:
            pos = (p0[0], p0[1], p0[2])
        block.setPos(pos[0] + shake[0], pos[1] + shake[1], pos[2] + dz + shake[2])
        block.setScale(sxy, sxy, sz)

    def _update(self, task):
        self._t += min(ClockObject.getGlobalClock().getDt(), .05)
        t = self._t
        t_drop = self.WAVE + self.TILE_TIME
        ts = t - (t_drop + self.DROP_TIME)            # seconds since impact
        shake = self._shake(ts) if ts > 0 else (0, 0, 0)
        for index, (node, pos, delay, _) in enumerate(self._items):
            if node.isEmpty():
                continue
            u = min(1.0, max(0.0, (t - delay) / self.TILE_TIME))
            x, y = pos[0], pos[1]
            z = pos[2] - self.DEPTH * (1 - _back(u))
            if ts > 0:
                x, y, z = x + shake[0], y + shake[1], z - self._tile_dip(index, ts) + shake[2]
            node.setPos(x, y, z)
            node.setScale(.01 + .99 * (1 - (1 - u) ** 3))
        tb = (t - t_drop) / self.DROP_TIME
        if tb > 0:
            if not self._dropping:
                self._begin_drop()
            if tb < 1:
                # Free fall: height shrinks with t^2, so speed peaks at impact.
                self._place_block(1 + .05 * tb, 1 - .025 * tb,
                                  self.DROP_HEIGHT * (1 - tb * tb))
            else:
                if not self._landed:
                    self._land()
                u = min(1.0, ts / self.SETTLE)
                q = math.exp(-4.5 * u) * math.cos(7.5 * u)   # 1 = fully squashed
                self._place_block(1 - .20 * q, 1 + .09 * q, 0.0, shake)
                if ts >= self.SETTLE:
                    self._finish(True, keep_fx=True)
                    return task.done
        return task.cont

    def _fx_update(self, task):
        if self._fx is None:
            return task.done
        alive = self._fx.update(min(ClockObject.getGlobalClock().getDt(), .05))
        if not alive:
            self._fx_task = None        # cracks stay on the floor until finish()
            return task.done
        return task.cont

    def _kill_fx(self):
        if self._fx_task is not None:
            self.app.taskMgr.remove(self._fx_task)
            self._fx_task = None
        if self._fx is not None:
            self._fx.dispose()
            self._fx = None

    # ---------------------------------------------------------------- finish
    def finish(self, notify=True):
        self._finish(notify, keep_fx=False)

    def _finish(self, notify, keep_fx):
        if self._task is not None:
            self.app.taskMgr.remove(self._task)
            self._task = None
        for node, pos, _, _ in self._items:
            if not node.isEmpty():
                node.setPos(pos)
                node.setScale(1)
        self._items = []
        for node in self._hidden_growth:
            if not node.isEmpty():
                node.show()
        self._hidden_growth = []
        block = self.app.block_root
        if not block.isEmpty():
            if self._pos0 is not None:
                block.setPos(self._pos0)
                block.setScale(self._scale0)
            block.show()
        self._pos0 = self._scale0 = None
        if not keep_fx:
            self._kill_fx()
        was_active, self.active = self.active, False
        if notify and was_active and self.on_done:
            self.on_done()