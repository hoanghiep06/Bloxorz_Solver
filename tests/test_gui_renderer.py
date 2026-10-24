"""Gates B/C: real Panda3D geometry and scene graphs without creating ShowBase."""

from collections import Counter
import importlib.util
import math
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


HAS_PANDA = importlib.util.find_spec("panda3d") is not None
if HAS_PANDA:
    from panda3d.core import GeomVertexReader, NodePath, Vec3
    from src.gui.mesh_factory import make_block_mesh, make_floor_mesh, make_goal_mesh
    from src.gui.renderer import BasicSceneRenderer


def mesh_data(node):
    geom = node.getGeom(0)
    data = geom.getVertexData()
    vertices, normals = [], []
    position = GeomVertexReader(data, "vertex")
    normal = GeomVertexReader(data, "normal")
    for _ in range(data.getNumRows()):
        vertices.append(Vec3(position.getData3f()))
        normals.append(Vec3(normal.getData3f()))
    primitive = geom.getPrimitive(0).decompose()
    triangles = []
    for i in range(primitive.getNumPrimitives()):
        start, end = primitive.getPrimitiveStart(i), primitive.getPrimitiveEnd(i)
        triangles.append(tuple(primitive.getVertex(j) for j in range(start, end)))
    return vertices, normals, triangles


@unittest.skipUnless(HAS_PANDA, "Panda3D mesh tests require the GUI .venv; no window is opened.")
class MeshTests(unittest.TestCase):
    def assert_mesh_integrity(self, node, *, convex=False):
        vertices, normals, triangles = mesh_data(node)
        edges = Counter()
        faces = set()
        for triangle in triangles:
            self.assertEqual(len(triangle), 3)
            self.assertTrue(all(0 <= i < len(vertices) for i in triangle))
            a, b, c = [vertices[i] for i in triangle]
            cross = (b - a).cross(c - a)
            self.assertGreater(cross.length(), 1e-7)
            normal = normals[triangle[0]]
            self.assertAlmostEqual(normal.length(), 1, places=6)
            self.assertGreater(cross.normalized().dot(normal), 0.99999)
            if convex:
                self.assertGreater(((a + b + c) / 3).dot(normal), 0)
            keys = [tuple(round(v, 6) for v in vertices[i]) for i in triangle]
            face_key = tuple(sorted(keys))
            self.assertNotIn(face_key, faces, "duplicate coincident triangle")
            faces.add(face_key)
            for i in range(3):
                edges[tuple(sorted((keys[i], keys[(i + 1) % 3])))] += 1
        self.assertTrue(all(count == 2 for count in edges.values()), "mesh must be watertight")
        self.assertTrue(all(math.isfinite(v) for p in vertices + normals for v in p))

    def test_t16_floor_has_vertices_and_triangles(self):
        vertices, _, triangles = mesh_data(make_floor_mesh())
        self.assertGreater(len(vertices), 0)
        self.assertEqual(len(triangles), 44)

    def test_t17_floor_top_is_zero(self):
        vertices, normals, _ = mesh_data(make_floor_mesh())
        self.assertAlmostEqual(max(v.z for v in vertices), 0, places=6)
        self.assertTrue(any(abs(v.z) < 1e-6 and n.z > 0.99 for v, n in zip(vertices, normals)))

    def test_t18_floor_bottom_is_minus_018(self):
        vertices, _, _ = mesh_data(make_floor_mesh())
        self.assertAlmostEqual(min(v.z for v in vertices), -0.18, places=6)

    def test_t19_floor_dimensions_and_seam(self):
        low, high = NodePath(make_floor_mesh()).getTightBounds()
        self.assertAlmostEqual(high.x - low.x, 0.96, places=6)
        self.assertAlmostEqual(high.y - low.y, 0.96, places=6)
        self.assertAlmostEqual(1 - (high.x - low.x), 0.04, places=6)

    def test_t20_floor_normals_winding_and_watertight_bevel(self):
        # Center the baked floor again for the convex outward-normal check.
        from panda3d.core import Mat4
        node = make_floor_mesh()
        node.modifyGeom(0).transformVertices(Mat4.translateMat(0, 0, 0.09))
        self.assert_mesh_integrity(node, convex=True)

    def test_t22_goal_has_rim_inner_walls_and_depth(self):
        vertices, normals, _ = mesh_data(make_goal_mesh())
        self.assertTrue(any(abs(v.z + 0.14) < 1e-6 and n.z > 0.99
                            for v, n in zip(vertices, normals)))
        self.assertTrue(any(abs(abs(v.x) - 0.38) < 1e-6 and abs(n.x) > 0.99
                            for v, n in zip(vertices, normals)))
        self.assertAlmostEqual(max(v.z for v in vertices), 0, places=6)
        self.assert_mesh_integrity(make_goal_mesh())
        for normal in normals:
            self.assertAlmostEqual(normal.length(), 1, places=6)
        vertices, normals, triangles = mesh_data(make_goal_mesh())
        for triangle in triangles:
            center = sum((vertices[i] for i in triangle), vertices[triangle[0]] * 0) / 3
            normal = normals[triangle[0]]
            if abs(center.z) < 1e-6 or abs(center.z + 0.14) < 1e-6:
                self.assertGreater(normal.z, 0.99)
            elif abs(center.z + 0.18) < 1e-6:
                self.assertLess(normal.z, -0.99)
            else:
                for axis in (0, 1):
                    if abs(abs(center[axis]) - 0.48) < 1e-6:
                        self.assertGreater(normal[axis] * center[axis], 0)
                    elif abs(abs(center[axis]) - 0.38) < 1e-6:
                        self.assertLess(normal[axis] * center[axis], 0)

    def test_t23_goal_has_no_top_surface_covering_the_aperture(self):
        vertices, _, triangles = mesh_data(make_goal_mesh())
        area = 0
        for indices in triangles:
            points = [vertices[i] for i in indices]
            if all(abs(v.z) < 1e-6 for v in points):
                a, b, c = points
                area += (b - a).cross(c - a).length() / 2
                # No triangle covers even the central aperture test point.
                crosses = [(points[(i + 1) % 3] - points[i]).cross(-points[i]).z
                           for i in range(3)]
                self.assertFalse(all(v >= -1e-7 for v in crosses))
        self.assertAlmostEqual(area, 0.96 ** 2 - 0.76 ** 2, places=6)

    def test_t25_block_nominal_dimensions_and_center(self):
        low, high = NodePath(make_block_mesh()).getTightBounds()
        self.assertEqual(tuple(low), (-0.5, -0.5, -1.0))
        self.assertEqual(tuple(high), (0.5, 0.5, 1.0))

    def test_t26_block_normals_winding_and_flush_detail_are_valid(self):
        self.assert_mesh_integrity(make_block_mesh(), convex=True)

    def test_meshes_scale_without_scaling_a_pose_node(self):
        for factory in (make_floor_mesh, make_goal_mesh, make_block_mesh):
            unit = NodePath(factory()).getTightBounds()
            scaled = NodePath(factory(pitch=2)).getTightBounds()
            for expected, actual in zip(unit, scaled):
                for a, b in zip(expected, actual):
                    self.assertAlmostEqual(2 * a, b, places=6)


@unittest.skipUnless(HAS_PANDA, "Panda3D scene tests require the GUI .venv; no window is opened.")
class RendererTests(unittest.TestCase):
    def setUp(self):
        from src.core.board import Board
        from src.gui.render_adapter import build_board_data, build_game_snapshot
        self.host = NodePath("SceneRoot")
        self.static = self.host.attachNewNode("StaticBoardRoot")
        self.dynamic = self.host.attachNewNode("DynamicTileRoot")
        self.block_root = self.host.attachNewNode("BlockRoot")
        self.effects = self.host.attachNewNode("EffectsRoot")
        board = Board(str(Path(__file__).resolve().parents[1] / "levels/level_01.json"))
        self.data = build_board_data(board, level_id="level_01")
        self.initial = build_game_snapshot(board.get_initial_state(), board_data=self.data,
                                            session_id="preview", state_revision=0)
        self.renderer = BasicSceneRenderer(self.static, self.block_root)
        self.addCleanup(self.host.removeNode)
        self.addCleanup(self.renderer.dispose)

    def snapshot(self, orientation, revision=0):
        from src.gui.contracts import BasicOrientation as O
        row, col = self.initial.anchor_cell
        cells = {O.STANDING: ((row, col),),
                 O.HORIZONTAL: ((row, col), (row, col + 1)),
                 O.VERTICAL: ((row, col), (row + 1, col))}[orientation]
        return replace(self.initial, orientation=orientation,
                       occupied_cells=cells, state_revision=revision)

    def block(self):
        return self.block_root.find("MainBlockVisual")

    def test_t21_void_has_no_node_or_floor_geometry(self):
        self.renderer.load_board(self.data)
        content = self.static.find("BasicBoardContent")
        self.assertEqual(content.getNumChildren(), 20)
        self.assertEqual(content.findAllMatches("Floor-*").getNumPaths(), 19)
        self.assertTrue(content.find("Floor-0-3").isEmpty())
        self.assertEqual(content.findAllMatches("**/+GeomNode").getNumPaths(), 20)

    def test_t24_goal_uses_authoritative_coordinates(self):
        data = replace(self.data, goal_cells=((2, 6),), board_revision="goal-moved")
        self.renderer.load_board(data)
        goal = self.static.find("**/Goal-2-6")
        self.assertEqual(tuple(goal.getPos(self.host)), (3, -0.5, 0))
        self.assertTrue(self.static.find("**/Goal-1-6").isEmpty())
        self.assertFalse(self.static.find("**/Floor-1-6").isEmpty())
        self.assertTrue(self.static.find("**/Floor-2-6").isEmpty())

    def test_t27_real_vertex_transforms_have_correct_aabb_for_all_poses(self):
        from src.gui.contracts import BasicOrientation as O
        self.renderer.load_board(self.data)
        for revision, (orientation, center, size) in enumerate((
            (O.STANDING, (-2, 0.5, 1), (1, 1, 2)),
            (O.HORIZONTAL, (-1.5, 0.5, 0.5), (2, 1, 1)),
            (O.VERTICAL, (-2, 0, 0.5), (1, 2, 1)),
        )):
            with self.subTest(orientation=orientation):
                self.renderer.show_snapshot(self.snapshot(orientation, revision))
                low, high = self.block().getTightBounds(self.host)
                for axis in range(3):
                    self.assertAlmostEqual(low[axis], center[axis] - size[axis] / 2, places=5)
                    self.assertAlmostEqual(high[axis], center[axis] + size[axis] / 2, places=5)
                self.assertAlmostEqual(low.z, 0, places=6)
                self.assertEqual(tuple(self.block().getScale()), (1, 1, 1))

    def test_t28_repeated_absolute_pose_updates_do_not_drift(self):
        from src.gui.contracts import BasicOrientation as O
        self.renderer.load_board(self.data)
        for revision in range(300):
            self.renderer.show_snapshot(self.snapshot(list(O)[revision % 3], revision))
        self.renderer.show_snapshot(self.snapshot(O.STANDING, 300))
        self.assertEqual(tuple(self.block().getPos()), (-2, 0.5, 1))
        rotation = self.block().getQuat()
        self.assertAlmostEqual(rotation.getR(), 1, places=6)
        for component in (rotation.getI(), rotation.getJ(), rotation.getK()):
            self.assertAlmostEqual(component, 0, places=6)
        low, high = self.block().getTightBounds(self.host)
        self.assertAlmostEqual(low.z, 0, places=6)
        self.assertAlmostEqual(high.z, 2, places=6)

    def test_t29_renderer_accepts_real_static_board_dto(self):
        self.renderer.load_board(self.data)
        self.assertEqual(self.static.getNumChildren(), 1)
        self.assertEqual(self.static.find("BasicBoardContent").getNumChildren(), 20)

    def test_t30_import_does_not_depend_on_core(self):
        code = """
import importlib.abc
import sys
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        forbidden = ('src.core', 'src.solvers', 'src.gui.app', 'src.gui.controller',
                     'src.gui.render_adapter', 'direct.showbase', 'pygame')
        if any(fullname == n or fullname.startswith(n + '.') for n in forbidden):
            raise AssertionError(fullname)
sys.meta_path.insert(0, Guard())
from panda3d.core import GraphicsEngine, NodePath
from src.gui.renderer import BasicSceneRenderer
root = NodePath('host')
renderer = BasicSceneRenderer(root.attachNewNode('static'), root.attachNewNode('block'))
renderer.dispose()
assert GraphicsEngine.getGlobalPtr().getNumWindows() == 0
"""
        result = subprocess.run([sys.executable, '-B', '-c', code],
                                cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_t31_renderer_constructs_no_showbase_or_graphics_window(self):
        from panda3d.core import GraphicsEngine
        import builtins
        self.renderer.load_board(self.data)
        self.renderer.show_snapshot(self.initial)
        self.assertEqual(GraphicsEngine.getGlobalPtr().getNumWindows(), 0)
        self.assertFalse(hasattr(builtins, "base"))

    def test_t32_renderer_never_calls_gameplay_apis(self):
        from src.core.board import Board
        with patch.object(Board, 'transition', side_effect=AssertionError('transition')), \
             patch.object(Board, 'is_goal', side_effect=AssertionError('is_goal')), \
             patch.object(Board, 'is_valid_state', side_effect=AssertionError('support')):
            self.renderer.load_board(self.data)
            self.renderer.show_snapshot(self.initial)

    def test_t33_load_board_builds_static_geometry_only(self):
        self.renderer.load_board(self.data)
        for root in (self.block_root, self.dynamic, self.effects):
            self.assertEqual(root.getNumChildren(), 0)

    def test_t34_snapshot_updates_one_block_pose(self):
        self.renderer.load_board(self.data)
        self.renderer.show_snapshot(self.initial)
        self.assertEqual(self.block_root.getNumChildren(), 1)
        self.assertEqual(self.block().getNumChildren(), 1)
        self.assertEqual(tuple(self.block().getPos()), (-2, 0.5, 1))

    def test_t35_snapshot_reuses_static_and_block_nodes_and_mesh_prototype(self):
        from src.gui.contracts import BasicOrientation as O
        self.renderer.load_board(self.data)
        content = self.static.find("BasicBoardContent").node()
        floors = self.static.findAllMatches("**/FloorMesh")
        self.assertTrue(all(floor.node() == floors[0].node() for floor in floors))
        # Shared mesh stays at local identity; each unique parent carries position.
        self.assertEqual(tuple(floors[0].getPos()), (0, 0, 0))
        self.renderer.show_snapshot(self.initial)
        block = self.block().node()
        self.renderer.show_snapshot(self.snapshot(O.HORIZONTAL, 1))
        self.assertEqual(self.static.find("BasicBoardContent").node(), content)
        self.assertEqual(self.block().node(), block)

    def test_t36_revision_mismatch_preserves_existing_scene(self):
        self.renderer.load_board(self.data)
        self.renderer.show_snapshot(self.initial)
        position = self.block().getPos()
        with self.assertRaisesRegex(ValueError, 'board_revision'):
            self.renderer.show_snapshot(replace(self.initial, board_revision='wrong'))
        self.assertEqual(self.block().getPos(), position)

    def test_t37_repeated_load_and_update_keep_node_counts_stable(self):
        self.renderer.load_board(self.data)
        self.renderer.show_snapshot(self.initial)
        count = self.host.findAllMatches("**").getNumPaths()
        for _ in range(50):
            self.renderer.load_board(self.data)
            self.renderer.show_snapshot(self.initial)
            self.assertEqual(self.host.findAllMatches("**").getNumPaths(), count)

    def test_t38_replacing_board_removes_old_owned_geometry_and_block(self):
        from src.gui.contracts import BasicTileKind, StaticBoardData
        self.renderer.load_board(self.data)
        self.renderer.show_snapshot(self.initial)
        data = StaticBoardData(1, 'single', 'new', 1, 1, ((BasicTileKind.FLOOR,),), ())
        for revision in range(20):
            self.renderer.load_board(replace(data, board_revision=f'new-{revision}'))
            self.assertEqual(self.static.getNumChildren(), 1)
            self.assertEqual(self.static.find('BasicBoardContent').getNumChildren(), 1)
            self.assertEqual(self.block_root.getNumChildren(), 0)
            self.assertTrue(self.static.find('**/Goal-1-6').isEmpty())

    def test_t39_clear_and_dispose_preserve_host_roots_and_foreign_children(self):
        foreign_static = self.static.attachNewNode('ForeignStatic')
        foreign_block = self.block_root.attachNewNode('ForeignBlock')
        self.renderer.load_board(self.data)
        self.renderer.show_snapshot(self.initial)
        self.renderer.clear()
        self.assertEqual(self.static.getNumChildren(), 1)
        self.assertEqual(self.block_root.getNumChildren(), 1)
        self.assertEqual(foreign_static.getParent(), self.static)
        self.assertEqual(foreign_block.getParent(), self.block_root)
        self.renderer.load_board(self.data)
        self.renderer.dispose()
        for root in (self.static, self.block_root, self.dynamic, self.effects):
            self.assertFalse(root.isEmpty())
            self.assertEqual(root.getParent(), self.host)

    def test_t40_dispose_is_idempotent_and_later_commands_fail(self):
        self.renderer.load_board(self.data)
        self.renderer.dispose()
        self.renderer.dispose()
        with self.assertRaisesRegex(RuntimeError, 'disposed'):
            self.renderer.load_board(self.data)
        with self.assertRaisesRegex(RuntimeError, 'disposed'):
            self.renderer.show_snapshot(self.initial)

    def test_t41_unsupported_mode_orientation_and_schema_never_default(self):
        self.renderer.load_board(self.data)
        self.renderer.show_snapshot(self.initial)
        for field, value in (('orientation', 'STANDING'), ('block_mode', 'SPLIT'),
                             ('schema_version', 2)):
            bad = replace(self.initial)
            object.__setattr__(bad, field, value)  # Simulate corrupted external input.
            with self.subTest(field=field):
                with self.assertRaisesRegex((TypeError, ValueError), field):
                    self.renderer.show_snapshot(bad)
                self.assertEqual(tuple(self.block().getPos()), (-2, 0.5, 1))

    def test_empty_multiple_and_void_goal_profiles_are_explicit(self):
        for goals in ((), ((1, 6), (2, 6))):
            data = replace(self.data, goal_cells=goals, board_revision=repr(goals))
            self.renderer.load_board(data)
            self.assertEqual(self.static.findAllMatches('**/Goal-*').getNumPaths(), len(goals))
        content = self.static.find('BasicBoardContent').node()
        unsupported = replace(self.data, goal_cells=((0, 3),), board_revision='void-goal')
        with self.assertRaisesRegex(ValueError, 'goal on VOID'):
            self.renderer.load_board(unsupported)
        self.assertEqual(self.static.find('BasicBoardContent').node(), content)

    def test_snapshot_bounds_and_stale_or_conflicting_revisions(self):
        from src.gui.contracts import BasicOrientation as O
        with self.assertRaisesRegex(RuntimeError, 'load_board'):
            self.renderer.show_snapshot(self.initial)
        self.renderer.load_board(self.data)
        self.renderer.show_snapshot(replace(self.initial, state_revision=2))
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.renderer.show_snapshot(self.initial)
        with self.assertRaisesRegex(ValueError, 'reused'):
            self.renderer.show_snapshot(self.snapshot(O.HORIZONTAL, 2))
        outside = replace(self.initial, anchor_cell=(99, 99), occupied_cells=((99, 99),),
                          state_revision=3)
        with self.assertRaisesRegex(ValueError, 'bounds'):
            self.renderer.show_snapshot(outside)
        self.renderer.show_snapshot(replace(self.initial, session_id='new-session'))
        self.assertEqual(tuple(self.block().getPos()), (-2, 0.5, 1))

    def test_failed_board_build_and_conflicting_revision_leave_scene_unchanged(self):
        self.renderer.load_board(self.data)
        self.renderer.show_snapshot(self.initial)
        original = self.static.find('BasicBoardContent').node()
        with self.assertRaisesRegex(ValueError, 'board_revision'):
            self.renderer.load_board(replace(self.data, level_id='different'))
        with patch('src.gui.renderer.cell_to_world', side_effect=RuntimeError('build failed')):
            with self.assertRaisesRegex(RuntimeError, 'build failed'):
                self.renderer.load_board(replace(self.data, board_revision='next'))
        self.assertEqual(self.static.find('BasicBoardContent').node(), original)
        self.assertEqual(self.block_root.getNumChildren(), 1)

    def test_t44_preview_import_adds_no_pygame_or_window(self):
        code = """
import sys
import builtins
from panda3d.core import GraphicsEngine
from src.gui import board_preview
assert GraphicsEngine.getGlobalPtr().getNumWindows() == 0
assert not hasattr(builtins, 'base')
assert not any(n == 'pygame' or n.startswith('pygame.') for n in sys.modules)
"""
        result = subprocess.run([sys.executable, '-B', '-c', code],
                                cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_preview_main_disposes_renderer_and_host_when_loop_raises(self):
        from src.gui.board_preview import main
        from unittest.mock import Mock
        app, renderer = Mock(), Mock()
        app.run.side_effect = RuntimeError('loop failed')
        with patch('src.gui.board_preview.create_preview', return_value=(app, renderer)) as create:
            with self.assertRaisesRegex(RuntimeError, 'loop failed'):
                main(['--pose', 'HORIZONTAL'])
        create.assert_called_once()
        app.run.assert_called_once_with()
        renderer.dispose.assert_called_once_with()
        app.destroy.assert_called_once_with()

    def test_invalid_preview_input_does_not_open_a_host(self):
        from src.gui.board_preview import create_preview
        with patch('src.gui.board_preview.BloxorzPreviewApp') as app:
            with self.assertRaisesRegex(ValueError, 'pose'):
                create_preview(pose='STANDING')
            with self.assertRaises(FileNotFoundError):
                create_preview(Path(__file__).resolve().parent / 'nonexistent-level.json')
            app.assert_not_called()


if __name__ == '__main__':
    unittest.main()
