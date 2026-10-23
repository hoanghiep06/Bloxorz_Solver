"""Lifecycle/rollback/history tests on actual Panda NodePaths, without a window."""
from dataclasses import replace
import threading
import unittest
from unittest.mock import Mock, patch
from gui_animation_support import AnimationSceneCase, HAS_PANDA
from src.gui.animation_contracts import AnimationStatus as Status, as_visual_snapshot
from src.gui.animation_math import canonical_poses, rotate
from src.gui.animation_fixtures import get_animation_fixture


@unittest.skipUnless(HAS_PANDA, 'Panda3D not installed')
class AnimationManagerTests(AnimationSceneCase):
    def test_completion_once_with_identity_and_revision(self):
        results=[]
        request=self.fixture.requests[0]
        self.finish(request, results.append)
        for _ in range(10):
            self.manager.advance(1)
            self.assertFalse(self.manager.cancel())
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, Status.COMPLETED)
        self.assertEqual(results[0].request_id, request.request_id)
        self.assertEqual(results[0].to_state_revision, 1)
        self.assertEqual(self.manager.current_snapshot, request.after_snapshot)

    def test_busy_and_duplicate_reject_without_notification(self):
        request=self.fixture.requests[0]; results=[]
        self.manager.submit(request,results.append)
        with self.assertRaises(RuntimeError):
            self.manager.submit(request,results.append)
        self.manager.cancel()
        with self.assertRaises(ValueError):
            self.manager.submit(request,results.append)
        self.assertEqual(len(results),1)
        self.assertEqual(results[0].status,Status.CANCELLED)

    def test_invalid_geometry_request_leaves_scene_untouched(self):
        r=self.fixture.requests[0]
        after=replace(r.after_snapshot,anchor_cell=(3,7),occupied_cells=((3,7),(3,8)))
        before=self.state(); results=[]
        with self.assertRaises(ValueError):
            self.manager.submit(replace(r,after_snapshot=after),results.append)
        self.assertEqual(self.state(),before)
        self.assertEqual(results,[])
        self.assertFalse(self.manager.is_busy)

    def test_wrong_before_session_or_revision_rejected(self):
        request=self.fixture.requests[0]
        for fields in ({'session_id':'other'},{'state_revision':5}):
            before=replace(request.before_snapshot,**fields)
            after=replace(request.after_snapshot,session_id=before.session_id,state_revision=before.state_revision+1)
            with self.assertRaises(ValueError):
                self.manager.submit(replace(request,before_snapshot=before,after_snapshot=after))

    def test_pause_resume_exact_pose_and_rate_change(self):
        self.manager.submit(self.fixture.requests[0]); self.manager.advance(.2)
        old=self.poses(); graph=self.state()
        self.assertTrue(self.manager.pause());self.assertFalse(self.manager.pause())
        self.manager.advance(99)
        self.manager.set_playback_rate(4)
        self.assertEqual(self.poses(),old);self.assertEqual(self.state(),graph)
        self.assertTrue(self.manager.resume());self.assertFalse(self.manager.resume())
        self.manager.advance(.1)
        self.assertGreater(self.manager.progress,.2/self.fixture.requests[0].duration)

    def test_idle_pause_resume_and_invalid_rate_are_explicit(self):
        self.assertFalse(self.manager.pause());self.assertFalse(self.manager.resume())
        for rate in (0,float('nan'),True,9):
            with self.assertRaises(ValueError):self.manager.set_playback_rate(rate)
        self.assertEqual(self.manager.status,Status.IDLE)

    def test_cancel_restores_before_and_quaternion_without_after_commit(self):
        request=self.fixture.requests[0];results=[];old=self.poses()
        self.manager.submit(request,results.append);self.manager.advance(.4)
        self.assertNotEqual(old,self.poses())
        self.assertTrue(self.manager.cancel());self.assertFalse(self.manager.cancel())
        self.assertEqual(self.poses(),old)
        self.assertEqual(self.manager.current_snapshot,request.before_snapshot)
        self.assertEqual(self.renderer._snapshot,as_visual_snapshot(request.before_snapshot))
        self.assertEqual(results[0].status,Status.CANCELLED)
        self.assertIsNone(results[0].to_state_revision)

    def test_cancellation_blocks_later_events(self):
        self.build('combined')
        self.finish(self.fixture.requests[0])
        request=self.fixture.requests[1]
        self.manager.submit(request);self.manager.advance(.2*request.duration)
        self.manager.cancel();self.manager.advance(99)
        self.assertTrue(self.renderer._bridges['bridge-main'].isHidden())
        self.assertEqual(self.manager.current_snapshot,request.before_snapshot)

    def test_runtime_failure_notifies_once_and_preserves_before(self):
        request=self.fixture.requests[0];results=[]
        self.manager.submit(request,results.append)
        with patch.object(self.manager._rig,'apply',side_effect=RuntimeError('draw failure')):
            with self.assertRaises(RuntimeError):self.manager.advance(.3)
        self.assertEqual(len(results),1)
        self.assertEqual(results[0].status,Status.FAILED)
        self.assertIn('draw failure',results[0].error)
        self.assertEqual(self.manager.current_snapshot,request.before_snapshot)
        self.manager.advance(99)
        self.assertEqual(len(results),1)

    def test_callback_exception_does_not_emit_second_result(self):
        results=[]
        def callback(result):
            results.append(result)
            raise ValueError('callback failure')
        self.manager.submit(self.fixture.requests[0],callback)
        with self.assertRaises(ValueError):self.manager.advance(5)
        self.assertEqual(self.manager.status,Status.COMPLETED)
        self.manager.advance(5)
        self.assertEqual(len(results),1)

    def test_success_callback_can_submit_next_request_safely(self):
        self.build('roll-chain');results=[]
        def first(result):
            results.append(result)
            self.manager.submit(self.fixture.requests[1],results.append)
        self.manager.submit(self.fixture.requests[0],first)
        self.manager.advance(1)
        self.assertEqual(self.manager.current_request_id,self.fixture.requests[1].request_id)
        self.manager.advance(1)
        self.assertEqual(len(results),2)
        self.assertNotEqual(results[0].request_id,results[1].request_id)

    def test_resync_cancels_once_and_intentionally_canonicalizes(self):
        self.build('roll-chain');results=[]
        self.finish(self.fixture.requests[0])
        self.manager.submit(self.fixture.requests[1],results.append);self.manager.advance(.2)
        snapshot=replace(self.fixture.initial,session_id='new-opaque-session')
        self.manager.resync(snapshot)
        self.assertEqual(results[0].status,Status.CANCELLED)
        self.assertEqual(self.manager.status,Status.IDLE)
        self.assertEqual(self.poses(),canonical_poses(snapshot,self.board))

    def test_invalid_resync_does_not_cancel_current_request(self):
        results=[];self.manager.submit(self.fixture.requests[0],results.append)
        with self.assertRaises(ValueError):
            self.manager.resync(replace(self.fixture.initial,board_revision='other'))
        self.assertTrue(self.manager.is_busy);self.assertEqual(results,[])

    def test_resync_callback_barrier_rejects_reentrant_submit(self):
        results=[]
        def callback(result):
            with self.assertRaises(RuntimeError):self.manager.submit(self.fixture.requests[0])
            results.append(result)
        self.manager.submit(self.fixture.requests[0],callback)
        self.manager.resync(replace(self.fixture.initial,session_id='replacement'))
        self.assertEqual(len(results),1);self.assertFalse(self.manager.is_busy)

    def test_dispose_during_animation_stops_task_and_notifies_once(self):
        results=[];self.manager.submit(self.fixture.requests[0],results.append)
        self.manager.advance(.2);self.manager.dispose();self.manager.dispose()
        self.assertEqual(len(results),1);self.assertEqual(results[0].status,Status.CANCELLED)
        self.assertTrue(self.block.find('AnimatedActorRig').isEmpty())
        with self.assertRaises(RuntimeError):self.manager.advance(1)

    def test_one_runtime_task_per_manager_no_per_request_tasks(self):
        from src.gui.animation_manager import AnimationManager
        self.manager.dispose();tasks=Mock();tasks.add.return_value=object()
        self.manager=AnimationManager(self.renderer,self.fixture.board,self.fixture.initial,
            self.block,surface_layer=self.layer,task_mgr=tasks)
        self.finish(self.fixture.requests[0])
        self.manager.dispose();self.manager.dispose()
        tasks.add.assert_called_once();tasks.remove.assert_called_once_with(tasks.add.return_value)

    def test_main_thread_constraint_checked_before_touching_scene(self):
        errors=[]
        def worker():
            try:self.manager.pause()
            except Exception as error:errors.append(error)
        thread=threading.Thread(target=worker);thread.start();thread.join()
        self.assertEqual(len(errors),1);self.assertIsInstance(errors[0],RuntimeError)

    def test_face_history_persists_between_all_sixteen_moves(self):
        self.build('roll-chain');noncanonical=0
        for request in self.fixture.requests:
            previous=self.poses()
            self.manager.submit(request)
            self.assertEqual(self.poses(),previous)
            self.manager.advance(request.duration)
            actual=self.poses()[None]
            canonical=canonical_poses(request.after_snapshot,self.board)[None]
            noncanonical += abs(sum(x*y for x,y in zip(actual.quaternion,canonical.quaternion)))<.99
            self.assertTrue(self.renderer._contents[2].isHidden())
        self.assertGreater(noncanonical,4)

    def test_frame_rate_independence_at_midpoint(self):
        sampled=[]
        for fps in (30,60,120):
            self.build('basic-roll')
            request=replace(self.fixture.requests[0],duration=1)
            self.manager.submit(request)
            for _ in range(fps//2):self.manager.advance(1/fps)
            sampled.append(self.poses()[None])
        for pose in sampled[1:]:
            for a,b in zip((*pose.center,*pose.quaternion),(*sampled[0].center,*sampled[0].quaternion)):
                self.assertAlmostEqual(a,b,places=9)

    def test_actor_visibility_lease_survives_show_and_reload(self):
        self.finish(self.fixture.requests[0])
        self.assertTrue(self.renderer._contents[2].isHidden())
        self.renderer.show_snapshot(as_visual_snapshot(self.manager.current_snapshot))
        self.assertTrue(self.renderer._contents[2].isHidden())
        self.renderer.set_actor_visuals_visible(True)
        self.assertFalse(self.renderer._contents[2].isHidden())
        self.renderer.set_actor_visuals_visible(False)
        with self.assertRaises(TypeError):self.renderer.set_actor_visuals_visible(1)

    def test_no_foreign_or_host_nodes_removed_on_cleanup(self):
        self.finish(self.fixture.requests[0]);self.manager.dispose()
        self.assertTrue(all(not node.isEmpty() for node in (*self.foreign,self.static,self.dynamic,self.block)))

    def test_terminal_waits_for_explicit_resync_without_fake_after(self):
        self.build('fall');results=[]
        self.finish(self.fixture.requests[0],results.append)
        self.assertIsNone(results[0].to_state_revision)
        self.assertIsNotNone(self.manager.terminal_outcome)
        self.assertEqual(self.manager.current_snapshot,self.fixture.initial)
        with self.assertRaises(RuntimeError):self.manager.submit(self.fixture.requests[0])
        self.manager.resync(self.fixture.initial)
        self.assertIsNone(self.manager.terminal_outcome)

    def test_repeated_requests_keep_node_counts_and_bounded_ids(self):
        baseline=self.root.findAllMatches('**').getNumPaths()
        for i in range(150):
            snapshot=replace(self.fixture.initial,session_id=f'visual-stress-{i}')
            self.manager.resync(snapshot)
            request=self.fixture.requests[0]
            after=replace(request.after_snapshot,session_id=snapshot.session_id)
            request=replace(request,request_id=f'roll-{i}',before_snapshot=snapshot,after_snapshot=after)
            self.finish(request)
        self.assertEqual(self.root.findAllMatches('**').getNumPaths(),baseline)
        self.assertEqual(len(self.manager._recent_ids),128)

    def test_request_id_can_be_reused_in_explicit_new_session(self):
        request=self.fixture.requests[0]
        self.finish(request)
        before=replace(self.fixture.initial,session_id='new-session')
        self.manager.resync(before)
        self.finish(replace(request,before_snapshot=before,
            after_snapshot=replace(request.after_snapshot,session_id=before.session_id)))
        self.assertEqual(self.manager.current_snapshot.session_id,'new-session')

    def test_one_shot_runtime_failure_restores_visible_before_state(self):
        request=self.fixture.requests[0];results=[];before=self.state()
        self.manager.submit(request,results.append)
        original=self.manager._rig.apply
        fail=[True]
        def draw(*args,**kwargs):
            if fail[0]:
                fail[0]=False
                raise RuntimeError('one-shot draw failure')
            return original(*args,**kwargs)
        with patch.object(self.manager._rig,'apply',side_effect=draw):
            with self.assertRaises(RuntimeError):self.manager.advance(.3)
        self.assertEqual(results[0].status,Status.FAILED)
        self.assertEqual(self.manager.current_snapshot,request.before_snapshot)
        self.assertFalse(self.manager._rig._whole.isHidden())
