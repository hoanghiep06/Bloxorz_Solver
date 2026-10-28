"""Captured Core roots, worker isolation and continuing replay through real animation."""
import importlib
import unittest
from copy import deepcopy
from unittest.mock import patch, Mock
from dataclasses import replace
from src.core.board import Board
from src.core.state import Orientation, BloxorzState
from src.gui.controller import SOLVER_SPECS, Replay
from src.solvers.base_solver import SearchResult
from game_integration_support import GameIntegrationCase, LEVELS
from gui_task_support import TaskManagerDouble


def solver(name, board):
    module, cls = SOLVER_SPECS[name]
    return getattr(importlib.import_module(module), cls)(board)


def follow(board, state, actions):
    for action in actions:
        state = board.transition(state, action)
        if state is None:
            raise AssertionError(f'Invalid Core action {action}')
    return state


class CurrentRootSolverTests(unittest.TestCase):
    def test_all_six_roots_initial_horizontal_vertical_bridge_split_and_active_cube(self):
        for name in SOLVER_SPECS:
            for level, prefix in (('level_01', ()), ('level_01', ('R',)),
                                  ('level_01', ('R','R','D')),
                                  ('level_03_soft_bridge', ('R','R')),
                                  ('level_05_split', ('R','R')),
                                  ('level_05_split', ('R','R','SPACE')),
                                  ('level_10_cube_fragile', ('R','R'))):
                with self.subTest(solver=name, level=level, prefix=prefix):
                    board=Board(str(LEVELS/(level+'.json')))
                    root=follow(board,board.get_initial_state(),prefix)
                    before=deepcopy(vars(board));agent=solver(name,board)
                    # An explicit root must not consult initial state at all.
                    with patch.object(board,'get_initial_state',side_effect=AssertionError('initial root used')):
                        result=agent.solve(start_state=root)
                    self.assertEqual(result.start_state,root)
                    self.assertTrue(result.success)
                    self.assertTrue(board.is_goal(follow(board,root,result.actions)))
                    self.assertEqual(vars(board),before)
                    if name=='UCS':
                        self.assertEqual(agent.solution_states[0],root)
                        self.assertEqual(agent.solution_costs[0],0)
                        self.assertEqual(agent.get_solution_states(result.actions)[0],root)

    def test_all_six_repeated_default_solve_does_not_reuse_previous_root(self):
        board=Board(str(LEVELS/'level_03_soft_bridge.json'))
        root=follow(board,board.get_initial_state(),('R','R'))
        for name in SOLVER_SPECS:
            with self.subTest(solver=name):
                agent=solver(name,board)
                self.assertEqual(agent.solve(start_state=root).solution_length,2)
                default=agent.solve()
                self.assertEqual(default.start_state,board.get_initial_state())
                self.assertEqual(default.solution_length,4)

    def test_state_keys_distinguish_bridge_flags_cube_order_and_selection(self):
        whole=BloxorzState(0,0,Orientation.STANDING,(False,))
        split=BloxorzState.create_split((0,0),(0,3),bridges_state=(False,))
        states={whole,replace(whole,bridges_state=(True,)),split,
                BloxorzState.create_split((0,0),(0,3),1,(False,)),
                BloxorzState.create_split((0,3),(0,0),0,(False,))}
        self.assertEqual(len(states),5)


class CurrentStateReplayTests(GameIntegrationCase):
    def capture(self):
        c=self.controller
        return c.state,c.moves,c.session_id,c.revision,c.manager.current_snapshot,dict(c.manager.current_visual_poses)

    def test_all_six_replay_after_eight_manual_moves_without_reset(self):
        for name in SOLVER_SPECS:
            with self.subTest(solver=name):
                self.load('level_01')
                for action in ('R','L')*4:self.move(action)
                before=self.capture();c=self.controller
                with patch.object(c.manager,'resync',wraps=c.manager.resync) as resync:
                    self.assertTrue(c.select_solver(name));self.assertEqual(self.capture(),before)
                    c.start_guide('step')
                    self.assertEqual(c._search_capture.state,before[0])
                    self.assertEqual(c._search_capture.moves,8)
                    self.assertEqual(c.moves,8)
                    self.assertEqual(c.state,before[0])
                    remaining=c.search.solution_length
                    self.drain();self.assertEqual(c.moves,9)
                    while c.phase!='GOAL':
                        previous=c.moves;c.step();self.drain()
                        self.assertEqual(c.moves,previous+1)
                    self.assertEqual(c.moves,8+remaining)
                    model=self.hud.update_view_model.call_args.args[0]
                    self.assertEqual(model.move_count,8+remaining)
                    self.assertEqual(model.solution_length,remaining)
                    self.assertEqual(c.session_id,before[2])
                    c.end_guide();self.assertEqual(c.phase,'GOAL')
                    self.assertEqual(c.moves,8+remaining);resync.assert_not_called()

    def test_all_six_from_horizontal_vertical_changed_bridge_and_split_cube_one(self):
        for level,prefix in (('level_01',('R',)),('level_01',('R','R','D')),
                             ('level_03_soft_bridge',('R','R')),
                             ('level_05_split',('R','R','SPACE'))):
            for name in SOLVER_SPECS:
                with self.subTest(level=level,solver=name):
                    self.load(level)
                    for action in prefix:self.move(action)
                    before=self.capture();c=self.controller
                    c.select_solver(name);self.assertEqual(self.capture(),before)
                    c.start_guide('play')
                    self.assertEqual(c._solution_states[0],before[0])
                    self.assertEqual(c.moves,len(prefix));self.drain()
                    self.assertEqual(c.phase,'GOAL',c._status)
                    self.assertEqual(c.moves,len(prefix)+c.search.solution_length)
                    self.assertEqual(c.session_id,before[2])

    def test_no_solution_all_six_preserves_state_pose_and_manual_control(self):
        index=self.custom({'grid':[[1,1,1,1,0,2]],'start':[0,0],'goal':[0,5]})
        for name in SOLVER_SPECS:
            with self.subTest(solver=name):
                self.controller.load_level(index);self.move('R');before=self.capture();c=self.controller
                c.select_solver(name);c.start_guide('play')
                self.assertFalse(c.search.success);self.assertEqual(self.capture(),before)
                self.assertIn('NO SOLUTION',c._status);self.assertFalse(c.guide_active)
                self.move('L');self.assertEqual(c.moves,2)

    def test_busy_solver_request_rejected_until_entire_split_commits(self):
        self.load('level_05_split');self.move('R');c=self.controller
        c.manual_move('R');c.manager.advance(c.MOVE_DURATION)
        self.assertFalse(c.run_solver('BFS'));self.assertFalse(c.select_solver('BFS'))
        self.assertIsNone(c._search_capture);self.assertIn('current move',c._status)
        self.drain();self.assertTrue(c.state.is_split())
        self.assertTrue(c.run_solver('BFS',after='step'))
        self.assertTrue(c._solution_states[0].is_split())

    def test_stop_paused_split_finishes_one_action_then_returns_manual_control(self):
        self.load('level_05_split');self.move('R');c=self.controller
        c.select_solver('BFS');c.start_guide('play');c.manager.advance(.1);c.pause()
        c.stop();self.drain()
        self.assertEqual(c.moves,2);self.assertTrue(c.state.is_split())
        self.assertEqual(c._mode,Replay.IDLE);self.assertFalse(c.guide_active)
        self.assertTrue(c.manual_move('SPACE'));self.drain()
        self.assertEqual(c.moves,3)

    def test_step_can_resume_paused_last_action_without_reset(self):
        self.load('level_03_soft_bridge')
        for action in ('R','R','R'):self.move(action)
        c=self.controller;c.select_solver('BFS');c.start_guide('play')
        self.assertEqual(c.search.solution_length,1)
        c.manager.advance(.1);c.pause();c.step();self.drain()
        self.assertEqual(c.phase,'GOAL');self.assertEqual(c.moves,4)

    def job(self):
        c=self.controller;c._task_mgr=TaskManagerDouble()
        job=Mock();job.poll.return_value=None
        c._job_factory=Mock(return_value=job)
        c.select_solver('BFS');c.start_guide('step');c._task_mgr.tick(deferred_only=True)
        return job,c._task_mgr.tasks[0]

    def test_async_board_and_start_root_are_isolated_from_live_configuration(self):
        self.load('level_03_soft_bridge');self.move('R');self.move('R')
        c=self.controller;before=self.capture();job,poll=self.job()
        isolated,_,_,root=c._job_factory.call_args.args
        self.assertIsNot(isolated,c.board);self.assertEqual(root,c.state)
        isolated.grid[0][0]=0;isolated.switches.clear()
        self.assertEqual(c.board.grid[0][0],1);self.assertTrue(c.board.switches)
        self.assertEqual(self.capture(),before)
        self.assertFalse(c.manual_move('L'));self.assertFalse(c.run_solver('A*'))
        job.poll.return_value=True,solver('BFS',c.board).solve(start_state=root)
        c._task_mgr.tick();self.drain();self.assertEqual(c.moves,3)

    def test_restart_level_change_and_stop_discard_old_callbacks(self):
        for operation in ('restart','level','stop'):
            with self.subTest(operation=operation):
                self.load('level_03_soft_bridge');self.move('R');c=self.controller
                job,poll=self.job();capture=c._search_capture
                result=solver('BFS',c.board).solve(start_state=c.state)
                if operation=='restart':c.restart_level()
                elif operation=='level':c.load_level(0)
                else:c.stop()
                before=self.capture();job.cancel.assert_called_once()
                job.poll.return_value=True,result
                poll.function(poll)
                c._finish_search('BFS','play',True,result,capture)
                self.assertEqual(self.capture(),before);self.assertFalse(c.manager.is_busy)
                self.assertEqual(c.phase,'READY')

    def test_invalid_worker_paths_preserve_state_and_return_manual_control(self):
        for kind in ('root','action','not_goal','empty','worker_error'):
            with self.subTest(kind=kind):
                self.load('level_03_soft_bridge');self.move('R');c=self.controller
                before=self.capture();job,poll=self.job();root=c.state
                result=SearchResult(['R'],0,0,1,start_state=root)
                if kind=='root':result.start_state=c.board.get_initial_state()
                elif kind=='action':result.actions=['BAD']
                elif kind=='empty':result.actions=[];result.solution_length=0
                job.poll.return_value=(False,'worker error') if kind=='worker_error' else (True,result)
                c._task_mgr.tick();self.assertEqual(c.phase,'READY')
                self.assertEqual(self.capture(),before)
                self.assertIn('ERROR' if kind=='worker_error' else 'INVALID SOLUTION',c._status)
                self.move('L')

    def test_revision_change_discards_job_without_leaving_solving_lock(self):
        self.load('level_03_soft_bridge');self.move('R');c=self.controller
        job,poll=self.job();c.revision+=1
        before=self.capture();c._task_mgr.tick()
        self.assertEqual(self.capture(),before)
        self.assertEqual(c.phase,'READY');self.assertIsNone(c._job)
        self.assertIn('discarded',c._status);job.cancel.assert_called_once()
        self.assertFalse(c._task_mgr.tasks)

    def test_malformed_worker_result_is_diagnostic_not_ui_exception(self):
        self.load('level_03_soft_bridge');self.move('R');c=self.controller
        before=self.capture();job,poll=self.job();job.poll.return_value=True,None
        c._task_mgr.tick()
        self.assertEqual(c.phase,'READY');self.assertEqual(self.capture(),before)
        self.assertIn('INVALID SOLUTION',c._status);self.move('L')

    def test_already_goal_all_six_no_new_terminal_events_or_motion(self):
        for name in SOLVER_SPECS:
            with self.subTest(solver=name):
                self.load('level_03_soft_bridge')
                for action in ('R',)*4:self.move(action)
                before=self.capture();c=self.controller;events=list(self.events)
                c.select_solver(name);c.start_guide('play')
                self.assertEqual(c.search.solution_length,0)
                self.assertEqual(c.phase,'GOAL');self.assertEqual(self.capture(),before)
                self.assertFalse(c.manager.is_busy);self.assertEqual(self.events,events)

    def test_manual_move_invalidates_previously_captured_remaining_solution(self):
        self.load('level_03_soft_bridge');c=self.controller
        c.select_solver('BFS');c.start_guide('step');self.drain();c.stop()
        self.move('L');c.start_guide('step')
        self.assertEqual(c._solution_states[0],c.board.get_initial_state())
        self.assertEqual(c._search_capture.moves,2)
