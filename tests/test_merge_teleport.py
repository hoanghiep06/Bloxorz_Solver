"""Cyan energy fusion uses supplied endpoints, elapsed time and existing ownership."""
from dataclasses import replace
import unittest
from src.gui.animation_math import VisualPose, axis_angle
from src.gui.split_teleport_math import MergeTeleportPlan, MERGE_TELEPORT_DURATION
from src.gui.animation_contracts import EventKind
from gui_animation_support import AnimationSceneCase
from game_integration_support import GameIntegrationCase


class MergeMathTests(unittest.TestCase):
    def plan(self,vertical=False):
        target=VisualPose((1,2,.5),axis_angle((1,0,0) if vertical else (0,1,0),1.5707963267948966),(1,1,2))
        sources={'b':VisualPose((1,3,.5),(1,0,0,0),(1,1,1)),
                 'a':VisualPose((1,1,.5),(1,0,0,0),(1,1,1))}
        return MergeTeleportPlan(sources,target,('b','a'),'a')

    def test_five_beats_start_exact_cubes_end_exact_whole_horizontally_or_vertically(self):
        for vertical in (False,True):
            plan=self.plan(vertical)
            start,end=plan.sample(0),plan.sample(1)
            self.assertEqual(start.poses,plan.targets)
            self.assertEqual(start.opacity,{'a':1,'b':1})
            self.assertEqual(start.weights,{'a':1})
            self.assertEqual(end.poses,{None:plan.source})
            self.assertEqual(end.scales,{None:1});self.assertEqual(end.opacity,{None:1})
            self.assertEqual(end.weights,{})
            for t,phase in ((.1,'MERGE_CHARGE'),(.3,'MERGE_DISSOLVE'),(.55,'MERGE_CONVERGE'),
                            (.76,'MERGE_RECONSTRUCT'),(.94,'MERGE_SETTLE')):
                self.assertEqual(plan.sample(t).phase,phase)

    def test_visible_cubes_remain_at_source_or_inside_final_footprint_no_flight(self):
        for vertical in (False,True):
            plan=self.plan(vertical)
            for i in range(1001):
                t=i/1000;frame=plan.sample(t)
                for key,pose in frame.poses.items():
                    if key is None:
                        self.assertEqual(pose,plan.source);continue
                    if frame.opacity[key]==0:continue
                    if t<.42:self.assertEqual(pose,plan.targets[key])
                    else:
                        start=plan._reverse.starts[key]
                        self.assertLessEqual(sum((pose.center[j]-start.center[j])**2 for j in range(3)),.010001)
            for t in (.43,.50,.60):
                self.assertTrue(all(v==0 for v in plan.sample(t).opacity.values()))

    def test_reverse_visual_clock_decreases_continuously_and_covers_entire_effect(self):
        previous=1
        for i in range(1001):
            t=i/1000;v=MergeTeleportPlan.visual_progress(t)
            self.assertLessEqual(v,previous);self.assertGreaterEqual(v,0);previous=v
        self.assertEqual(previous,0)


class MergeVFXTests(AnimationSceneCase):
    FIXTURE='merge'

    def test_real_pool_converges_then_releases_and_no_active_marker_remains(self):
        r=self.fixture.requests[0];self.manager.submit(r)
        self.manager.advance(r.duration*.55)
        fx=self.manager._split_vfx
        self.assertFalse(fx.root.isHidden());self.assertEqual(fx.phase,'MERGE_CONVERGE')
        self.assertTrue(any(not core.isHidden() for lane in fx.streams for _,core in lane))
        self.assertTrue(all(node.isHidden() for node in self.manager._rig._cubes))
        self.manager.advance(r.duration)
        self.assertEqual(set(self.poses()),{None})
        self.assertTrue(fx.root.isHidden());self.assertEqual(fx.phase,'IDLE')
        self.assertTrue(all(n.isHidden() for n in self.manager._rig._indicators))
        self.assertEqual(self.manager._rig._whole.getColorScale()[3],1)
        self.assertEqual(tuple(self.manager._rig._whole.getScale()),(1,1,1))

    def test_pause_cancel_resync_and_dispose_at_each_fusion_beat(self):
        for t in (.1,.3,.55,.76,.94):
            for operation in ('cancel','resync','dispose'):
                with self.subTest(t=t,operation=operation):
                    self.build('merge');r=self.fixture.requests[0];old=self.poses()
                    self.manager.submit(r);self.manager.advance(r.duration*t)
                    self.manager.pause();state=self.state();self.manager.advance(20)
                    self.assertEqual(self.state(),state)
                    fx=self.manager._split_vfx
                    if operation=='dispose':self.manager.dispose();self.assertTrue(fx.root.isEmpty())
                    else:
                        if operation=='resync':self.manager.resync(self.fixture.initial)
                        else:self.manager.cancel()
                        self.assertEqual(self.poses(),old);self.assertTrue(fx.root.isHidden())
                        self.assertTrue(all(n.getColorScale()[3]==1 for n in self.manager._rig._cubes))
                    self.assertTrue(all(not node.isEmpty() for node in self.foreign))

    def test_deterministic_final_at_30_60_120_fps_and_three_rates(self):
        expected=None
        for fps in (30,60,120):
            for rate in (.25,1,4):
                self.build('merge');r=self.fixture.requests[0];self.manager.set_playback_rate(rate)
                self.manager.submit(r)
                while self.manager.is_busy:self.manager.advance(1/fps)
                result=(self.poses(),self.manager.current_snapshot)
                if expected is None:expected=result
                self.assertEqual(result,expected);self.assertTrue(self.manager._split_vfx.root.isHidden())

    def test_event_window_and_repeated_merges_do_not_add_nodes_or_tasks(self):
        r=self.fixture.requests[0];count=self.root.findAllMatches('**').getNumPaths()
        pool=self.manager._split_vfx
        for i in range(20):
            before=replace(r.before_snapshot,session_id=f'merge-{i}')
            after=replace(r.after_snapshot,session_id=before.session_id)
            self.manager.resync(before)
            request=replace(r,request_id=f'merge-{i}',before_snapshot=before,after_snapshot=after,
                            events=(replace(r.events[0],start=.2,end=.8),))
            self.manager.submit(request);self.manager.advance(r.duration*.1)
            self.assertTrue(pool.root.isHidden())
            self.manager.advance(r.duration*.5);self.assertFalse(pool.root.isHidden())
            self.manager.advance(r.duration)
            self.assertEqual(self.root.findAllMatches('**').getNumPaths(),count)
            self.assertIs(self.manager._split_vfx,pool);self.assertIsNone(self.manager._task)


class MergeGameplayTests(GameIntegrationCase):
    def prepare_merge(self):
        self.load('level_05_split')
        for action in ('R','R','SPACE'):self.move(action)
        c=self.controller;self.assertTrue(c.state.is_split())
        return c

    def test_split_and_merge_share_pool_commit_once_and_continue_whole_roll(self):
        c=self.prepare_merge();pool=c.manager._split_vfx;before=c.state
        c.manual_move('R');c.manager.advance(c.MOVE_DURATION)
        request=c.manager._request
        self.assertTrue(any(e.kind is EventKind.MERGE for e in request.events))
        self.assertEqual(request.duration,MERGE_TELEPORT_DURATION)
        c.manager.advance(request.duration*.6)
        self.assertEqual(c.state,before);self.assertEqual(c.moves,3)
        self.assertIs(c.manager._split_vfx,pool)
        self.drain();self.assertEqual(c.moves,4);self.assertFalse(c.state.is_split())
        self.move('R');self.assertEqual(c.phase,'GOAL');self.assertEqual(c.moves,5)

    def test_restart_or_change_level_during_fusion_removes_effect_and_stale_commit(self):
        for mode in ('restart','level'):
            c=self.prepare_merge();c.manual_move('R');c.manager.advance(c.MOVE_DURATION)
            c.manager.advance(MERGE_TELEPORT_DURATION*.55);pool=c.manager._split_vfx
            if mode=='restart':c.restart_level();self.assertTrue(pool.root.isHidden())
            else:c.load_level(0);self.assertTrue(pool.root.isEmpty())
            self.drain();self.assertEqual(c.moves,0);self.assertFalse(c.state.is_split())
