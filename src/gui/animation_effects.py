"""Owned actor rig and leased dynamic surface visuals, not a game engine.

SurfaceLayer supplies a dedicated renderer_root to AdvancedSceneRenderer. During
an effect only that borrowed layer is hidden; animated_root owns all replacement
surface instances. Host roots and foreign nodes are never hidden or removed.
"""
from panda3d.core import NodePath, Quat, TransparencyAttrib, GeomVertexReader, GeomVertexRewriter

from src.gui.animation_math import smoothstep
from src.gui.animation_contracts import EventKind
from src.gui.advanced_contracts import AdvancedBoardData, SwitchVisualKind
from src.gui.advanced_mesh_factory import (
    make_active_cube_mesh, make_split_cube_mesh, make_fragile_mesh,
    make_bridge_mesh, make_switch_mesh, FRAGILE,
)
from src.gui.mesh_factory import make_block_mesh


def _marked_cube_mesh(pitch):
    """Tint one local bevel strip, keeping every vertex inside the exact cuboid.

    A raised face decal would protrude below Z=0 when that face rolls downward.
    This fresh factory result belongs only to the rig, never Stage 4 prototypes.
    """
    mesh = make_split_cube_mesh(pitch=pitch)
    for index in range(mesh.getNumGeoms()):
        data = mesh.modifyGeom(index).modifyVertexData()
        normals = GeomVertexReader(data, 'normal')
        colors = GeomVertexRewriter(data, 'color')
        row = 0
        while not normals.isAtEnd():
            normal = normals.getData3f()
            if abs(normal.x) < 1e-6 and normal.y < -.6 and normal.z > .6:
                colors.setRow(row)
                colors.setData4f(*FRAGILE)
            row += 1
    return mesh
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
        self._whole, self._whole_model = self._actor(self.root, 'AnimatedWhole', make_block_mesh(pitch=pitch))
        cube_mesh = _marked_cube_mesh(pitch)
        cubes = [self._actor(self.root, 'AnimatedCube', cube_mesh) for _ in range(2)]
        self._cubes = tuple(node for node, model in cubes)
        self._models = {None: self._whole_model}
        self._cube_models = tuple(model for node, model in cubes)
        self._indicators = tuple(node.attachNewNode(make_active_cube_mesh(pitch=pitch)) for node in self._cubes)
        self.root.hide()

    @staticmethod
    def _actor(parent, name, mesh):
        node = parent.attachNewNode(name)
        model = node.attachNewNode('LocalGeometry')
        model.attachNewNode(mesh)
        node.setTransparency(TransparencyAttrib.MAlpha)
        return node, model

    def apply(self, poses, *, active_weights=None, opacity=None, scales=None):
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
        self.root.show()

    def dispose(self):
        if self._disposed:
            return
        self.root.removeNode()
        self._slots.clear()
        self._models.clear()
        self._whole = self._whole_model = None
        self._cubes = self._cube_models = self._indicators = ()
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
        self._fragile, self._bridges, self._switches = {}, {}, {}
        self._leased = False
        self._prior_hidden = False
        self._disposed = False
        try:
            intact, broken = make_fragile_mesh(pitch=pitch), make_fragile_mesh(pitch=pitch, broken=True)
            platform = make_bridge_mesh(pitch=pitch)
            switches = {(kind, active): make_switch_mesh(kind, activated=active, pitch=pitch)
                        for kind in SwitchVisualKind for active in (False, True)}
            for cell in board_data.fragile_cells:
                self._fragile[cell] = tuple(self._instance(self.animated_root, mesh, cell)
                                            for mesh in (intact, broken))
            for bridge in board_data.bridges:
                group = self.animated_root.attachNewNode('AnimatedBridge-' + bridge.bridge_id)
                for cell in bridge.cells:
                    self._instance(group, platform, cell)
                self._bridges[bridge.bridge_id] = group
            for switch in board_data.switches:
                self._switches[switch.switch_id] = tuple(self._instance(self.animated_root,
                    switches[switch.kind, active], switch.cell) for active in (False, True))
        except BaseException:
            self.dispose()
            raise

    def _instance(self, parent, mesh, cell):
        wrapper = parent.attachNewNode(mesh.getName() + '-Instance')
        wrapper.attachNewNode(mesh)
        x, y = cell_to_world(*cell, rows=self.board.rows, cols=self.board.cols, pitch=self.pitch)
        wrapper.setPos(x, y, 0)
        return wrapper

    def sample(self, before, events, progress):
        if self._disposed:
            raise RuntimeError('Surface layer is disposed.')
        if not self._leased:
            self._prior_hidden = self.renderer_root.isHidden()
            self._leased = True
        self.renderer_root.hide()
        self.animated_root.show()
        for cell, (intact, broken) in self._fragile.items():
            is_broken = cell in before.broken_fragile_cells
            visible(intact, not is_broken)
            visible(broken, is_broken)
            intact.clearColorScale()
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
                visible(intact, u < .12)
                visible(broken, u >= .12)
                intact.setColorScale(1-.18*u, 1-.18*u, 1-.18*u, 1)
                broken.setZ(.25*self.pitch*(1-u))
            elif event.kind in (EventKind.BRIDGE_PRESENT, EventKind.BRIDGE_ABSENT):
                node = self._bridges[event.target_id]
                amount = u if event.kind is EventKind.BRIDGE_PRESENT else 1-u
                visible(node, amount > 0)
                node.setZ(-.65*self.pitch*(1-amount))
                node.setScale(1, 1, max(.02, amount))
            elif event.kind in (EventKind.SWITCH_ACTIVATE, EventKind.SWITCH_DEACTIVATE):
                target = event.kind is EventKind.SWITCH_ACTIVATE
                active = target if u >= .5 else not target
                off, on = self._switches[event.target_id]
                visible(off, not active)
                visible(on, active)
                import math
                off.setZ(-.035*self.pitch*math.sin(math.pi*u))
                on.setZ(-.035*self.pitch*math.sin(math.pi*u))

    def release(self):
        if self._disposed:
            return
        if self._leased:
            visible(self.renderer_root, not self._prior_hidden)
        self.animated_root.hide()
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
        self._disposed = True
