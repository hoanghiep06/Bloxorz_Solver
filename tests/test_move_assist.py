"""Preview invariants against real Core, including bridge side effects."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from collections import deque

from src.core.board import Board, ACTIONS
from src.core.state import BloxorzState, Orientation
from src.gui.move_assist import predict_moves, MovePredictor, Severity
from src.gui.mouse_control import controlled_cells

LEVELS = Path(__file__).resolve().parent / 'fixtures' / 'mechanics'


class MovePredictionTests(unittest.TestCase):
    def board(self, data=None):
        if data is None:
            return Board(str(LEVELS / 'level_11_advanced_sandbox.json'))
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as f:
            json.dump(data, f); f.flush()
            return Board(f.name)

    def test_three_poses_four_directions_and_either_selected_cube(self):
        board = self.board({'grid': [[1]*9 for _ in range(9)], 'start':[4,4], 'goal':[8,8]})
        states = [BloxorzState(4,4,o) for o in Orientation]
        states += [BloxorzState.create_split((2,2),(6,6),i) for i in (0,1)]
        for state in states:
            result = predict_moves(board,state)
            self.assertEqual(len(result.moves),4)
            for move in result.moves:
                with self.subTest(state=state, action=move.action):
                    core = board.describe_transition(state,move.action)
                    self.assertEqual(move.landing_cells,tuple(controlled_cells(core.motion_state)))
                    self.assertEqual(move.severity,Severity.SAFE)

    def test_reachable_states_across_catalog_match_core_without_mutation(self):
        # Walk the actual rule graph, exercising bridge toggles, fragile, split,
        # merge, and active-cube changes without invoking any solver.
        split = merge = danger = bridge_changes = 0
        for path in sorted((*LEVELS.glob('*.json'), *(Path(__file__).resolve().parents[1]/'levels').glob('*.json'))):
            board = Board(str(path)); before = copy.deepcopy(board.__dict__)
            queue = deque([board.get_initial_state()]); seen = set(queue)
            while queue and len(seen) < 600:
                state = queue.popleft(); state_hash = hash(state)
                preview = predict_moves(board,state)
                for move in preview.moves:
                    core = board.describe_transition(state,move.action)
                    expected = Severity.BLOCKED if core.failure_reason == 'blocked' else (
                        Severity.DANGER if core.next_state is None else Severity.SAFE)
                    self.assertEqual(move.severity,expected)
                    if core.next_state is not None:
                        target = core.next_state
                        split += int(not state.is_split() and target.is_split())
                        merge += int(state.is_split() and not target.is_split())
                        bridge_changes += int(state.bridges_state != target.bridges_state)
                        if target not in seen:
                            seen.add(target);queue.append(target)
                    else:
                        danger += 1
                if state.is_split():
                    target = board.transition(state,'SPACE')
                    if target is not None and target not in seen:
                        seen.add(target);queue.append(target)
                self.assertEqual(hash(state),state_hash)
            self.assertEqual(board.__dict__,before)
        self.assertGreater(split,0);self.assertGreater(merge,0)
        self.assertGreater(danger,0);self.assertGreater(bridge_changes,0)

    def test_cache_includes_board_session_bridges_and_selected_cube(self):
        board = self.board(); predictor = MovePredictor(); state=board.get_initial_state()
        with patch.object(board,'describe_transition',wraps=board.describe_transition) as describe:
            first = predictor.get(board,state,'s1')
            for _ in range(120):self.assertIs(predictor.get(board,state,'s1'),first)
            self.assertEqual(describe.call_count,4)
            predictor.get(board,state,'s2');self.assertEqual(describe.call_count,8)
            split=BloxorzState.create_split((2,7),(6,9),0,state.bridges_state)
            predictor.get(board,split,'s2')
            predictor.get(board,BloxorzState.create_split(*split.cubes,1,state.bridges_state),'s2')
            self.assertEqual(describe.call_count,16)
            predictor.get(board,BloxorzState.create_split(*split.cubes,1,
                tuple(not flag for flag in state.bridges_state)),'s2')
            self.assertEqual(describe.call_count,20)
        predictor.clear();self.assertIsNone(predictor._value)

    def test_off_map_footprint_and_blocked_overlap_are_explicit(self):
        board = self.board({'grid':[[1]*5 for _ in range(5)],'start':[0,0],'goal':[4,4]})
        p=predict_moves(board,board.get_initial_state())
        self.assertEqual(p.for_action('U').severity,Severity.DANGER)
        self.assertTrue(any(r<0 for r,c in p.for_action('U').landing_cells))
        self.assertEqual({a for _,a in p.edges},{'U','L'})
        state=BloxorzState.create_split((2,2),(2,3))
        self.assertEqual(predict_moves(board,state).for_action('R').severity,Severity.BLOCKED)

    def test_fragile_is_safe_for_lying_and_unit_cubes(self):
        grid=[[1]*7 for _ in range(7)];grid[3][3]=3
        board=self.board({'grid':grid,'start':[0,0],'goal':[6,6]})
        standing=predict_moves(board,BloxorzState(3,1,Orientation.HORIZONTAL)).for_action('R')
        self.assertEqual(standing.message,'Fragile tile will break')
        lying=predict_moves(board,BloxorzState(3,1,Orientation.STANDING)).for_action('R')
        self.assertEqual(lying.severity,Severity.SAFE)
        cube=predict_moves(board,BloxorzState.create_split((3,2),(6,5))).for_action('R')
        self.assertEqual(cube.severity,Severity.SAFE)

    def test_split_markers_and_final_merge_footprint(self):
        board=self.board(); state=board.get_initial_state()
        state=board.transition(state,'R')
        preview=predict_moves(board,state).for_action('R')
        outcome=board.describe_transition(state,'R')
        self.assertEqual(preview.landing_cells,tuple(controlled_cells(outcome.motion_state)))
        self.assertEqual(preview.markers,outcome.next_state.cubes)
        # A merge is reported as the final whole footprint, whichever cube moved.
        board=self.board({'grid':[[1]*7 for _ in range(7)],'start':[0,0],'goal':[6,6]})
        for active,action in ((0,'R'),(1,'L')):
            state=BloxorzState.create_split((3,2),(3,4),active)
            result=board.transition(state,action)
            self.assertFalse(result.is_split())
            self.assertEqual(predict_moves(board,state).for_action(action).landing_cells,
                             tuple(result.get_occupied_cells()))

    def test_switch_closing_inactive_cube_support_names_affected_cube(self):
        board=self.board({'grid':[[1,1,4,1,1,7,1,2]],'start':[0,0],'goal':[0,7],
            'bridges':[{'id':0,'cells':[[0,5]],'initial_state':True}],
            'switches':[{'cell':[0,2],'type':'soft','target':0,'action':'close'}]})
        state=BloxorzState.create_split((0,1),(0,5),bridges_state=(True,))
        move=predict_moves(board,state).for_action('R')
        self.assertEqual(move.severity,Severity.DANGER)
        self.assertEqual(move.affected_cube,1)
        self.assertIn('Cube 2',move.message)
        self.assertEqual(move.markers,((0,5),))
        self.assertEqual(move.landing_cells,((0,2),))

    def test_module_import_does_not_load_engine_or_solver(self):
        import subprocess,sys
        result=subprocess.run([sys.executable,'-S','-B','-c',
            "import sys; from src.gui.move_assist import predict_moves; "
            "assert not any(n.startswith(('panda3d','direct','src.solvers')) for n in sys.modules)"],
            cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_fatal_split_preserves_both_teleport_markers(self):
        grid=[[1]*9 for _ in range(5)];grid[2][3]=6;grid[0][6]=7
        board=self.board({'grid':grid,'start':[2,0],'goal':[4,8],
            'bridges':[{'id':0,'cells':[[0,6]],'initial_state':False}],
            'split_switch':{'cell':[2,3],'split_positions':[[0,6],[4,6]]}})
        state=board.transition(board.get_initial_state(),'R')
        move=predict_moves(board,state).for_action('R')
        self.assertEqual(move.severity,Severity.DANGER)
        self.assertEqual(move.markers,((0,6),(4,6)))
        self.assertEqual(move.affected_cube,0)
