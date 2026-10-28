"""Physical trajectories, boundary derivatives, actor identity and UI ownership."""
from dataclasses import replace
import math,unittest
from types import SimpleNamespace
from unittest.mock import Mock
from src.gui.fall_math import FallPlan,FallTuning,DEFAULT_TUNING,around
from src.gui.animation_math import VisualPose,RollDirection as D,axis_angle,rotate,add,sub
from gui_animation_support import AnimationSceneCase
from src.gui.animation_contracts import AnimationStatus


def pose(q=(1,0,0,0),cube=False):
    p=VisualPose((0,0,0),q,(1,1,1) if cube else (1,1,2))
    return replace(p,center=(0,0,p.extents[2]))


class FallMathTests(unittest.TestCase):
    def assert_vector(self,a,b,delta=1e-6):
        for x,y in zip(a,b):self.assertAlmostEqual(x,y,delta=delta)

    def test_all_three_poses_four_directions_and_cube_start_exactly_at_input(self):
        for q in ((1,0,0,0),axis_angle((0,1,0),math.pi/2),axis_angle((1,0,0),math.pi/2)):
            for cube in (False,True):
                for d in D:
                    p=pose(q,cube);plan=FallPlan(p,roll_direction=d)
                    self.assert_vector(plan.sample(0).pose.center,p.center)
                    self.assert_vector(plan.sample(0).pose.quaternion,p.quaternion)
                    self.assertGreater(plan.omega,0)
                    self.assertGreater(plan.free_time,.4)
                    self.assertEqual(plan.sample(.9).opacity,0)
                    for i in range(61):
                        s=plan.sample(i*.9/60)
                        self.assertEqual(s.pose.nominal_dimensions,p.nominal_dimensions)
                        self.assertTrue(all(math.isfinite(v) for v in (*s.pose.center,*s.pose.quaternion)))
                        self.assertAlmostEqual(sum(v*v for v in s.pose.quaternion),1,places=6)

    def test_position_quaternion_and_velocity_are_continuous_at_two_boundaries(self):
        for d in D:
            f=FallPlan(pose(),roll_direction=d)
            for t in (f.roll_end,f.tip_end):
                eps=1e-6
                a,b,c=f.sample(t-eps).pose,f.sample(t).pose,f.sample(t+eps).pose
                self.assert_vector(a.center,b.center,1e-4);self.assert_vector(b.center,c.center,1e-4)
                self.assert_vector(a.quaternion,b.quaternion,1e-4);self.assert_vector(b.quaternion,c.quaternion,1e-4)
                va=tuple((bb-aa)/eps for aa,bb in zip(a.center,b.center))
                vb=tuple((cc-bb)/eps for bb,cc in zip(b.center,c.center))
                self.assert_vector(va,vb,.001)

    def test_free_fall_has_configured_acceleration_and_tangent_release(self):
        f=FallPlan(pose(),roll_direction=D.RIGHT)
        h=.001;t=f.tip_end+.15
        a,b,c=[f.sample(x).pose.center for x in (t-h,t,t+h)]
        self.assertAlmostEqual((c[2]-2*b[2]+a[2])/h**2,-f.gravity,places=5)
        self.assertAlmostEqual((c[0]-2*b[0]+a[0])/h**2,0,places=5)
        self.assertGreater(f.velocity[0],0);self.assertLess(f.velocity[2],0)

    def test_horizontal_and_vertical_partial_support_keep_actual_last_contact(self):
        for q,center,supports,expected in (
            (axis_angle((0,1,0),math.pi/2),(.5,0,.5),((0,0),),(.5,0,0)),
            (axis_angle((1,0,0),math.pi/2),(0,.5,.5),((0,0),),(0,.5,0))):
            start=VisualPose(center,q,(1,1,2));f=FallPlan(start,supports=supports)
            self.assertEqual(f.case,'partial');self.assertEqual(f.pivot,expected)
            inv=(q[0],-q[1],-q[2],-q[3]);local=rotate(inv,sub(expected,center))
            for i in range(11):
                p=f.sample(i*f.tip_end/10).pose
                self.assert_vector(add(p.center,rotate(p.quaternion,local)),expected)

    def test_unsupported_fragile_bridge_and_airborne_do_not_get_invented_pivot(self):
        for start,supports in ((pose(),()),(replace(pose(),center=(0,0,2)),((0,0),))):
            f=FallPlan(start,supports=supports)
            self.assertIsNone(f.pivot);self.assertEqual(f.tip_end,0)
            self.assertEqual(f.sample(0).pose,start)
            self.assert_vector(f.sample(.2).pose.quaternion,start.quaternion)

    def test_interior_single_cell_drop_fits_between_unchanged_slabs(self):
        f=FallPlan(pose(),supports=((1,0),(-1,0),(0,1),(0,-1)))
        self.assertIsNone(f.pivot)
        for i in range(61):
            p=f.sample(i*.9/60).pose
            self.assertEqual(p.center[:2],(0.,0.))
            self.assertLessEqual(p.extents[0],.5);self.assertLessEqual(p.extents[1],.5)

    def test_edge_motion_has_no_corner_inside_original_slab_below_the_plane(self):
        for d in D:
            f=FallPlan(pose(),roll_direction=d)
            for i in range(121):
                for x,y,z in f.sample(i*.9/120).pose.corners():
                    self.assertFalse(abs(x)<.48 and abs(y)<.48 and -.18<z<-.001)

    def test_narrow_partial_opening_uses_explicit_nonrotating_occluded_drop_fallback(self):
        from src.gui.fall_math import intersects_slab
        start=VisualPose((.5,0,.5),axis_angle((0,1,0),math.pi/2),(1,1,2))
        f=FallPlan(start,supports=((0,0),(2,0)))
        self.assertEqual(f.case,'confined-drop')
        self.assertIsNone(f.pivot)
        self.assertEqual(f.sample(.2).pose.quaternion,start.quaternion)
        self.assertEqual(f.sample(.2).opacity,1)
        self.assertLess(f.sample(.2).pose.center[2],start.center[2])
        self.assertFalse(intersects_slab(start,(0,0),1))  # touching only
        self.assertTrue(intersects_slab(replace(start,center=(.5,0,.4)),(0,0),1))

    def test_deterministic_random_access_and_no_cumulative_drift_or_early_fade(self):
        f=FallPlan(pose(),roll_direction=D.LEFT)
        expected={t:f.sample(t) for t in (0,.225,.45,.675,.9)}
        for _ in range(100):
            for t in reversed(tuple(expected)):self.assertEqual(f.sample(t),expected[t])
        for i in range(61):
            t=i*.9/60;s=f.sample(t)
            if f.release.center[2]-s.pose.center[2]<DEFAULT_TUNING.fade_depth:
                self.assertEqual(s.opacity,1)
        self.assertEqual(f.sample(99),expected[.9])

    def test_invalid_parameters_fail_without_nan(self):
        for bad in (True,0,-1,float('inf'),float('nan')):
            with self.assertRaises((ValueError,TypeError)):FallTuning(gravity=bad)
            with self.assertRaises((ValueError,TypeError)):FallPlan(pose(),duration=bad)
        with self.assertRaises(ValueError):FallPlan(pose()).sample(float('nan'))
        with self.assertRaises(ValueError):FallTuning(angular_retention=2)


class FallLifecycleTests(AnimationSceneCase):
    def test_explicit_fall_event_window_holds_pose_and_completes_request_once(self):
        self.build('fall')
        from src.gui.animation_contracts import AnimationEvent,EventKind
        request=replace(self.fixture.requests[0],duration=1.,
                        events=(AnimationEvent(EventKind.FALL,start=.25,end=.75),))
        initial=self.manager.current_visual_poses;results=[]
        self.manager.submit(request,results.append);self.manager.advance(.2)
        self.assertEqual(self.manager.current_visual_poses,initial)
        self.manager.advance(.3)
        self.assertNotEqual(self.manager.current_visual_poses,initial)
        self.manager.advance(.3)
        self.assertEqual(self.manager.current_visual_poses,
                         tuple((key,self.manager._fall.sample(1).pose)
                               for key,_ in initial))
        self.assertEqual(results,[])
        self.manager.advance(.2);self.manager.advance(1)
        self.assertEqual(len(results),1)
        self.assertEqual(results[0].status,AnimationStatus.COMPLETED)

    def test_terminal_pause_in_tip_and_freefall_rate_and_once_only_callback(self):
        from src.gui.animation_contracts import TerminalVisualOutcome,EventKind
        for rate in (.5,1,2):
            for phase in (.1,.5):
                self.build('basic-roll')
                from src.gui.animation_contracts import AnimationRequest,AnimationKind,AnimationEvent
                request=AnimationRequest(1,'edge',self.manager.current_snapshot,None,AnimationKind.TERMINAL,.9,
                    events=(AnimationEvent(EventKind.FALL),),terminal=TerminalVisualOutcome(EventKind.FALL,roll_direction=D.RIGHT))
                results=[];self.manager.set_playback_rate(rate);self.manager.submit(request,results.append)
                self.manager.advance(phase*.9/rate)
                old=self.manager.current_visual_poses
                self.manager.pause();self.manager.advance(20);self.assertEqual(self.manager.current_visual_poses,old)
                self.manager.resume();self.manager.advance(10);self.manager.advance(10)
                self.assertEqual(len(results),1);self.assertEqual(results[0].status,AnimationStatus.COMPLETED)
                self.assertTrue(self.manager._rig._whole.isHidden())
                self.assertFalse(self.renderer._actor_visuals_visible)

    def test_edge_fall_same_final_at_30_60_120_fps_and_half_normal_double_rate(self):
        from src.gui.animation_contracts import AnimationRequest,AnimationKind,AnimationEvent,EventKind,TerminalVisualOutcome
        expected=None
        for fps in (30,60,120):
            for rate in (.5,1,2):
                self.build('basic-roll');self.manager.set_playback_rate(rate)
                r=AnimationRequest(1,'edge-fps',self.manager.current_snapshot,None,AnimationKind.TERMINAL,.9,
                    events=(AnimationEvent(EventKind.FALL),),terminal=TerminalVisualOutcome(EventKind.FALL,roll_direction=D.LEFT))
                results=[];self.manager.submit(r,results.append)
                for _ in range(int(.9*fps/rate)+3):
                    if not self.manager.is_busy:break
                    self.manager.advance(1/fps)
                actual=(self.manager.current_visual_poses,self.manager._rig._whole.getColorScale().w)
                if expected is None:expected=actual
                self.assertEqual(actual,expected);self.assertEqual(len(results),1)

    def test_cancel_dispose_and_new_session_cannot_complete_old_fall(self):
        for method in ('cancel','dispose','resync'):
            for progress in (.01,.5,.95):
                self.build('fall');r=self.fixture.requests[0];results=[]
                self.manager.submit(r,results.append);self.manager.advance(r.duration*progress)
                if method=='resync':self.manager.resync(replace(self.fixture.initial,session_id='new'))
                else:getattr(self.manager,method)()
                self.assertEqual(len(results),1);self.assertEqual(results[0].status,AnimationStatus.CANCELLED)
                self.assertIsNone(results[0].terminal_outcome)
                if method!='dispose':
                    self.manager.advance(10);self.assertEqual(len(results),1)

    def test_split_fall_reuses_only_named_cube_node_and_keeps_other_pose(self):
        self.build('cube-roll')
        from src.gui.animation_contracts import AnimationRequest,AnimationKind,AnimationEvent,EventKind,TerminalVisualOutcome
        before=self.poses();key='cube-a'
        request=AnimationRequest(1,'split-fall',self.manager.current_snapshot,None,AnimationKind.TERMINAL,.9,
            events=(AnimationEvent(EventKind.FALL),),terminal=TerminalVisualOutcome(EventKind.FALL,actor_id=key))
        self.manager.submit(request)
        node=self.manager._rig._cubes[self.manager._rig._slots[key]].node()
        for _ in range(20):
            self.manager.advance(.04)
            self.assertEqual(self.poses()['cube-b'],before['cube-b'])
            self.assertEqual(self.manager._rig._cubes[self.manager._rig._slots[key]].node(),node)
        self.manager.advance(1)
        self.assertEqual(self.poses()['cube-a'].nominal_dimensions,(1,1,1))


class AssistDefaultTests(unittest.TestCase):
    def test_disabled_assist_creates_no_nodes_tasks_or_predictor(self):
        from src.gui.move_arrows import MoveAssistLayer
        app=Mock();c=Mock()
        guide=MoveAssistLayer(app,c,lambda:True)
        self.assertFalse(guide.enabled)
        self.assertIsNone(guide.root);self.assertIsNone(guide._task);self.assertIsNone(guide.predictor)
        app.render.attachNewNode.assert_not_called();app.taskMgr.add.assert_not_called()
        self.assertIsNone(guide._hover());guide.dispose();guide.dispose()
