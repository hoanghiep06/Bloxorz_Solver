"""Basic DTO-only scene composition; the caller owns the window and scene roots."""

from panda3d.core import NodePath, Quat, Vec3

from src.gui.contracts import BasicTileKind, GameSnapshot, StaticBoardData
from src.gui.geometry_math import block_pose, cell_to_world, logical_board_bounds
from src.gui.mesh_factory import make_block_mesh, make_floor_mesh, make_goal_mesh


class BasicSceneRenderer:
    """Load static tiles and update one block, without Core, tasks or ShowBase.

    Public operations return None on success and raise before changing the scene
    for invalid data. Roots belong to the host; only children created here are
    removed by clear/dispose. Call all methods on the host's main thread.
    """

    def __init__(self, static_board_root: NodePath, block_root: NodePath, *,
                 pitch: float = 1.0) -> None:
        for name, root in (("static_board_root", static_board_root), ("block_root", block_root)):
            if not isinstance(root, NodePath) or root.isEmpty():
                raise ValueError(f"{name} must be a live host NodePath.")
        if static_board_root == block_root:
            raise ValueError("static_board_root and block_root must be distinct.")
        logical_board_bounds(1, 1, pitch=pitch)  # Validate without graphics resources.
        self._static_root = static_board_root
        self._block_root = block_root
        self._pitch = pitch
        self._floor_mesh = make_floor_mesh(pitch=pitch)
        self._goal_mesh = make_goal_mesh(pitch=pitch)
        self._block_mesh = make_block_mesh(pitch=pitch)
        self._content = None
        self._block = None
        self._board_data = None
        self._snapshot = None
        self._disposed = False

    def _require_active(self) -> None:
        if self._disposed:
            raise RuntimeError("Renderer is disposed.")
        if self._static_root.isEmpty() or self._block_root.isEmpty():
            raise RuntimeError("Host roots were removed before renderer cleanup.")

    def load_board(self, board_data: StaticBoardData) -> None:
        """Replace owned static geometry; identical data is an idempotent no-op.

        Render every declared goal on FLOOR, including multiple goals. Empty
        goal_cells is supported. A goal on VOID is an unsupported visual profile;
        it is not converted into a floor or classified as a gameplay error.
        """
        self._require_active()
        if type(board_data) is not StaticBoardData:
            raise TypeError("board_data must be StaticBoardData.")
        board_data.__post_init__()
        if self._board_data == board_data:
            return
        if self._board_data and self._board_data.board_revision == board_data.board_revision:
            raise ValueError("board_revision reused for different board data.")
        goals = set(board_data.goal_cells)
        for row, col in goals:
            if board_data.tiles[row][col] is BasicTileKind.VOID:
                raise ValueError(f"goal_cells: goal on VOID at {(row, col)} is unsupported for rendering.")
        content = NodePath("BasicBoardContent")
        try:
            for row, tile_row in enumerate(board_data.tiles):
                for col, kind in enumerate(tile_row):
                    if kind is BasicTileKind.VOID:
                        continue
                    is_goal = (row, col) in goals
                    instance = content.attachNewNode(f"{'Goal' if is_goal else 'Floor'}-{row}-{col}")
                    x, y = cell_to_world(row, col, rows=board_data.rows,
                                         cols=board_data.cols, pitch=self._pitch)
                    instance.setPos(x, y, 0)
                    # Instance transforms live on unique parents, never shared mesh nodes.
                    instance.attachNewNode(self._goal_mesh if is_goal else self._floor_mesh)
                    if is_goal:
                        instance.setLightOff(1)        # ô đích không bị bóng làm tối
                        instance.setColorScaleOff(1)   # bỏ qua tint theme
        except Exception:
            content.removeNode()
            raise
        self.clear()
        content.reparentTo(self._static_root)
        self._content = content
        self._board_data = board_data

    def show_snapshot(self, snapshot: GameSnapshot) -> None:
        """Apply one canonical pose without rebuilding tiles or creating a new block.

        Same-session revisions may repeat only with identical data and may not
        decrease. Session strings are opaque; caller authorizes replacement.
        No game rules, movement or session allocation occur here.
        """
        self._require_active()
        if self._board_data is None:
            raise RuntimeError("load_board must be called before show_snapshot.")
        if type(snapshot) is not GameSnapshot:
            raise TypeError("snapshot must be GameSnapshot.")
        snapshot.__post_init__()
        if snapshot.board_revision != self._board_data.board_revision:
            raise ValueError("snapshot.board_revision does not match the loaded board.")
        pose = block_pose(*snapshot.anchor_cell, snapshot.orientation,
                          rows=self._board_data.rows, cols=self._board_data.cols, pitch=self._pitch)
        if self._snapshot and snapshot.session_id == self._snapshot.session_id:
            if snapshot.state_revision < self._snapshot.state_revision:
                raise ValueError("snapshot.state_revision is stale for this session.")
            if snapshot.state_revision == self._snapshot.state_revision:
                if snapshot != self._snapshot:
                    raise ValueError("snapshot.state_revision reused for different snapshot data.")
                return
        rotation = Quat()
        rotation.setFromAxisAngle(pose.angle_degrees, Vec3(*pose.rotation_axis))
        if self._block is None:
            self._block = self._block_root.attachNewNode("MainBlockVisual")
            self._block.attachNewNode(self._block_mesh)
        self._block.setPos(*pose.center)
        self._block.setQuat(rotation)
        self._snapshot = snapshot

    def clear(self) -> None:
        """Remove only owned content and identity; keep meshes for subsequent loads."""
        for node in (self._content, self._block):
            if node is not None:
                node.removeNode()
        self._content = None
        self._block = None
        self._board_data = None
        self._snapshot = None

    def dispose(self) -> None:
        """Idempotently remove owned content and release mesh references, never host roots."""
        self.clear()
        self._floor_mesh = self._goal_mesh = self._block_mesh = None
        self._disposed = True