"""Core -> Advanced DTO -> phased controller -> actual Panda scene graph."""
import importlib.util
import unittest
from dataclasses import replace
from unittest.mock import patch, Mock

HAS_PANDA=importlib.util.find_spec('panda3d') is not None
if HAS_PANDA:
    from game_integration_support import GameIntegrationCase
    from src.gui.controller import Replay, SOLVER_SPECS
    from src.gui.animation_contracts import EventKind, AnimationStatus
else:
    GameIntegrationCase=unittest.TestCase

@unittest.skipUnless(HAS_PANDA,'Panda3D required for game scene integration.')
class GamePipelineTests(GameIntegrationCase):
    def test_all_ten_levels_and_six_solvers_replay_through_real_animation(self):
        self.assertGreaterEqual(len(self.catalog),10)
        for index,entry in enumerate(self.catalog.entries):
            for name in SOLVER_SPECS:
                with self.subTest(level=entry.level_id,solver=name):
                    self.assertTrue(self.controller.load_level(index),self.controller._status)
                    self.events.clear()
                    self.controller.select_solver(name)
                    self.controller.start_guide('play')
                    result=self.controller.search
                    self.assertTrue(result.success,self.controller._status)
                    self.drain()
                    self.assertEqual(self.controller.phase,'GOAL',self.controller._status)
                    self.assertTrue(self.controller.board.is_goal(self.controller.state))
                    self.assertEqual(self.controller.moves,result.solution_length)
                    self.assertEqual(self.events.count('goal'),1)

    def test_split_space_merge_commit_one_core_action_after_all_phases(self):
        self.load('level_05_split')
        self.move('R')
        c=self.controller;old=c.state
        self.assertTrue(c.manual_move('R'))
        c.manager.advance(c.MOVE_DURATION)
        self.assertIs(c.state,old)
        self.assertEqual(c.moves,1)
        self.assertTrue(c.manager.is_busy)
        self.drain()
        self.assertTrue(c.state.is_split())
        self.assertEqual(c.moves,2)
        self.assertEqual(c._snapshot().active_cube_id,'cube-0')
        self.move('SPACE')
        self.assertEqual(c.state.active_cube,1)
        self.assertEqual(c._snapshot().active_cube_id,'cube-1')
        self.move('R')
        self.assertFalse(c.state.is_split())
        self.assertEqual(c.moves,4)
        self.move('R')
        self.assertEqual(c.phase,'GOAL')

    def test_split_moves_only_selected_cube_in_core_and_animation(self):
        grid=[[1]*13 for _ in range(9)]
        grid[4][3]=6;grid[8][12]=2
        index=self.custom({'grid':grid,'start':[4,0],'goal':[8,12],
            'split_switch':{'cell':[4,3],'split_positions':[[4,5],[4,9]]}})
        self.assertTrue(self.controller.load_level(index))
        self.move('R');self.move('R')
        c=self.controller
        for active in (0,1):
            if c.state.active_cube!=active:self.move('SPACE')
            for action in ('R','L','U','D'):
                with self.subTest(active=active,action=action):
                    old=c.state
                    poses=dict(c.manager.current_visual_poses)
                    self.assertTrue(c.manual_move(action))
                    c.manager.advance(.1)
                    during=dict(c.manager.current_visual_poses)
                    self.assertEqual(during[f'cube-{1-active}'],poses[f'cube-{1-active}'])
                    self.assertNotEqual(during[f'cube-{active}'],poses[f'cube-{active}'])
                    self.drain()
                    self.assertTrue(c.state.is_split())
                    self.assertEqual(c.state.cubes[1-active],old.cubes[1-active])
                    self.assertNotEqual(c.state.cubes[active],old.cubes[active])

    def test_cubes_merge_only_at_shared_edge_then_move_as_one_block(self):
        from src.core.state import Orientation
        cases=(
            ([(4,5),(4,9)],('L','L','L'),Orientation.HORIZONTAL,'R',(4,7)),
            ([(2,5),(6,5)],('U','U','U'),Orientation.VERTICAL,'D',(4,5)),
            ([(2,3),(4,5)],('U','L','U'),Orientation.HORIZONTAL,'R',(2,5)),
        )
        for positions,actions,orientation,whole_action,anchor in cases:
            with self.subTest(positions=positions):
                grid=[[1]*13 for _ in range(9)]
                grid[4][3]=6;grid[8][12]=2
                index=self.custom({'grid':grid,'start':[4,0],'goal':[8,12],
                    'split_switch':{'cell':[4,3],'split_positions':positions}})
                self.assertTrue(self.controller.load_level(index))
                self.move('R');self.move('R');self.move('SPACE')
                c=self.controller
                for action in actions[:-1]:
                    self.move(action)
                    self.assertTrue(c.state.is_split())
                    self.assertEqual(len(c.manager.current_visual_poses),2)
                self.move(actions[-1])
                self.assertFalse(c.state.is_split())
                self.assertEqual(c.state.orientation,orientation)
                self.assertEqual([key for key,_ in c.manager.current_visual_poses],[None])
                self.move(whole_action)
                self.assertEqual((c.state.r,c.state.c),anchor)
                self.assertEqual(c.state.orientation,Orientation.STANDING)
                self.assertIsNone(c._snapshot().active_cube_id)

    def test_bridge_flags_ids_and_switch_visuals_match_core(self):
        self.load('level_03_soft_bridge')
        self.move('R');self.move('R')
        c=self.controller;snapshot=c.manager.current_snapshot
        self.assertEqual(c.state.bridges_state,(True,))
        self.assertEqual([(s.bridge_id,s.present) for s in snapshot.bridge_states],[('0',True)])
        self.assertEqual(snapshot.activated_switch_ids,('switch:0:3',))
        self.assertIsNotNone(c.manager.surface_layer)
        self.move('R')
        self.assertEqual(c.manager.current_snapshot.activated_switch_ids,())

    def test_fragile_failure_rolls_to_tile_breaks_then_falls(self):
        index=self.custom({'grid':[[1,1,1,3,1,1,2]],'start':[0,0],'goal':[0,6]})
        self.assertTrue(self.controller.load_level(index))
        self.move('R');c=self.controller;old=c.state
        self.assertTrue(c.manual_move('R'))
        kinds=[event.kind for request in (c.manager._request,*c._pending_requests)
               for event in request.events]
        self.assertIn(EventKind.FRAGILE_BREAK,kinds)
        self.assertEqual(kinds[-1],EventKind.FALL)
        self.drain()
        self.assertEqual(c.phase,'FELL')
        self.assertIs(c.state,old)
        self.assertEqual(c.manager.current_snapshot.whole_pose.anchor_cell,(0,3))
        self.assertEqual(c.manager.current_snapshot.broken_fragile_cells,((0,3),))
        c.restart_level()
        self.assertEqual(c.manager.current_snapshot.broken_fragile_cells,())

    def test_off_board_fall_rolls_in_requested_direction(self):
        self.load('level_02_fragile')
        c=self.controller
        before=dict(c.manager.current_visual_poses)[None].center
        c.manual_move('U');c.manager.advance(.3)
        after=dict(c.manager.current_visual_poses)[None].center
        self.assertNotEqual(before[:2],after[:2])
        self.drain();self.assertEqual(c.phase,'FELL')

    def test_restart_during_split_cancels_phases_without_stale_commit(self):
        self.load('level_05_split');self.move('R')
        c=self.controller;c.manual_move('R');c.manager.advance(c.MOVE_DURATION)
        self.assertTrue(c.manager.is_busy)
        session=c.session_id;c.restart_level();c.manager.advance(10)
        self.assertNotEqual(c.session_id,session)
        self.assertFalse(c.state.is_split());self.assertEqual(c.moves,0)
        self.assertFalse(c.manager.is_busy);self.assertIsNone(c._current_plan)

    def test_invalid_initial_level_keeps_entire_live_scene(self):
        c=self.controller;c.manual_move('R');c.manager.advance(.1)
        old=(c.board,c.manager,c.state,c._scene,c.manager.current_visual_poses)
        index=self.custom({'grid':[[3,1,2]],'start':[0,0],'goal':[0,2]})
        self.assertFalse(c.load_level(index))
        self.assertEqual((c.board,c.manager,c.state,c._scene,c.manager.current_visual_poses),old)
        self.assertTrue(c.manager.is_busy)

    def test_scene_build_failure_preserves_live_scene_and_nodes(self):
        c=self.controller;before=self.root.findAllMatches('**').getNumPaths()
        old=(c.board,c.manager,c.state,c._scene)
        with patch('src.gui.game_scene.AnimationManager',side_effect=RuntimeError('injected build failure')):
            self.assertFalse(c.load_level(1))
        self.assertEqual((c.board,c.manager,c.state,c._scene),old)
        self.assertEqual(self.root.findAllMatches('**').getNumPaths(),before)
        self.move('R')

    def test_scene_activation_failure_keeps_previous_scene_operational(self):
        from src.gui.game_scene import GameScene
        c=self.controller
        old=(c.board,c.manager,c.state,c._scene)
        before=self.root.findAllMatches('**').getNumPaths()
        def fail_activate(board):
            raise RuntimeError('injected camera activation failure')
        c._prepare_scene=lambda board,snapshot:GameScene(self.app,board,snapshot,on_activate=fail_activate)
        self.assertFalse(c.load_level(1))
        self.assertEqual((c.board,c.manager,c.state,c._scene),old)
        self.assertEqual(self.root.findAllMatches('**').getNumPaths(),before)
        self.move('R')

    def test_exception_building_plan_is_caught_and_rolled_back(self):
        c=self.controller;old=c.state
        with patch('src.gui.controller.plan_action',side_effect=ValueError('bad DTO')):
            self.assertFalse(c.manual_move('R'))
        self.assertEqual(c.phase,'ERROR');self.assertIs(c.state,old)
        self.assertEqual(c.manager.current_snapshot.whole_pose.anchor_cell,(old.r,old.c))
        c.restart_level();self.move('R')

    def test_effect_submit_failure_rolls_back_core_and_visual_pose(self):
        self.load('level_05_split');self.move('R')
        c=self.controller;old=c.state;c.manual_move('R')
        with patch.object(c.manager,'submit',side_effect=RuntimeError('effect rejected')):
            c.manager.advance(c.MOVE_DURATION)
        self.assertEqual(c.phase,'ERROR');self.assertIs(c.state,old)
        self.assertEqual(c.manager.current_snapshot.whole_pose.anchor_cell,(old.r,old.c))
        self.assertFalse(c.manager.is_busy)

    def test_step_resumes_paused_roll_but_stops_after_whole_core_action(self):
        self.load('level_05_split');c=self.controller
        c.select_solver('BFS');c.start_guide('step');self.drain()
        self.assertEqual(c.moves,1)
        c.play();c.manager.advance(.08);c.pause()
        self.assertEqual(c.manager.status,AnimationStatus.PAUSED)
        c.step();self.drain()
        self.assertTrue(c.state.is_split());self.assertEqual(c.moves,2)
        self.assertEqual(c._mode,Replay.PAUSED)
        self.assertFalse(c.manager.is_busy)

    def test_zero_action_solution_finishes_and_updates_metrics(self):
        index=self.custom({'grid':[[2]],'start':[0,0],'goal':[0,0]})
        self.assertTrue(self.controller.load_level(index))
        c=self.controller
        self.drain()  # Capture only after the initial Goal terminal animation commits.
        c.select_solver('BFS');c.start_guide('play');self.drain()
        self.assertEqual(c.phase,'GOAL');self.assertEqual(c.moves,0)
        model=self.hud.update_view_model.call_args.args[0]
        self.assertEqual(model.runtime_status,'GOAL REACHED')
        self.assertEqual(model.solution_length,0)
        self.assertIsNotNone(model.search_time_ms)
        c.end_guide()
        self.assertIsNotNone(c.search)
        self.assertEqual(self.hud.update_view_model.call_args.args[0].solution_length,0)

    def test_space_key_binding_and_blocked_whole_space(self):
        c=self.controller;keys={}
        c.bind_keys(lambda key,command,args=():keys.update({key:(command,args)}))
        self.assertIn('space',keys)
        command,args=keys['space'];command(*args)
        self.assertEqual(c.phase,'READY');self.assertFalse(c.manager.is_busy)
        self.assertEqual(c.moves,0)

    def test_space_still_changes_cube_in_mouse_control_mode(self):
        self.load('level_05_split');self.move('R');self.move('R')
        c=self.controller;c.keyboard_enabled=False
        c._key_move('R')
        self.assertFalse(c.manager.is_busy)
        c._key_move('SPACE');self.drain()
        self.assertEqual(c.state.active_cube,1)

    def test_repeated_level_replacement_has_no_scene_or_task_growth(self):
        c=self.controller;counts={}
        for _ in range(5):
            for i,entry in enumerate(self.catalog.entries):
                self.assertTrue(c.load_level(i))
                count=self.root.findAllMatches('**').getNumPaths()
                if i in counts:self.assertEqual(count,counts[i])
                counts[i]=count

    def test_merge_that_closes_support_falls_as_whole_block(self):
        from src.core.state import BloxorzState
        from src.gui.game_adapter import build_game_snapshot
        index=self.custom({'grid':[[1,1,4,7,1,1,1,2]],'start':[0,0],'goal':[0,7],
            'bridges':[{'id':0,'cells':[[0,3]],'initial_state':True}],
            'switches':[{'cell':[0,2],'type':'soft','target':0,'action':'close'}]})
        self.assertTrue(self.controller.load_level(index))
        c=self.controller
        c.state=BloxorzState.create_split((0,1),(0,3),bridges_state=(True,))
        c.session_id='injected-split'
        c.manager.resync(build_game_snapshot(c.state,board_data=c.board_data,
            session_id=c.session_id,state_revision=0))
        self.assertTrue(c.manual_move('R'))
        self.drain()
        self.assertEqual(c.phase,'FELL')
        self.assertIsNone(c.manager.terminal_outcome.actor_id)
        self.assertFalse(c.manager.current_snapshot.bridge_states[0].present)

    def test_async_solver_result_is_applied_only_on_main_task(self):
        from gui_task_support import TaskManagerDouble
        from src.solvers.bfs import BFSSolver
        c=self.controller;scheduler=TaskManagerDouble();c._task_mgr=scheduler
        job=type('Job',(),{'outcome':None,'poll':lambda job:job.outcome,'cancel':lambda job:None})()
        c._job_factory=lambda *args:job
        c.select_solver('BFS');c.start_guide('step');scheduler.tick(deferred_only=True)
        self.assertEqual(c.phase,'SOLVING');self.assertIsNone(c.search)
        scheduler.tick();self.assertIsNone(c.search)
        job.outcome=(True,BFSSolver(c.board).solve());scheduler.tick()
        self.assertIsNotNone(c.search);self.assertTrue(c.manager.is_busy)
        self.drain();self.assertEqual(c.moves,1)

    def test_restart_cancels_solver_and_ignores_late_result(self):
        from gui_task_support import TaskManagerDouble
        c=self.controller;scheduler=TaskManagerDouble();c._task_mgr=scheduler
        job=Mock();job.poll.return_value=None;c._job_factory=lambda *args:job
        c.select_solver('BFS');c.start_guide('play');scheduler.tick(deferred_only=True)
        poll=scheduler.tasks[0]
        c.restart_level()
        job.cancel.assert_called_once()
        poll.function(poll)
        self.assertEqual(c.phase,'READY');self.assertEqual(c.moves,0)
        self.assertIsNone(c.search);self.assertFalse(scheduler.tasks)

    def test_worker_poll_error_is_reported_without_breaking_ui_loop(self):
        from gui_task_support import TaskManagerDouble
        c=self.controller;scheduler=TaskManagerDouble();c._task_mgr=scheduler
        job=Mock();job.poll.side_effect=OSError('broken worker pipe')
        c._job_factory=lambda *args:job
        c.select_solver('BFS');c.start_guide('play');scheduler.tick(deferred_only=True)
        scheduler.tick()
        self.assertEqual(c.phase,'READY')
        self.assertIn('broken worker pipe',c._status)
        self.assertFalse(c.guide_active);self.assertFalse(scheduler.tasks)

if __name__=='__main__':unittest.main()


@unittest.skipUnless(HAS_PANDA,'Panda3D required for game scene integration.')
class GoalActionTimingTests(GameIntegrationCase):
    def test_goal_commit_and_move_count_wait_for_suction_phase(self):
        index=self.custom({'grid':[[1,1,1,2]],'start':[0,0],'goal':[0,3]})
        self.assertTrue(self.controller.load_level(index))
        self.move('R');c=self.controller;old=c.state
        self.assertEqual(c.moves,1)
        self.assertTrue(c.manual_move('R'))
        c.manager.advance(c.MOVE_DURATION)
        self.assertTrue(c.manager.is_busy)
        self.assertEqual(c.manager._request.terminal.kind,EventKind.GOAL_COMPLETE)
        self.assertEqual(c.moves,1);self.assertIs(c.state,old)
        self.assertNotIn('goal',self.events)
        c.manager.advance(c.TERMINAL_DURATION*.5)
        self.assertEqual(c.moves,1);self.assertIs(c.state,old)
        c.manager.pause();pose=c.manager.current_visual_poses
        c.manager.advance(20)
        self.assertEqual(c.manager.current_visual_poses,pose)
        c.manager.resume();self.drain()
        self.assertEqual(c.moves,2);self.assertTrue(c.board.is_goal(c.state))
        self.assertEqual(c.phase,'GOAL');self.assertEqual(self.events.count('goal'),1)

    def test_restart_in_goal_phase_discards_the_uncommitted_action(self):
        index=self.custom({'grid':[[1,1,1,2]],'start':[0,0],'goal':[0,3]})
        self.assertTrue(self.controller.load_level(index))
        self.move('R');c=self.controller;c.manual_move('R')
        c.manager.advance(c.MOVE_DURATION);c.manager.advance(.2)
        c.restart_level();c.manager.advance(10)
        self.assertEqual(c.moves,0);self.assertEqual(c.phase,'READY')
        self.assertFalse(c.board.is_goal(c.state));self.assertNotIn('goal',self.events)
