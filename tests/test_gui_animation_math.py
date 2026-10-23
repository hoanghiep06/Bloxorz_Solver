"""Pure rolling mathematics plus an explicit Panda quaternion convention check."""
from dataclasses import replace
import importlib.util
import math
import unittest
from src.gui.animation_math import *
from src.gui.animation_contracts import as_visual_board
from src.gui.animation_fixtures import get_roll_fixture, get_animation_fixture
from src.gui.contracts import BasicOrientation


class RollingMathTests(unittest.TestCase):
    def cases(self):
        for orientation in BasicOrientation:
            for direction in RollDirection:
                f = get_roll_fixture(orientation, direction)
                board = as_visual_board(f.board)
                start = canonical_poses(f.initial, board)[None]
                target = canonical_poses(f.requests[0].after_snapshot, board)[None]
                yield orientation, direction, RollPlan(start, direction), target

    def test_all_twelve_orientation_direction_endpoints(self):
        for orientation, direction, plan, target in self.cases():
            with self.subTest(orientation=orientation, direction=direction):
                plan.validate_target(target)
                for a, b in zip(plan.sample(1).center, target.center):
                    self.assertAlmostEqual(a, b, places=9)
                for a, b in zip(plan.sample(1).extents, target.extents):
                    self.assertAlmostEqual(a, b, places=9)

    def test_numeric_standing_right_example(self):
        p = RollPlan(VisualPose((0, 0, 1), (1, 0, 0, 0), (1, 1, 2)), RollDirection.RIGHT)
        self.assertEqual(p.pivot, (.5, 0, 0))
        self.assertEqual(p.axis, (0, 1, 0))
        for x, y in zip(p.sample(1).center, (1.5, 0, .5)):
            self.assertAlmostEqual(x, y)

    def test_numeric_horizontal_end_and_sideways(self):
        pose = VisualPose((0, 0, .5), axis_angle((0, 1, 0), math.pi/2), (1, 1, 2))
        for direction, target in ((RollDirection.RIGHT, (1.5, 0, 1)), (RollDirection.UP, (0, 1, .5))):
            p = RollPlan(pose, direction)
            for x, y in zip(p.sample(1).center, target):
                self.assertAlmostEqual(x, y)

    def test_keyframes_contact_edge_and_no_floor_penetration(self):
        for _, _, plan, _ in self.cases():
            inverse = (plan.start.quaternion[0], *(-v for v in plan.start.quaternion[1:]))
            local_contact = rotate(inverse, sub(plan.pivot, plan.start.center))
            for t in (0, .25, .5, .75, 1):
                pose = plan.sample(t)
                contact = add(pose.center, rotate(pose.quaternion, local_contact))
                for a, b in zip(contact, plan.pivot):
                    self.assertAlmostEqual(a, b, places=8)
                self.assertGreaterEqual(min(p[2] for p in pose.corners()), -1e-8)
                self.assertAlmostEqual(sum(v*v for v in pose.quaternion), 1, places=10)

    def test_midpoint_center_follows_arc_not_straight_line(self):
        plan = next(self.cases())[2]
        linear = lerp(plan.start.center, plan.sample(1).center, .5)
        self.assertGreater(math.dist(linear, plan.sample(.5).center), .1)
        self.assertGreater(plan.sample(.5).extents[2], .9)

    def test_sampling_does_not_accumulate_transforms(self):
        plan = next(self.cases())[2]
        expected = plan.sample(.5)
        for t in (.9, .1, 1, 0, .2, .7):
            plan.sample(t)
        self.assertEqual(plan.sample(.5), expected)

    def test_easing_monotonic_endpoints_without_overshoot(self):
        values = [smoothstep(i/100) for i in range(101)]
        self.assertEqual((values[0], values[-1]), (0, 1))
        self.assertEqual(values, sorted(values))
        self.assertTrue(all(0 <= x <= 1 for x in values))

    def test_invalid_math_inputs_rejected(self):
        for value in (-1, float('nan'), float('inf'), True, 1.01):
            with self.assertRaises(ValueError):
                smoothstep(value)
        with self.assertRaises(ValueError):
            VisualPose((0, 0, 1), (2, 0, 0, 0), (1, 1, 2))
        with self.assertRaises(ValueError):
            normalized((0, 0, 0, 0))
        with self.assertRaises(ValueError):
            RollPlan(VisualPose((0, 0, 2), (1, 0, 0, 0), (1, 1, 2)), RollDirection.RIGHT)

    def test_target_mismatch_rejected(self):
        for _, _, plan, target in self.cases():
            with self.assertRaises(ValueError):
                plan.validate_target(replace(target, center=add(target.center, (.1, 0, 0))))

    def test_split_cube_roll_is_one_cell_and_other_dimensions_unchanged(self):
        plan = RollPlan(VisualPose((0, 0, .5), (1, 0, 0, 0), (1, 1, 1)), RollDirection.RIGHT)
        self.assertAlmostEqual(plan.sample(1).center[0], 1)
        self.assertAlmostEqual(plan.sample(1).center[2], .5)
        self.assertEqual(plan.sample(1).nominal_dimensions, (1, 1, 1))

    def test_sixteen_move_chain_preserves_face_history(self):
        f = get_animation_fixture('roll-chain')
        b = as_visual_board(f.board)
        pose = canonical_poses(f.initial, b)[None]
        noncanonical = 0
        for request in f.requests:
            plan = RollPlan(pose, request.direction)
            self.assertEqual(plan.sample(0), pose)
            target = canonical_poses(request.after_snapshot, b)[None]
            plan.validate_target(target)
            pose = plan.sample(1)
            dot = abs(sum(a*b for a, b in zip(pose.quaternion, target.quaternion)))
            noncanonical += dot < .99
        self.assertGreater(noncanonical, 4)

    def test_five_hundred_reverse_rolls_have_no_position_drift(self):
        pose = VisualPose((0, 0, 1), (1, 0, 0, 0), (1, 1, 2))
        for i in range(500):
            pose = RollPlan(pose, RollDirection.RIGHT if i % 2 == 0 else RollDirection.LEFT).sample(1)
        self.assertLess(math.dist(pose.center, (0, 0, 1)), 1e-10)
        self.assertAlmostEqual(sum(q*q for q in pose.quaternion), 1, places=12)

    @unittest.skipUnless(importlib.util.find_spec('panda3d'), 'Panda3D not installed')
    def test_panda_component_conversion_and_multiplication_convention(self):
        from panda3d.core import Quat, Vec3
        world = axis_angle((0, 1, 0), 1.2)
        local = axis_angle((1, 0, 0), .7)
        q = qmul(world, local)
        for point in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            pure = rotate(q, point)
            direct = Quat(*q).xform(Vec3(*point))
            # Panda's a*b applies a then b: equivalent runtime composition is
            # Panda(local)*Panda(world), while pure Hamilton is world*local.
            composed = (Quat(*local)*Quat(*world)).xform(Vec3(*point))
            for x, y, z in zip(pure, direct, composed):
                self.assertAlmostEqual(x, y, places=6)
                self.assertAlmostEqual(x, z, places=6)
