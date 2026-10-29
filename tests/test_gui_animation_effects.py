"""Final visuals, intermediates, explicit events, cancellation and actor ownership."""
from dataclasses import replace
import unittest
from gui_animation_support import AnimationSceneCase, HAS_PANDA
from src.gui.animation_contracts import (
    as_visual_snapshot, AnimationRequest, AnimationKind, AnimationEvent,
    EventKind, TerminalVisualOutcome,
)
from src.gui.animation_fixtures import SCENARIOS
from src.gui.animation_math import RollDirection
from src.gui.advanced_contracts import SplitCubeVisualState


@unittest.skipUnless(HAS_PANDA, 'Panda3D not installed')
class AdvancedAnimationTests(AnimationSceneCase):
    def test_fragile_crack_sags_before_terminal_collapse(self):
        self.build('fragile');r=self.fixture.requests[0]
        self.manager.submit(r);self.manager.advance(r.duration*.5)
        intact,broken=self.layer._fragile[(5,2)]
        self.assertFalse(intact.isHidden());self.assertTrue(broken.isHidden())
        self.assertLess(intact.getZ(),0)
        self.assertTrue(self.layer.renderer_root.isHidden())
        self.manager.advance(r.duration)
        self.assertTrue(self.renderer._fragile[(5,2)][0].isHidden())
        self.assertFalse(self.renderer._fragile[(5,2)][1].isHidden())
        self.assertTrue(self.layer.animated_root.isHidden())

    def test_bridge_appears_at_exact_height_then_retracts_to_absence(self):
        self.build('bridge')
        r=self.fixture.requests[0];self.manager.submit(r);self.manager.advance(r.duration*.5)
        self.assertLess(self.layer._bridges['bridge-main'].getZ(),0)
        self.manager.advance(r.duration)
        self.assertFalse(self.renderer._bridges['bridge-main'].isHidden())
        self.assertEqual(self.renderer._bridges['bridge-main'].getZ(),0)
        self.finish(self.fixture.requests[1])
        self.assertTrue(self.renderer._bridges['bridge-main'].isHidden())

    def test_switch_press_and_release_uses_supplied_ids(self):
        self.build('switches');r=self.fixture.requests[0]
        self.manager.submit(r);self.manager.advance(r.duration*.3)
        off,on=self.layer._switches['soft']
        self.assertEqual(off.getZ(),0)  # the socket no longer sinks into the floor
        self.assertLess(off.find('**/SwitchActuator-0').getZ(),0)
        self.manager.advance(r.duration)
        for off,on in self.renderer._switches.values():
            self.assertTrue(off.isHidden());self.assertFalse(on.isHidden())
        self.finish(self.fixture.requests[1])
        for off,on in self.renderer._switches.values():
            self.assertFalse(off.isHidden());self.assertTrue(on.isHidden())

    def test_split_cinematic_moves_two_real_cubes_to_supplied_cells(self):
        self.build('split');r=self.fixture.requests[0]
        self.manager.submit(r);self.manager.advance(r.duration*.5)
        self.assertEqual(set(self.poses()),{'cube-a','cube-b'})
        self.assertTrue(self.manager._rig._whole.isHidden())
        for pose in self.poses().values():self.assertEqual(pose.nominal_dimensions,(1,1,1))
        self.manager.advance(r.duration)
        self.assertEqual(set(self.poses()),{'cube-a','cube-b'})
        self.assertTrue(self.renderer._contents[2].isHidden())
        self.assertEqual(self.renderer._snapshot,as_visual_snapshot(r.after_snapshot))

    def test_merge_final_exactly_one_whole_and_no_orphan_indicator(self):
        self.build('merge');r=self.fixture.requests[0]
        self.manager.submit(r);self.manager.advance(r.duration*.5)
        self.assertEqual(set(self.poses()),{'cube-a','cube-b'})
        self.manager.advance(r.duration)
        self.assertEqual(set(self.poses()),{None})
        self.assertFalse(self.manager._rig._whole.isHidden())
        self.assertTrue(all(c.isHidden() for c in self.manager._rig._cubes))
        self.assertTrue(all(c.isHidden() for c in self.manager._rig._indicators))

    def test_active_id_fades_to_b_then_none_without_moving_cubes(self):
        self.build('active-cube');before=self.poses()
        self.finish(self.fixture.requests[0]);self.assertEqual(self.poses(),before)
        slots=self.manager._rig._slots
        self.assertFalse(self.manager._rig._indicators[slots['cube-b']].isHidden())
        self.assertTrue(self.manager._rig._indicators[slots['cube-a']].isHidden())
        self.finish(self.fixture.requests[1])
        self.assertTrue(all(c.isHidden() for c in self.manager._rig._indicators))
        self.assertEqual(self.poses(),before)

    def test_split_cube_roll_preserves_identity_and_other_cube(self):
        self.build('cube-roll');before=self.poses();r=self.fixture.requests[0]
        self.manager.submit(r);self.manager.advance(r.duration*.5)
        self.assertEqual(self.poses()['cube-b'],before['cube-b'])
        self.assertNotEqual(self.poses()['cube-a'].quaternion,before['cube-a'].quaternion)
        self.manager.advance(r.duration)
        self.assertEqual(self.poses()['cube-b'],before['cube-b'])
        self.assertAlmostEqual(self.poses()['cube-a'].center[0]-before['cube-a'].center[0],1)

    def test_fall_decreases_z_and_does_not_make_fake_snapshot(self):
        self.build('fall');r=self.fixture.requests[0];before=self.poses()[None]
        self.manager.submit(r);self.manager.advance(r.duration*.5)
        self.assertLess(self.poses()[None].center[2],before.center[2])
        self.assertEqual(self.manager.current_snapshot,r.before_snapshot)
        self.manager.advance(r.duration)
        self.assertEqual(self.renderer._snapshot,as_visual_snapshot(r.before_snapshot))
        self.assertEqual(self.manager._rig._whole.getColorScale()[3],0)
        self.assertTrue(self.manager._rig._whole.isHidden())

    def test_goal_shrinks_before_sinking_without_rim_penetration(self):
        self.build('goal');r=self.fixture.requests[0];center=self.poses()[None].center
        self.manager.submit(r);self.manager.advance(r.duration*.5)
        self.assertLess(self.poses()[None].center[2],center[2])
        low,high=self.manager._rig._whole_model.getTightBounds(self.block)
        self.assertLessEqual(high.x-low.x,.76)
        self.assertLessEqual(high.y-low.y,.76)
        self.assertLess(self.manager._rig._whole.getScale().x,1)
        self.manager.advance(r.duration)
        self.assertEqual(self.manager._rig._whole.getColorScale()[3],0)
        self.assertTrue(self.manager._rig._whole.isHidden())
        self.assertIsNone(r.after_snapshot)

    def test_all_effect_cancellations_restore_known_before(self):
        for name in ('fragile','bridge','switches','split','merge','active-cube','fall','goal'):
            self.build(name);r=self.fixture.requests[0];before=self.poses()
            self.manager.submit(r);self.manager.advance(r.duration*.6);self.manager.cancel()
            self.assertEqual(self.poses(),before)
            self.assertEqual(self.renderer._snapshot,as_visual_snapshot(r.before_snapshot))
            self.assertTrue(self.layer.animated_root.isHidden())
            self.assertFalse(self.layer.renderer_root.isHidden())

    def test_combined_events_have_explicit_timing_and_final_state(self):
        self.build('combined')
        self.finish(self.fixture.requests[0])
        r=self.fixture.requests[1]
        self.manager.submit(r);self.manager.advance(r.duration*.2)
        self.assertTrue(self.layer._bridges['bridge-main'].isHidden())
        self.manager.advance(r.duration*.4)
        self.assertFalse(self.layer._bridges['bridge-main'].isHidden())
        self.manager.advance(r.duration)
        for request in self.fixture.requests[2:]:self.finish(request)
        self.assertEqual(self.manager.current_snapshot,self.fixture.requests[-1].after_snapshot)
        self.assertEqual(set(self.poses()),{None})

    def test_no_unbounded_transient_nodes_across_effect_resyncs(self):
        self.build('fragile');baseline=self.root.findAllMatches('**').getNumPaths()
        for i in range(60):
            r=self.fixture.requests[0]
            before=replace(r.before_snapshot,session_id=f'effect-demo-{i}')
            after=replace(r.after_snapshot,session_id=before.session_id)
            self.manager.resync(before)
            self.finish(replace(r,request_id=f'fragile-{i}',before_snapshot=before,after_snapshot=after))
        self.assertEqual(self.root.findAllMatches('**').getNumPaths(),baseline)

    def test_goal_resync_restores_full_scale_opacity_and_visible_actor(self):
        self.build('goal')
        self.finish(self.fixture.requests[0])
        self.manager.resync(self.fixture.initial)
        whole=self.manager._rig._whole
        self.assertFalse(whole.isHidden())
        self.assertEqual(tuple(whole.getScale()),(1,1,1))
        self.assertEqual(whole.getColorScale()[3],1)

    def test_explicit_cube_fall_keeps_other_cube_stationary_and_visible(self):
        self.build('cube-roll')
        before=self.poses()
        request=AnimationRequest(1,'cube-fall',self.fixture.initial,None,
            AnimationKind.TERMINAL,1,events=(AnimationEvent(EventKind.FALL),),
            terminal=TerminalVisualOutcome(EventKind.FALL,actor_id='cube-a'))
        self.finish(request)
        self.assertEqual(self.poses()['cube-b'],before['cube-b'])
        slots=self.manager._rig._slots
        self.assertTrue(self.manager._rig._cubes[slots['cube-a']].isHidden())
        self.assertFalse(self.manager._rig._cubes[slots['cube-b']].isHidden())

    def test_disposal_releases_owned_nodepath_handles_idempotently(self):
        rig=self.manager._rig
        self.manager.dispose();self.renderer.dispose();self.layer.dispose();self.layer.dispose()
        self.assertTrue(rig.root.isEmpty())
        self.assertEqual(rig._cubes,())
        self.assertIsNone(rig._whole)
        self.assertTrue(self.layer.renderer_root.isEmpty())
        self.assertTrue(self.layer.animated_root.isEmpty())
        self.assertTrue(all(not foreign.isEmpty() for foreign in self.foreign))

    def test_cube_face_marker_never_protrudes_through_floor_after_down_roll(self):
        self.build('cube-roll')
        before=self.fixture.initial
        after=replace(before,state_revision=1,cubes=(SplitCubeVisualState('cube-a',(4,4)),before.cubes[1]))
        request=replace(self.fixture.requests[0],after_snapshot=after,direction=RollDirection.DOWN)
        self.finish(request)
        slot=self.manager._rig._slots['cube-a']
        low,high=self.manager._rig._cube_models[slot].getTightBounds(self.block)
        self.assertAlmostEqual(low.z,0,places=6)
        self.assertAlmostEqual(high.z,1,places=6)
        for value in (high.x-low.x,high.y-low.y):self.assertAlmostEqual(value,1,places=6)
