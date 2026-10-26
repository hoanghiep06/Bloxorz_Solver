"""DTO-only Advanced scene composition; all calls belong on the host main thread."""

from panda3d.core import NodePath, Quat, Vec3

from src.gui.advanced_contracts import (
    AdvancedBoardData, AdvancedBlockMode, AdvancedTileKind as Tile,
    SwitchVisualKind, validate_snapshot,
)
from src.gui.advanced_mesh_factory import (
    make_fragile_mesh, make_bridge_mesh, make_switch_mesh,
    make_split_cube_mesh, make_active_cube_mesh, make_flag_mesh, THEMES,
)
from src.gui.contracts import BasicOrientation
from src.gui.geometry_math import block_pose, cell_to_world, logical_board_bounds
from src.gui.mesh_factory import (
    make_floor_mesh, make_goal_mesh, make_block_mesh,
    make_themed_block_mesh, make_themed_cube_mesh,
)
from src.gui.scene_style import sync_block_theme, sync_tile_theme


class AdvancedSceneRenderer:
    """Own three content children; borrow host roots, never create a window/task.

    No dynamic state is guessed at load time: dynamic and block content remain
    hidden until a complete snapshot arrives. Updates reuse prebuilt mesh nodes.
    Different session IDs are opaque replacements authorized by the caller.
    """

    def __init__(self, static_board_root, dynamic_tile_root, block_root, *, pitch=1.0):
        roots = (static_board_root, dynamic_tile_root, block_root)
        if any(not isinstance(root, NodePath) or root.isEmpty() for root in roots):
            raise ValueError('Expected live host NodePaths.')
        if any(roots[i] == roots[j] for i in range(3) for j in range(i)):
            raise ValueError('Host roots must be distinct.')
        logical_board_bounds(1, 1, pitch=pitch)
        self._roots = roots
        self._pitch = pitch
        self._meshes = {
            'floor': make_floor_mesh(pitch=pitch), 'goal': make_goal_mesh(pitch=pitch),
            'whole': make_block_mesh(pitch=pitch), 'cube': make_split_cube_mesh(pitch=pitch),
            'active': make_active_cube_mesh(pitch=pitch),
            'flag': make_flag_mesh(pitch=pitch),
        }
        # Ô đặc biệt (ô đích, cầu, ô cam vỡ, nút bấm): mỗi theme một bản mesh riêng.
        for theme in THEMES:
            self._meshes[('goal', theme)] = make_goal_mesh(pitch=pitch, theme=theme)
            self._meshes[('bridge', theme)] = make_bridge_mesh(pitch=pitch, theme=theme)
            self._meshes[('intact', theme)] = make_fragile_mesh(pitch=pitch, theme=theme)
            self._meshes[('broken', theme)] = make_fragile_mesh(pitch=pitch, broken=True, theme=theme)
            for kind in SwitchVisualKind:
                for activated in (False, True):
                    self._meshes[((kind, activated), theme)] = make_switch_mesh(
                        kind, activated=activated, pitch=pitch, theme=theme)
        for theme in ('light', 'dark'):
            self._meshes[('whole', theme)] = make_themed_block_mesh(theme, pitch=pitch)
            self._meshes[('cube', theme)] = make_themed_cube_mesh(theme, pitch=pitch)
        self._contents = ()
        self._board_data = self._snapshot = None
        self._fragile = self._bridges = self._switches = {}
        self._whole = None
        self._cubes = self._indicators = ()
        self._cube_slots = {}
        self._flags = {}
        self._actor_visuals_visible = True
        self._disposed = False

    def _require_active(self):
        if self._disposed:
            raise RuntimeError('Renderer is disposed.')
        if any(root.isEmpty() for root in self._roots):
            raise RuntimeError('Host roots were removed before renderer cleanup.')

    def _instance(self, parent, name, mesh_key, *, cell=None, board=None):
        node = parent.attachNewNode(name)
        node.attachNewNode(self._meshes[mesh_key])
        if cell is not None:
            x, y = cell_to_world(*cell, rows=board.rows, cols=board.cols, pitch=self._pitch)
            node.setPos(x, y, 0)
            node.setTag('cell', f'{cell[0]},{cell[1]}')
        return node

    def _themed_instance(self, parent, name, base_key):
        """Một node chứa cả 2 bản mesh theme; scene_style.sync_block_theme bật 1 bản, tắt bản kia."""
        node = parent.attachNewNode(name)
        for theme in ('light', 'dark'):
            holder = node.attachNewNode('BlockTheme-' + theme)
            holder.attachNewNode(self._meshes[(base_key, theme)])
        return node

    def _tile_instance(self, parent, name, key, *, cell, board):
        """Ô đặc biệt chứa cả 2 bản mesh theme; scene_style.sync_tile_theme chọn bản hiển thị."""
        node = parent.attachNewNode(name)
        for theme in THEMES:
            holder = node.attachNewNode('TileTheme-' + theme)
            holder.attachNewNode(self._meshes[(key, theme)])
        x, y = cell_to_world(*cell, rows=board.rows, cols=board.cols, pitch=self._pitch)
        node.setPos(x, y, 0)
        node.setTag('cell', f'{cell[0]},{cell[1]}')
        return node

    def load_board(self, board_data):
        """Build detached content, then replace only owned nodes after validation."""
        self._require_active()
        if type(board_data) is not AdvancedBoardData:
            raise TypeError('board_data must be AdvancedBoardData schema 2.')
        board_data.__post_init__()
        if board_data == self._board_data:
            return
        if self._board_data and board_data.board_revision == self._board_data.board_revision:
            raise ValueError('board_revision reused for different board data.')
        contents = tuple(NodePath(name) for name in (
            'AdvancedStaticContent', 'AdvancedDynamicContent', 'AdvancedBlockContent'))
        static, dynamic, blocks = contents
        fragile, bridges, switches = {}, {}, {}
        try:
            goals = set(board_data.goal_cells)
            for r, row in enumerate(board_data.tiles):
                for c, kind in enumerate(row):
                    cell = (r, c)
                    if kind is Tile.FLOOR:
                        if cell in goals:
                            node = self._tile_instance(static, f'Goal-{r}-{c}', 'goal',
                                                       cell=cell, board=board_data)
                            node.setLightOff(1)        # không bị bóng/ánh sáng làm tối
                            node.setColorScaleOff(1)   # giữ đúng màu gỗ / tuyết, không bị tint
                        else:
                            self._instance(static, f'Floor-{r}-{c}', 'floor',
                                           cell=cell, board=board_data)
                    elif kind is Tile.FRAGILE:
                        fragile[cell] = tuple(self._tile_instance(dynamic, f'Fragile-{key}-{r}-{c}', key,
                            cell=cell, board=board_data) for key in ('intact', 'broken'))
            for bridge in board_data.bridges:
                group = dynamic.attachNewNode('Bridge-' + bridge.bridge_id)
                group.setTag('bridge_id', bridge.bridge_id)
                for cell in bridge.cells:
                    self._tile_instance(group, f'Platform-{cell[0]}-{cell[1]}', 'bridge',
                                        cell=cell, board=board_data)
                bridges[bridge.bridge_id] = group
            for switch in board_data.switches:
                variants = tuple(self._tile_instance(dynamic, f'Switch-{switch.switch_id}-{active}',
                    (switch.kind, active), cell=switch.cell, board=board_data) for active in (False, True))
                for node in variants:
                    node.setTag('switch_id', switch.switch_id)
                switches[switch.switch_id] = variants
            flags = {cell: self._instance(dynamic, f'GoalFlag-{cell[0]}-{cell[1]}', 'flag',
                                          cell=cell, board=board_data)
                     for cell in board_data.goal_cells}
            for flag in flags.values():
                flag.setLightOff(1)        # cờ giữ đúng màu đỏ sáng, không bị tối
                flag.setColorScaleOff(1)   # không bị tint theo theme
            whole = self._themed_instance(blocks, 'WholeBlockVisual', 'whole')
            cubes = tuple(self._themed_instance(blocks, f'SplitCubeSlot-{i}', 'cube') for i in range(2))
            indicators = tuple(self._instance(cube, 'ActiveCubeIndicator', 'active') for cube in cubes)
            for indicator in indicators:
                # Bỏ qua tint của block_root để khung chỉ thị giữ màu xanh lá.
                indicator.setColorScaleOff(1)
            dynamic.hide()
            blocks.hide()
        except BaseException:
            for content in contents:
                content.removeNode()
            raise
        self.clear()
        for content, root in zip(contents, self._roots):
            content.reparentTo(root)
        self._contents = contents
        self._board_data = board_data
        self._fragile, self._bridges, self._switches = fragile, bridges, switches
        self._flags = flags
        self._whole, self._cubes, self._indicators = whole, cubes, indicators
        sync_block_theme(self._roots[2])
        sync_tile_theme(self._roots[1])

    def show_snapshot(self, snapshot):
        """Apply a complete visual state, with validation before scene mutation."""
        self._require_active()
        if self._board_data is None:
            raise RuntimeError('load_board must be called first.')
        validate_snapshot(snapshot, self._board_data)
        if self._snapshot and snapshot.session_id == self._snapshot.session_id:
            if snapshot.state_revision < self._snapshot.state_revision:
                raise ValueError('snapshot.state_revision is stale for this session.')
            if snapshot.state_revision == self._snapshot.state_revision:
                if snapshot != self._snapshot:
                    raise ValueError('state_revision reused for different snapshot data.')
                return
        pose = None
        rotation = Quat()
        positions = {}
        if snapshot.whole_pose is not None:
            pose = block_pose(*snapshot.whole_pose.anchor_cell, snapshot.whole_pose.orientation,
                rows=self._board_data.rows, cols=self._board_data.cols, pitch=self._pitch)
            rotation.setFromAxisAngle(pose.angle_degrees, Vec3(*pose.rotation_axis))
        for cube in snapshot.cubes:
            x, y = cell_to_world(*cube.cell, rows=self._board_data.rows,
                                cols=self._board_data.cols, pitch=self._pitch)
            positions[cube.cube_id] = (x, y, self._pitch / 2)
        # Finish all data/pose work before changing any visibility or transform.
        # Cờ ẩn khi khối đang nằm trên ô đích để cột cờ không xuyên vào khối.
        occupied = {cube.cell for cube in snapshot.cubes}
        if snapshot.whole_pose is not None:
            r, c = snapshot.whole_pose.anchor_cell
            occupied.add((r, c))
            if snapshot.whole_pose.orientation is BasicOrientation.HORIZONTAL:
                occupied.add((r, c + 1))
            elif snapshot.whole_pose.orientation is BasicOrientation.VERTICAL:
                occupied.add((r + 1, c))
        for cell, flag in self._flags.items():
            self._visible(flag, cell not in occupied)
        for cell, (intact, broken) in self._fragile.items():
            is_broken = cell in snapshot.broken_fragile_cells
            self._visible(intact, not is_broken)
            self._visible(broken, is_broken)
        for state in snapshot.bridge_states:
            self._visible(self._bridges[state.bridge_id], state.present)
        for switch_id, (inactive, activated) in self._switches.items():
            is_active = switch_id in snapshot.activated_switch_ids
            self._visible(inactive, not is_active)
            self._visible(activated, is_active)
        is_whole = snapshot.block_mode is AdvancedBlockMode.WHOLE
        self._visible(self._whole, is_whole)
        if pose is not None:
            self._whole.setPos(*pose.center)
            self._whole.setQuat(rotation)
        # Keep matching IDs on their existing slot even if input tuple order changes.
        if not is_whole:
            slots = {key: value for key, value in self._cube_slots.items() if key in positions}
            available = [i for i in range(2) if i not in slots.values()]
            for cube_id in positions:
                if cube_id not in slots:
                    slots[cube_id] = available.pop(0)
            self._cube_slots = slots
            for cube_id, index in slots.items():
                self._cubes[index].setPos(*positions[cube_id])
                self._cubes[index].setTag('cube_id', cube_id)
        for index, (cube, indicator) in enumerate(zip(self._cubes, self._indicators)):
            self._visible(cube, not is_whole)
            self._visible(indicator, not is_whole and snapshot.active_cube_id is not None
                          and self._cube_slots.get(snapshot.active_cube_id) == index)
        self._contents[1].show()
        self._visible(self._contents[2], self._actor_visuals_visible)
        self._snapshot = snapshot

    def set_actor_visuals_visible(self, visible):
        """Presentation lease for an external rig; never change snapshots or tiles.

        The flag persists through show_snapshot/load_board until explicitly released.
        Only this renderer's actor content is touched, including during host cleanup.
        """
        if type(visible) is not bool:
            raise TypeError('visible must be bool.')
        if self._disposed:
            raise RuntimeError('Renderer is disposed.')
        self._actor_visuals_visible = visible
        if self._contents and self._snapshot is not None:
            self._visible(self._contents[2], visible)

    @staticmethod
    def _visible(node, visible):
        node.show() if visible else node.hide()

    def clear(self):
        """Idempotently release content; preserve host/foreign nodes and prototypes."""
        for node in self._contents:
            node.removeNode()
        self._contents = ()
        self._board_data = self._snapshot = self._whole = None
        self._fragile, self._bridges, self._switches = {}, {}, {}
        self._flags = {}
        self._cubes = self._indicators = ()
        self._cube_slots = {}

    def dispose(self):
        """Terminal idempotent cleanup, also safe after host roots are removed."""
        self.clear()
        self._meshes.clear()
        self._disposed = True