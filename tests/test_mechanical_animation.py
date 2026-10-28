"""Mechanical presentation invariants, independent of rendering frame rate."""
from dataclasses import replace
import unittest
from gui_animation_support import AnimationSceneCase, HAS_PANDA
from src.gui.animation_contracts import (
    AnimationRequest, AnimationKind, AnimationEvent, EventKind,
    TerminalVisualOutcome, validate_request,
)


@unittest.skipUnless(HAS_PANDA,'Panda3D required')
class MechanicalAnimationTests(AnimationSceneCase):
    def test_goal_never_crosses_plane_until_inside_unchanged_aperture(self):
        self.build('goal');r=self.fixture.requests[0]
        self.manager.submit(r)
        for i in range(1,101):
            self.manager.advance(r.duration/100)
            low,high=self.manager._rig._whole_model.getTightBounds(self.block)
            if i <= 35:
                self.assertGreaterEqual(low.z,-1e-6)
            if low.z < -1e-6:
                self.assertLessEqual(high.x-low.x,.760001)
                self.assertLessEqual(high.y-low.y,.760001)
            if i >= 35:
                self.assertAlmostEqual(self.manager._rig._whole.getScale().x,.7,places=6)
        self.assertTrue(self.manager._rig._whole.isHidden())

    def test_teleport_never_visits_intermediate_map_cells(self):
        self.build('split');r=self.fixture.requests[0]
        self.manager.submit(r);self.manager.advance(.1*r.duration)
        plan=self.manager._split_plan
        origins={key:p.center for key,p in plan.starts.items()}
        targets=self.manager._targets
        for i in range(1,10):
            self.manager.advance(.09*r.duration)
            for key,pose in self.poses().items():
                if key is None:
                    # Intentional new charging beat retains the solid whole.
                    self.assertLess(self.manager.progress,.24)
                    self.assertEqual(pose,plan.source)
                elif pose != targets[key]:
                    # Energy disassembly may separate each half by at most .1
                    # cell at source; no solid cube travels along the energy arc.
                    self.assertLessEqual(sum((pose.center[j]-origins[key][j])**2
                                             for j in range(3)),.010001)
                else:self.assertEqual(pose.center,targets[key].center)
        # At the discontinuity both actors are invisible, with no long path.
        self.manager.cancel();r=replace(r,request_id='split-hidden')
        self.manager.submit(r);self.manager.advance(.5*r.duration)
        self.assertTrue(all(node.isHidden() for node in self.manager._rig._cubes))

    def test_bridge_thickness_is_constant_while_translating(self):
        self.build('bridge');r=self.fixture.requests[0]
        self.manager.submit(r)
        previous=-1
        for _ in range(9):
            self.manager.advance(.1*r.duration)
            node=self.layer._bridges['bridge-main']
            self.assertEqual(tuple(node.getScale()),(1,1,1))
            self.assertGreaterEqual(node.getZ(),previous);previous=node.getZ()

    def collapse_request(self):
        self.build('fragile');self.finish(self.fixture.requests[0])
        return AnimationRequest(1,'collapse',self.manager.current_snapshot,None,
            AnimationKind.TERMINAL,.9,events=(AnimationEvent(EventKind.FALL),),
            terminal=TerminalVisualOutcome(EventKind.FALL,collapse_cell=(5,2)))

    def test_six_fragments_fall_and_spin_with_actor_then_cancel_cleanly(self):
        r=self.collapse_request();old=self.poses();self.manager.submit(r)
        group,pieces=self.layer._debris[(5,2)]
        self.assertEqual(len(pieces),6);self.assertFalse(group.isHidden())
        first=[p.getPos() for p in pieces]
        self.manager.advance(.45)
        self.assertLess(self.poses()[None].center[2],old[None].center[2])
        self.assertEqual(len({tuple(p.getHpr()) for p in pieces}),6)
        self.assertTrue(all(p.getZ()<q.z for p,q in zip(pieces,first)))
        self.assertTrue(self.layer._fragile[(5,2)][1].isHidden())
        self.manager.cancel()
        self.assertTrue(group.isHidden());self.assertEqual(self.poses(),old)
        self.assertEqual(tuple(self.manager._rig._whole.getScale()),(1,1,1))
        self.assertEqual(self.manager._rig._whole.getColorScale().w,1)

    def test_collapse_metadata_rejects_wrong_kind_and_unbroken_cell(self):
        with self.assertRaises(ValueError):TerminalVisualOutcome(EventKind.GOAL_COMPLETE,collapse_cell=(1,1))
        with self.assertRaises(ValueError):TerminalVisualOutcome(EventKind.FALL,collapse_cell=(-1,True))
        r=self.collapse_request()
        with self.assertRaises(ValueError):validate_request(replace(r,
            terminal=replace(r.terminal,collapse_cell=(0,0))),self.board)
        validate_request(r,self.board)
        self.assertIsNone(TerminalVisualOutcome(EventKind.FALL).collapse_cell)

    def test_all_profiles_same_final_at_30_60_120_fps_and_three_rates(self):
        for name in ('basic-roll','fragile','bridge','switches','split','merge','active-cube','fall','goal'):
            expected=None
            for fps in (30,60,120):
                for rate in (.25,1,4):
                    with self.subTest(profile=name,fps=fps,rate=rate):
                        self.build(name);self.manager.set_playback_rate(rate)
                        r=self.fixture.requests[0];results=[];self.manager.submit(r,results.append)
                        for _ in range(int(r.duration*fps/rate)+3):
                            if not self.manager.is_busy:break
                            self.manager.advance(1/fps)
                        self.assertFalse(self.manager.is_busy);self.assertEqual(len(results),1)
                        state=(self.poses(),self.manager.current_snapshot,
                            self.manager.terminal_outcome,
                            tuple(self.manager._rig._whole.getScale()),
                            self.manager._rig._whole.getColorScale().w)
                        if expected is None:expected=state
                        self.assertEqual(state,expected)

    def test_pause_and_cancel_at_start_middle_end_for_every_effect(self):
        for name in ('fragile','bridge','switches','split','merge','active-cube','fall','goal'):
            for fraction in (0,.5,.999):
                self.build(name);r=self.fixture.requests[0];old=self.poses()
                count=self.root.findAllMatches('**').getNumPaths()
                self.manager.submit(r);self.manager.advance(r.duration*fraction)
                pose=self.poses();self.manager.pause();self.manager.advance(10)
                self.assertEqual(self.poses(),pose)
                self.manager.cancel();self.assertEqual(self.poses(),old)
                self.assertTrue(self.layer.animated_root.isHidden())
                self.assertEqual(self.root.findAllMatches('**').getNumPaths(),count)
