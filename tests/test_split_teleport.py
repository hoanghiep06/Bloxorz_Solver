"""Teleport choreography, endpoint ownership, deterministic VFX and cancellation."""
from dataclasses import replace
import unittest
from src.gui.animation_contracts import AnimationStatus, EventKind
from src.gui.animation_math import VisualPose, axis_angle
from src.gui.split_teleport_math import SplitTeleportPlan, SPLIT_TELEPORT_DURATION
from gui_animation_support import AnimationSceneCase
from game_integration_support import GameIntegrationCase


class TeleportMathTests(unittest.TestCase):
    def plan(self):
        self.source=VisualPose((0,0,1),(1,0,0,0),(1,1,2))
        targets={'a':VisualPose((4,2,.5),(1,0,0,0),(1,1,1)),
                 'b':VisualPose((-3,-2,.5),(1,0,0,0),(1,1,1))}
        return SplitTeleportPlan(self.source,targets,('a','b'),'b')

    def test_six_story_beats_preserve_magma_then_materialize_exact_targets(self):
        plan=self.plan()
        for t,phase in ((.15,'CHARGE'),(.32,'DISASSEMBLE'),(.53,'TRANSIT'),(.78,'MATERIALIZE'),(.96,'ACTIVE')):
            self.assertEqual(plan.sample(t).phase,phase)
        charge=plan.sample(.2)
        self.assertEqual(charge.poses,{None:self.source});self.assertEqual(charge.opacity,{None:1})
        final=plan.sample(1)
        self.assertEqual(final.poses,plan.targets)
        self.assertEqual(final.opacity,{'a':1,'b':1});self.assertEqual(final.scales,{'a':1,'b':1})
        self.assertEqual(final.weights,{'b':1})

    def test_no_solid_actor_ever_flies_between_source_and_destinations(self):
        plan=self.plan()
        for i in range(1001):
            frame=plan.sample(i/1000)
            for key,pose in frame.poses.items():
                if key is None or frame.opacity[key]==0:continue
                if i/1000<.58:
                    self.assertLessEqual(abs(pose.center[0]),.101)
                    self.assertEqual(pose.center[1],0)
                else:self.assertEqual(pose,plan.targets[key])
        for t in (.42,.50,.579,.58,.65,.70):
            self.assertTrue(all(v==0 for v in plan.sample(t).opacity.values()))

    def test_horizontal_source_halves_and_order_follow_source_quaternion(self):
        plan=self.plan();source=replace(self.source,center=(1,1,.5),quaternion=axis_angle((0,1,0),3.141592653589793/2))
        plan=SplitTeleportPlan(source,plan.targets,('b','a'),'a')
        self.assertAlmostEqual(plan.starts['b'].center[0],.5)
        self.assertAlmostEqual(plan.starts['a'].center[0],1.5)
        self.assertEqual(plan.sample(1).poses,plan.targets)

    def test_energy_arc_has_exact_endpoints_and_elevation(self):
        plan=self.plan()
        for index,key in enumerate(plan.cube_ids):
            start,end=plan.stream_point(index,0),plan.stream_point(index,1)
            self.assertAlmostEqual(start[2],1.35)
            for j in (0,1):self.assertAlmostEqual(end[j],plan.targets[key].center[j])
            self.assertGreater(plan.stream_point(index,.5)[2],max(start[2],end[2]))


class TeleportRigTests(AnimationSceneCase):
    FIXTURE='split'

    def begin(self):
        request=self.fixture.requests[0];self.manager.submit(request)
        return request

    def test_pooled_energy_rings_streams_and_reconstruction_are_real_scene_nodes(self):
        r=self.begin();self.manager.advance(r.duration*.53)
        fx=self.manager._split_vfx
        self.assertFalse(fx.root.isHidden());self.assertEqual(fx.phase,'TRANSIT')
        self.assertEqual(len(fx.streams),2)
        self.assertTrue(any(not core.isHidden() for lane in fx.streams for _,core in lane))
        self.assertEqual(len(fx.receivers),2);self.assertEqual(len(fx.shards),28)
        self.assertTrue(all(node.getColorScale()[3]==0 for node in self.manager._rig._cubes))

    def test_pause_freezes_every_fx_transform_and_resume_finishes_exactly(self):
        r=self.begin();self.manager.advance(r.duration*.54);self.manager.pause()
        before=self.state();self.manager.advance(30)
        self.assertEqual(self.state(),before)
        self.manager.resume();self.manager.advance(r.duration)
        self.assertEqual(self.manager.current_snapshot,r.after_snapshot)
        self.assertTrue(self.manager._split_vfx.root.isHidden())
        self.assertEqual(self.manager._split_vfx.phase,'IDLE')
        self.assertTrue(all(tuple(c.getScale())==(1,1,1) for c in self.manager._rig._cubes))

    def test_30_60_120_fps_and_replay_rates_have_same_final_pose(self):
        endings=[]
        for fps in (30,60,120):
            for rate in (.25,1,4):
                self.build('split');r=self.fixture.requests[0]
                self.manager.set_playback_rate(rate);self.manager.submit(r)
                while self.manager.is_busy:self.manager.advance(1/fps)
                endings.append((self.poses(),self.manager.current_snapshot))
                self.assertTrue(self.manager._split_vfx.root.isHidden())
        self.assertTrue(all(end==endings[0] for end in endings))

    def test_cancel_and_resync_at_every_phase_restore_whole_no_energy_residue(self):
        for t in (.1,.32,.54,.78,.96):
            for action in ('cancel','resync'):
                with self.subTest(progress=t,action=action):
                    self.build('split');before=self.poses();r=self.begin()
                    self.manager.advance(r.duration*t)
                    if action=='cancel':self.manager.cancel()
                    else:self.manager.resync(self.fixture.initial)
                    self.assertEqual(self.poses(),before)
                    self.assertTrue(self.manager._split_vfx.root.isHidden())
                    self.assertFalse(self.manager._rig._whole.isHidden())
                    self.assertEqual(tuple(self.manager._rig._whole.getScale()),(1,1,1))
                    self.assertEqual(self.manager._rig._whole.getColorScale()[3],1)

    def test_repeat_teleports_reuse_nodes_and_geometry_without_tasks(self):
        r=self.begin();self.manager.advance(r.duration)
        count=self.root.findAllMatches('**').getNumPaths()
        fx=self.manager._split_vfx;geometry=fx.rings[0].getChild(0).node()
        for i in range(30):
            before=replace(r.before_snapshot,session_id=f'pool-{i}')
            after=replace(r.after_snapshot,session_id=before.session_id)
            self.manager.resync(before)
            self.manager.submit(replace(r,request_id=f'pool-{i}',before_snapshot=before,after_snapshot=after))
            self.manager.advance(r.duration*.6);self.manager.advance(r.duration)
            self.assertEqual(self.root.findAllMatches('**').getNumPaths(),count)
            self.assertIs(self.manager._split_vfx,fx)
            self.assertEqual(fx.rings[0].getChild(0).node(),geometry)
        self.assertIsNone(self.manager._task)

    def test_dispose_mid_teleport_removes_only_owned_vfx(self):
        r=self.begin();self.manager.advance(r.duration*.6)
        fx=self.manager._split_vfx;self.manager.dispose();self.manager.dispose()
        self.assertTrue(fx.root.isEmpty())
        self.assertTrue(all(not node.isEmpty() for node in self.foreign))

    def test_event_start_end_window_is_respected(self):
        r=replace(self.fixture.requests[0],events=(replace(self.fixture.requests[0].events[0],start=.2,end=.8),))
        self.manager.submit(r);self.manager.advance(r.duration*.1)
        self.assertTrue(self.manager._split_vfx.root.isHidden());self.assertEqual(set(self.poses()),{None})
        self.manager.advance(r.duration*.75)
        self.assertTrue(self.manager._split_vfx.root.isHidden())
        self.assertEqual(set(self.poses()),{'cube-a','cube-b'})


class TeleportGameplayTests(GameIntegrationCase):
    def test_manual_split_uses_cinematic_duration_and_commits_only_once_after_vfx(self):
        self.load('level_11_advanced_sandbox');self.move('R');c=self.controller
        before=c.state;self.assertTrue(c.manual_move('R'))
        c.manager.advance(c.MOVE_DURATION)
        request=c.manager._request
        self.assertTrue(any(e.kind is EventKind.SPLIT for e in request.events))
        self.assertEqual(request.duration,SPLIT_TELEPORT_DURATION)
        c.manager.advance(request.duration*.7)
        self.assertEqual(c.state,before);self.assertEqual(c.moves,1)
        self.drain();self.assertEqual(c.moves,2)
        self.assertEqual(c.state.cubes,((2,7),(6,9)))
        self.assertEqual(c.state.active_cube,0)
        self.assertTrue(c.manager._split_vfx.root.isHidden())
        self.move('SPACE');self.assertEqual(c.state.active_cube,1)

    def test_restart_and_level_change_during_transit_clean_effects_and_stale_commit(self):
        for mode in ('restart','level'):
            self.load('level_05_split');self.move('R');c=self.controller
            c.manual_move('R');c.manager.advance(c.MOVE_DURATION)
            c.manager.advance(SPLIT_TELEPORT_DURATION*.5)
            fx=c.manager._split_vfx
            if mode=='restart':c.restart_level();self.assertTrue(fx.root.isHidden())
            else:c.load_level(0);self.assertTrue(fx.root.isEmpty())
            self.drain();self.assertEqual(c.moves,0);self.assertFalse(c.state.is_split())
