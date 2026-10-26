"""Owned actor rig and leased dynamic surface visuals, not a game engine.

SurfaceLayer supplies a dedicated renderer_root to AdvancedSceneRenderer. During
an effect only that borrowed layer is hidden; animated_root owns all replacement
surface instances. Host roots and foreign nodes are never hidden or removed.
"""
from panda3d.core import NodePath, Quat, TransparencyAttrib

from src.gui.animation_math import smoothstep
from src.gui.animation_contracts import EventKind
from src.gui.advanced_contracts import AdvancedBoardData, SwitchVisualKind
from src.gui.advanced_mesh_factory import (
    make_active_cube_mesh, make_fragile_mesh,
    make_bridge_mesh, make_switch_mesh, PALETTES, THEMES,
)
from src.gui.mesh_factory import (make_beveled_box_mesh,
                                  make_themed_block_mesh, make_themed_cube_mesh)
from src.gui.geometry_math import cell_to_world


def visible(node, shown):
    node.show() if shown else node.hide()


def event_progress(event, progress):
    return max(0.0, min(1.0, (progress-event.start)/(event.end-event.start)))


class AnimatedActorRig:
    """One persistent whole and two cube slots; no per-frame geometry allocation."""
    def __init__(self, block_root, *, pitch=1.0):
        self.root = block_root.attachNewNode('AnimatedActorRig')
        self._disposed = False
        self.pitch = pitch
        self._slots = {}
        self._meshes = {(kind,theme): factory(theme,pitch=pitch)
                        for kind,factory in (('whole',make_themed_block_mesh),('cube',make_themed_cube_mesh))
                        for theme in ('light','dark')}
        self._whole, self._whole_model = self._actor(self.root, 'AnimatedWhole', 'whole')
        cubes = [self._actor(self.root, 'AnimatedCube', 'cube') for _ in range(2)]
        self._cubes = tuple(node for node, model in cubes)
        self._models = {None: self._whole_model}
        self._cube_models = tuple(model for node, model in cubes)
        self._indicators = tuple(node.attachNewNode(make_active_cube_mesh(pitch=pitch)) for node in self._cubes)
        # Persistent soft contact patches, clipped to real supporting tiles by
        # apply(). They never cast another shadow or create a floor over void.
        from panda3d.core import Geom, GeomNode, GeomTriangles, GeomVertexData, GeomVertexFormat, GeomVertexWriter
        from src.gui.scene_style import SHADOW_MASK
        import math
        data = GeomVertexData('ContactShadow', GeomVertexFormat.getV3c4(), Geom.UHStatic)
        vertex, color = GeomVertexWriter(data, 'vertex'), GeomVertexWriter(data, 'color')
        vertex.addData3(0, 0, 0); color.addData4(.02,.03,.05,.23)
        for i in range(25):
            a = math.tau*i/24
            vertex.addData3(math.cos(a),math.sin(a),0)
            color.addData4(.02,.03,.05,0)
        triangles = GeomTriangles(Geom.UHStatic)
        for i in range(24):triangles.addVertices(0,i+1,i+2)
        geom=Geom(data);geom.addPrimitive(triangles)
        mesh=GeomNode('ContactShadow');mesh.addGeom(geom)
        self._shadow_root=self.root.attachNewNode('ContactShadows')
        self._shadow_root.setLightOff(1);self._shadow_root.setShaderOff(1)
        self._shadow_root.setTransparency(TransparencyAttrib.MAlpha)
        self._shadow_root.setDepthWrite(False);self._shadow_root.hide(SHADOW_MASK)
        self._shadows=tuple(self._shadow_root.attachNewNode(f'Contact-{i}') for i in range(12))
        for shadow in self._shadows:shadow.attachNewNode(mesh)
        self.root.hide()

    def _actor(self, parent, name, kind):
        node = parent.attachNewNode(name)
        model = node.attachNewNode('LocalGeometry')
        for theme in ('light','dark'):
            holder = model.attachNewNode('BlockTheme-'+theme)
            holder.attachNewNode(self._meshes[kind,theme])
        from src.gui.scene_style import sync_block_theme
        sync_block_theme(model)
        node.setTransparency(TransparencyAttrib.MAlpha)
        return node, model

    def apply(self, poses, *, active_weights=None, opacity=None, scales=None, supports=()):
        if self._disposed:
            raise RuntimeError('Actor rig is disposed.')
        active_weights, opacity, scales = active_weights or {}, opacity or {}, scales or {}
        ids = [key for key in poses if key is not None]
        slots = {key: slot for key, slot in self._slots.items() if key in ids}
        available = [i for i in range(2) if i not in slots.values()]
        if len(ids) > 2:
            raise ValueError('Rig supports at most two split cubes.')
        for key in ids:
            if key not in slots:
                slots[key] = available.pop(0)
        self._slots = slots
        nodes = {None: self._whole, **{key: self._cubes[i] for key, i in slots.items()}}
        models = {None: self._whole_model, **{key: self._cube_models[i] for key, i in slots.items()}}
        for node in (self._whole, *self._cubes):
            node.hide()
        for marker in self._indicators:
            marker.hide()
        for key, pose in poses.items():
            node, model = nodes[key], models[key]
            visible(node, opacity.get(key, 1) > 0)
            node.setPos(*pose.center)
            node.setScale(scales.get(key, 1))
            node.setAlphaScale(opacity.get(key, 1))
            node.setTag('actor_id', 'WHOLE' if key is None else key)
            model.setQuat(Quat(*pose.quaternion))
            if key is not None:
                indicator = self._indicators[slots[key]]
                weight = active_weights.get(key, 0)
                visible(indicator, weight > 0)
                indicator.setTransparency(TransparencyAttrib.MAlpha)
                indicator.setAlphaScale(weight)
                # Active cue follows position and the world top, while the local
                # local bevel marker follows the rigid orientation underneath it.
                indicator.setZ(pose.extents[2]-self.pitch/2)
        for shadow in self._shadows:shadow.hide()
        slot = 0
        for key, pose in poses.items():
            scale = scales.get(key, 1)
            bottom = pose.center[2]-pose.extents[2]*scale
            if bottom < -.001 or opacity.get(key,1) <= 0:
                continue
            ex, ey = (v*scale for v in pose.extents[:2])
            for x, y in supports:
                lo_x,hi_x=max(x-.46*self.pitch,pose.center[0]-ex),min(x+.46*self.pitch,pose.center[0]+ex)
                lo_y,hi_y=max(y-.46*self.pitch,pose.center[1]-ey),min(y+.46*self.pitch,pose.center[1]+ey)
                if hi_x <= lo_x or hi_y <= lo_y or slot >= len(self._shadows):continue
                shadow=self._shadows[slot];slot+=1
                shadow.setPos((lo_x+hi_x)/2,(lo_y+hi_y)/2,.007*self.pitch)
                shadow.setScale((hi_x-lo_x)/2,(hi_y-lo_y)/2,1)
                shadow.setAlphaScale(opacity.get(key,1)/(1+max(0,pose.center[2]/self.pitch-.5)))
                shadow.show()
        self.root.show()

    def dispose(self):
        if self._disposed:
            return
        self.root.removeNode()
        self._slots.clear()
        self._models.clear()
        self._meshes.clear()
        self._whole = self._whole_model = None
        self._cubes = self._cube_models = self._indicators = ()
        self._shadows = ()
        self._shadow_root = None
        self._disposed = True


class AnimatedSurfaceLayer:
    """Dedicated dynamic ownership boundary; never inspect renderer private nodes.

    Construct before AdvancedSceneRenderer and pass renderer_root as its dynamic
    root. AnimatedSurfaceLayer itself must be disposed after that renderer.
    """
    def __init__(self, dynamic_root, board_data, *, pitch=1.0):
        if not isinstance(dynamic_root, NodePath) or dynamic_root.isEmpty():
            raise ValueError('Expected live DynamicTileRoot.')
        if type(board_data) is not AdvancedBoardData:
            raise TypeError('Surface layer requires AdvancedBoardData (use as_visual_board for Basic).')
        board_data.__post_init__()
        self.board = board_data
        self.pitch = pitch
        self.root = dynamic_root.attachNewNode('AnimationSurfaceLayer')
        self.renderer_root = self.root.attachNewNode('StaticSurfaceLease')
        self.animated_root = self.root.attachNewNode('AnimatedSurfaceContent')
        self.animated_root.hide()
        self._fragile, self._bridges, self._switches, self._debris = {}, {}, {}, {}
        self._tile_variants = {theme: [] for theme in THEMES}
        self._theme = None
        self._leased = False
        self._prior_hidden = False
        self._disposed = False
        try:
            intact = {theme: make_fragile_mesh(pitch=pitch, theme=theme) for theme in THEMES}
            broken = {theme: make_fragile_mesh(pitch=pitch, broken=True, theme=theme)
                      for theme in THEMES}
            platform = {theme: make_bridge_mesh(pitch=pitch, theme=theme) for theme in THEMES}
            switches = {(kind, active): {
                            theme: make_switch_mesh(kind, activated=active, pitch=pitch, theme=theme)
                            for theme in THEMES}
                        for kind in SwitchVisualKind for active in (False, True)}
            fragments = {theme: make_beveled_box_mesh(name='FragileFragment-' + theme,
                dimensions=(.30*pitch, .46*pitch, .16*pitch), bevel=.012*pitch,
                top_color=PALETTES[theme]['FRAGILE'],
                side_color=PALETTES[theme]['FRAGILE_SIDE'],
                edge_color=PALETTES[theme]['FRAGILE_EDGE']) for theme in THEMES}
            for cell in board_data.fragile_cells:
                self._fragile[cell] = tuple(self._instance(self.animated_root, mesh, cell)
                                            for mesh in (intact, broken))
                # Six reusable pieces per fragile tile. No nodes are allocated
                # by timeline sampling, pause, or cancellation.
                group = self.animated_root.attachNewNode('CollapseFragments')
                group.hide()
                pieces = tuple(group.attachNewNode(f'Fragment-{i}') for i in range(6))
                for piece in pieces:
                    self._add_theme_variants(piece, fragments)
                    piece.setTransparency(TransparencyAttrib.MAlpha)
                self._debris[cell] = group, pieces
            for bridge in board_data.bridges:
                group = self.animated_root.attachNewNode('AnimatedBridge-' + bridge.bridge_id)
                for cell in bridge.cells:
                    self._instance(group, platform, cell)
                self._bridges[bridge.bridge_id] = group
            for switch in board_data.switches:
                self._switches[switch.switch_id] = tuple(self._instance(self.animated_root,
                    switches[switch.kind, active], switch.cell) for active in (False, True))
            self._sync_theme()
        except BaseException:
            self.dispose()
            raise

    def _add_theme_variants(self, parent, meshes):
        for theme in THEMES:
            holder = parent.attachNewNode('TileTheme-' + theme)
            holder.attachNewNode(meshes[theme])
            self._tile_variants[theme].append(holder)

    def _sync_theme(self):
        # Follow the same theme API as the static renderer. Restrict our own
        # sampling to owned nodes; do not traverse or alter foreign scene roots.
        from src.gui.scene_style import TILE_THEME
        if TILE_THEME != self._theme:
            for theme, holders in self._tile_variants.items():
                for holder in holders:
                    visible(holder, theme == TILE_THEME)
            self._theme = TILE_THEME

    def _instance(self, parent, meshes, cell):
        wrapper = parent.attachNewNode(meshes[THEMES[0]].getName() + '-Instance')
        self._add_theme_variants(wrapper, meshes)
        x, y = cell_to_world(*cell, rows=self.board.rows, cols=self.board.cols, pitch=self.pitch)
        wrapper.setPos(x, y, 0)
        return wrapper

    def sample(self, before, events, progress, *, collapse_cell=None):
        if self._disposed:
            raise RuntimeError('Surface layer is disposed.')
        self._sync_theme()
        if not self._leased:
            self._prior_hidden = self.renderer_root.isHidden()
            self._leased = True
        self.renderer_root.hide()
        self.animated_root.show()
        for group, _ in self._debris.values():
            group.hide()
        for cell, (intact, broken) in self._fragile.items():
            is_broken = cell in before.broken_fragile_cells
            visible(intact, not is_broken)
            visible(broken, is_broken)
            intact.clearColorScale()
            intact.setZ(0)
            broken.setZ(0)
        for state in before.bridge_states:
            node = self._bridges[state.bridge_id]
            visible(node, state.present)
            node.setZ(0)
            node.setScale(1)
        for key, (inactive, active) in self._switches.items():
            on = key in before.activated_switch_ids
            visible(inactive, not on)
            visible(active, on)
            inactive.setZ(0)
            active.setZ(0)
        for event in events:
            if progress < event.start:
                continue
            u = smoothstep(event_progress(event, progress))
            if event.kind is EventKind.FRAGILE_BREAK:
                intact, broken = self._fragile[event.cell]
                # This phase is the brief crack/sag; terminal collapse owns the
                # simultaneous free fall of the actor and individual fragments.
                visible(intact, True)
                visible(broken, False)
                intact.setColorScale(1-.35*u, 1-.35*u, 1-.35*u, 1)
                intact.setZ(-.025*self.pitch*u)
            elif event.kind in (EventKind.BRIDGE_PRESENT, EventKind.BRIDGE_ABSENT):
                node = self._bridges[event.target_id]
                amount = u if event.kind is EventKind.BRIDGE_PRESENT else 1-u
                visible(node, amount > 0)
                node.setZ(-.65*self.pitch*(1-amount))
                node.setScale(1)  # translate a rigid platform; never squash its thickness
            elif event.kind in (EventKind.SWITCH_ACTIVATE, EventKind.SWITCH_DEACTIVATE):
                target = event.kind is EventKind.SWITCH_ACTIVATE
                active = target if u >= .5 else not target
                off, on = self._switches[event.target_id]
                visible(off, not active)
                visible(on, active)
                import math
                off.setZ(-.035*self.pitch*math.sin(math.pi*u))
                on.setZ(-.035*self.pitch*math.sin(math.pi*u))

        if collapse_cell is not None:
            intact, broken = self._fragile[collapse_cell]
            intact.hide()
            broken.hide()
            group, pieces = self._debris[collapse_cell]
            group.show()
            x, y = cell_to_world(*collapse_cell, rows=self.board.rows,
                                 cols=self.board.cols, pitch=self.pitch)
            # Deterministic ballistic paths with different spin and horizontal
            # drift; all pieces start inside the original tile footprint.
            for i, piece in enumerate(pieces):
                dx = (i % 3 - 1)*.32
                dy = (i // 3 - .5)*.48
                t = progress
                piece.setPos(x+self.pitch*(dx+dx*.5*t),
                             y+self.pitch*(dy+dy*.4*t),
                             self.pitch*(-.08-(2.8+i*.16)*t*t))
                piece.setHpr((i-2)*45*t, (i%2*2-1)*110*t, (i-3)*37*t)
                piece.setAlphaScale(1-smoothstep(min(1, max(0,(t-.65)/.35))))

    def release(self):
        if self._disposed:
            return
        if self._leased:
            visible(self.renderer_root, not self._prior_hidden)
        self.animated_root.hide()
        for group,pieces in self._debris.values():
            group.hide()
            for piece in pieces:
                piece.setHpr(0,0,0)
                piece.setScale(1)
                piece.setAlphaScale(1)
        self._leased = False

    def dispose(self):
        if self._disposed:
            return
        self.release()
        self.renderer_root.removeNode()
        self.animated_root.removeNode()
        self.root.removeNode()
        self._fragile.clear()
        self._bridges.clear()
        self._switches.clear()
        self._debris.clear()
        self._tile_variants.clear()
        self._disposed = True
