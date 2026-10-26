"""Read actual vertices and primitive indices without creating a window."""
import importlib.util
import math
import unittest

HAS_PANDA = importlib.util.find_spec('panda3d') is not None
if HAS_PANDA:
    from panda3d.core import GeomVertexReader, NodePath, Vec3
    from src.gui.advanced_mesh_factory import (
        make_fragile_mesh, make_bridge_mesh, make_switch_mesh,
        make_split_cube_mesh, make_active_cube_mesh,
    )
    from src.gui.advanced_contracts import SwitchVisualKind
    from src.gui.mesh_factory import make_beveled_box_mesh


def vertices(node, column='vertex'):
    result = []
    for geom in node.getGeoms():
        reader = GeomVertexReader(geom.getVertexData(), column)
        while not reader.isAtEnd():
            result.append(tuple(reader.getData4f() if column == 'color' else reader.getData3f()))
    return result


def bounds(node):
    points = vertices(node)
    return tuple(min(p[i] for p in points) for i in range(3)), tuple(max(p[i] for p in points) for i in range(3))


@unittest.skipUnless(HAS_PANDA, 'Panda3D not installed')
class AdvancedGeometryTests(unittest.TestCase):
    def assets(self, pitch=1):
        return [make_fragile_mesh(pitch=pitch), make_fragile_mesh(pitch=pitch, broken=True),
                make_bridge_mesh(pitch=pitch), make_split_cube_mesh(pitch=pitch),
                make_active_cube_mesh(pitch=pitch),
                *[make_switch_mesh(kind, activated=active, pitch=pitch)
                  for kind in SwitchVisualKind for active in (False, True)]]

    def test_finite_vertices_unit_normals_and_outward_triangle_winding(self):
        for node in self.assets():
            with self.subTest(asset=node.getName()):
                for geom in node.getGeoms():
                    data = geom.getVertexData()
                    vp, vn = GeomVertexReader(data, 'vertex'), GeomVertexReader(data, 'normal')
                    points, normals = [], []
                    while not vp.isAtEnd():
                        points.append(Vec3(vp.getData3f()))
                        normals.append(Vec3(vn.getData3f()))
                    for p, n in zip(points, normals):
                        self.assertTrue(all(math.isfinite(v) for v in (*p, *n)))
                        self.assertAlmostEqual(n.length(), 1, places=5)
                    for primitive in geom.getPrimitives():
                        triangles = primitive.decompose()
                        for i in range(triangles.getNumPrimitives()):
                            indices = [triangles.getVertex(j) for j in range(
                                triangles.getPrimitiveStart(i), triangles.getPrimitiveEnd(i))]
                            self.assertEqual(len(indices), 3)
                            a, b, c = (points[index] for index in indices)
                            cross = (b-a).cross(c-a)
                            self.assertGreater(cross.lengthSquared(), 1e-14)
                            self.assertGreater(cross.dot(normals[indices[0]]), 0)
                self.assertFalse(NodePath(node).getTwoSided())

    def test_pitch_scales_every_asset(self):
        for one, scaled in zip(self.assets(), self.assets(2.5)):
            a, b = vertices(one), vertices(scaled)
            self.assertEqual(len(a), len(b))
            for p, q in zip(a, b):
                for x, y in zip(p, q):
                    self.assertAlmostEqual(x * 2.5, y, places=5)

    def test_intact_fragile_has_full_support_and_raised_cracks(self):
        mesh = make_fragile_mesh()
        low, high = bounds(mesh)
        self.assertAlmostEqual(low[2], -.18, places=5)
        self.assertAlmostEqual(high[0] - low[0], .96, places=5)
        surface = mesh.getGeom(0)
        reader = GeomVertexReader(surface.getVertexData(), 'vertex')
        z = []
        while not reader.isAtEnd():
            z.append(reader.getData3f().z)
        self.assertAlmostEqual(max(z), 0, places=6)
        self.assertGreater(high[2], .009)
        self.assertAlmostEqual(high[2], .014, places=6)
        self.assertGreater(min(p[2] for p in vertices(mesh)[surface.getVertexData().getNumRows():]), .001)

    def test_broken_fragile_has_only_small_debris_below_support(self):
        mesh = make_fragile_mesh(broken=True)
        self.assertEqual(mesh.getNumGeoms(), 3)
        self.assertLess(bounds(mesh)[1][2], -.10)
        for geom in mesh.getGeoms():
            reader = GeomVertexReader(geom.getVertexData(), 'vertex')
            xs = []
            while not reader.isAtEnd():
                xs.append(reader.getData3f().x)
            self.assertLess(max(xs) - min(xs), .25)

    def test_bridge_has_real_volume_and_distinct_colors(self):
        low, high = bounds(make_bridge_mesh())
        self.assertAlmostEqual(low[2], -.18, places=5)
        self.assertGreater(high[2], 0)
        self.assertGreater(len(set(vertices(make_bridge_mesh(), 'color'))), 2)
        self.assertNotEqual(set(vertices(make_bridge_mesh(), 'color')),
                            set(vertices(make_fragile_mesh(), 'color')))

    def test_three_switch_shapes_and_activation_are_distinct(self):
        shapes = []
        for kind in SwitchVisualKind:
            off, on = make_switch_mesh(kind), make_switch_mesh(kind, activated=True)
            self.assertEqual(vertices(off), vertices(on))
            self.assertNotEqual(vertices(off, 'color'), vertices(on, 'color'))
            self.assertAlmostEqual(bounds(off)[0][2],
                                   .005 if kind is SwitchVisualKind.SOFT else 0, places=6)
            shapes.append(tuple(vertices(off)))
        self.assertEqual(len(set(shapes)), 3)

    def test_cube_nominal_dimensions_and_placed_bottom(self):
        node = NodePath(make_split_cube_mesh())
        low, high = bounds(node.node())
        for i in range(3):
            self.assertAlmostEqual(high[i] - low[i], 1, places=6)
        node.setZ(.5)
        self.assertAlmostEqual(node.getTightBounds()[0].z, 0, places=6)
        self.assertAlmostEqual(node.getTightBounds()[1].z, 1, places=6)

    def test_active_brackets_inside_footprint_above_top(self):
        low, high = bounds(make_active_cube_mesh())
        self.assertTrue(all(-.5 < low[i] < high[i] < .5 for i in (0, 1)))
        self.assertGreater(low[2], .50)
        self.assertLessEqual(high[2], .55)

    def test_invalid_pitch_kind_and_boolean_inputs(self):
        for pitch in (0, -1, True, float('nan'), float('inf')):
            for factory in (make_fragile_mesh, make_bridge_mesh, make_split_cube_mesh, make_active_cube_mesh):
                with self.assertRaises(ValueError):
                    factory(pitch=pitch)
        with self.assertRaises(TypeError):
            make_switch_mesh('SOFT')
        with self.assertRaises(TypeError):
            make_switch_mesh(SwitchVisualKind.SOFT, activated=1)
        with self.assertRaises(TypeError):
            make_fragile_mesh(broken=1)

    def test_shared_box_extension_validates_geometry_parameters(self):
        args = dict(name='test', dimensions=(1, 1, 1), bevel=.02,
                    top_color=(1, 1, 1, 1), side_color=(.5, .5, .5, 1), edge_color=(0, 0, 0, 1))
        for fields in ({'dimensions': (1, 0, 1)}, {'dimensions': [1, 1, 1]}, {'bevel': .5},
                       {'top_color': (1, 2, 1, 1)}, {'side_color': (float('nan'), 0, 0, 1)}, {'name': ''}):
            with self.assertRaises(ValueError):
                make_beveled_box_mesh(**{**args, **fields})
