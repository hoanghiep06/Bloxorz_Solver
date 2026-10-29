"""Production Mechanics Laboratory: schema, reachable mechanics and actual UI flow."""
from pathlib import Path
import hashlib
import importlib
import json
import tempfile
import unittest
from unittest.mock import Mock,patch
from src.core.board import Board
from src.gui.controller import LevelCatalog,LevelEntry,SOLVER_SPECS
from src.gui.game_adapter import prepare_level
from src.gui.mechanics_focus import mechanic_targets

ROOT=Path(__file__).resolve().parents[1]
LEVEL=ROOT/'levels/level_19.json'
FIXTURE=ROOT/'tests/fixtures/level19'
SCENARIOS=json.loads((FIXTURE/'scenarios.json').read_text())


def walk(board,actions):
    state=board.get_initial_state()
    for action in actions:
        if board.is_goal(state):raise AssertionError('Scenario continues beyond Goal')
        state=board.transition(state,action)
        if state is None:raise AssertionError(f'Invalid prefix action {action}')
    return state


class LaboratoryCoreTests(unittest.TestCase):
    def setUp(self):self.board=Board(str(LEVEL))

    def test_catalog_appends_19_and_preserves_all_original_level_bytes(self):
        catalog=LevelCatalog(ROOT/'levels')
        self.assertEqual([e.level_id for e in catalog.entries],[f'level_{i:02}' for i in range(1,20)])
        self.assertEqual(catalog[-1].title,'The Mechanics Laboratory')
        for file,digest in json.loads((FIXTURE/'original_levels_sha256.json').read_text()).items():
            self.assertEqual(hashlib.sha256((ROOT/file).read_bytes()).hexdigest(),digest,file)

    def test_dimensions_codes_counts_start_goal_and_advanced_contracts(self):
        b=self.board;data,state,snapshot=prepare_level(b,level_id='level_19',session_id='lab')
        self.assertEqual((b.rows,b.cols),(13,17));self.assertEqual((b.start_r,b.start_c),(3,2))
        self.assertTrue(state.is_standing() and b.is_valid_state(state))
        self.assertEqual(data.goal_cells,((9,13),))
        counts={code:sum(row.count(code) for row in b.grid) for code in range(8)}
        self.assertTrue(set(c for row in b.grid for c in row)<=set(range(8)))
        self.assertEqual(tuple(counts[i] for i in (2,3,4,5,6)),(1,8,3,3,2))
        self.assertGreater(counts[0],60);self.assertEqual(len(b.bridges),3)
        self.assertEqual(snapshot.bridge_states[1].present,True)

    def test_all_bridge_cells_targets_and_split_destinations_are_unambiguous(self):
        b=self.board;cells=set();ids={bridge['id'] for bridge in b.bridges}
        self.assertEqual(b.initial_bridges_state,(False,True,False))
        for bridge in b.bridges:
            self.assertGreaterEqual(len(bridge['cells']),2)
            for r,c in bridge['cells']:
                self.assertTrue(0<=r<b.rows and 0<=c<b.cols)
                self.assertEqual(b.grid[r][c],7);self.assertNotIn((r,c),cells);cells.add((r,c))
        self.assertEqual(cells,{(r,c) for r,row in enumerate(b.grid) for c,tile in enumerate(row) if tile==7})
        for sw in b.switches:
            self.assertIn(sw['target'],ids);r,c=sw['cell']
            self.assertEqual(b.grid[r][c],4 if sw['type']=='soft' else 5)
        for source,definition in b.split_switches.items():
            self.assertEqual(b.grid[source[0]][source[1]],6)
            destinations=[tuple(p) for p in definition['split_positions']]
            self.assertEqual(len(set(destinations)),2)
            self.assertGreater(sum(abs(x-y) for x,y in zip(*destinations)),1)
            for cell in destinations:
                self.assertTrue(b.is_valid_cell(*cell,b.initial_bridges_state))
                self.assertEqual(b.grid[cell[0]][cell[1]],1)

    def test_all_36_scenarios_reach_their_real_core_outcomes_from_start(self):
        b=self.board
        self.assertEqual(len(SCENARIOS),36)
        for name,actions in SCENARIOS.items():
            with self.subTest(name=name):
                state=walk(b,actions[:-1]);out=b.describe_transition(state,actions[-1]);n=out.next_state
                kind,*parts=name.split(':')
                if kind in ('fragile-break','interior-fall','edge-fall'):
                    self.assertIsNone(n)
                    self.assertEqual(out.failure_reason,'fragile' if kind=='fragile-break' else 'fall')
                    if parts:self.assertEqual((out.attempted_state.r,out.attempted_state.c),tuple(map(int,parts)))
                    continue
                self.assertIsNotNone(n);self.assertTrue(b.is_valid_state(n))
                if kind in ('soft','heavy'):
                    cell=tuple(map(int,parts));self.assertIn(cell,n.get_occupied_cells())
                    if kind=='heavy':self.assertTrue(n.is_standing())
                elif kind=='split':
                    self.assertFalse(state.is_split());self.assertTrue(n.is_split())
                    self.assertEqual((out.motion_state.r,out.motion_state.c),tuple(map(int,parts)))
                    self.assertEqual(n.cubes,tuple(tuple(p) for p in b.split_switches[tuple(map(int,parts))]['split_positions']))
                elif kind=='fragile-safe':
                    self.assertFalse(n.is_split());self.assertFalse(n.is_standing())
                    self.assertIn(tuple(map(int,parts)),n.get_occupied_cells())
                elif kind.startswith('bridge-'):
                    idx=int(parts[0]);self.assertNotEqual(state.bridges_state[idx],n.bridges_state[idx])
                    self.assertEqual(n.bridges_state[idx],kind=='bridge-open')
                elif kind=='cube-switch':
                    self.assertEqual(n.cubes,state.cubes);self.assertNotEqual(n.active_cube,state.active_cube)
                elif kind=='cube-move':
                    self.assertTrue(state.is_split() and n.is_split())
                    self.assertEqual(n.cubes[1-state.active_cube],state.cubes[1-state.active_cube])
                    self.assertNotEqual(n.cubes[state.active_cube],state.cubes[state.active_cube])
                elif kind=='merge':self.assertTrue(state.is_split());self.assertFalse(n.is_split())
                elif kind=='goal':self.assertTrue(b.is_goal(n))

    def test_heavy_lying_contact_and_repeat_toggle_keep_actual_rules(self):
        b=self.board;root=b.get_initial_state()
        lying=b.transition(root,'D')
        self.assertIn((4,2),lying.get_occupied_cells());self.assertFalse(lying.is_standing())
        self.assertEqual(lying.bridges_state,root.bridges_state)
        state=walk(b,['R','R']);self.assertEqual(state.bridges_state,(True,False,False))
        state=b.transition(b.transition(state,'L'),'R')
        self.assertEqual(state.bridges_state,(True,True,False))

    def test_guide_targets_include_every_instance_in_row_major_order_and_bounds(self):
        b=self.board;data,_,_=prepare_level(b,level_id='level_19',session_id='guide')
        counts={'goal':1,'bridge':3,'soft_switch':3,'heavy_switch':3,'split_switch':2,'fragile':8,
            'void':sum(row.count(0) for row in b.grid)}
        for key,count in counts.items():
            targets=mechanic_targets(data,key);self.assertEqual(len(targets),count,key)
            self.assertEqual([t.cell for t in targets],sorted(t.cell for t in targets))
            self.assertTrue(all(0<=r<b.rows and 0<=c<b.cols for target in targets for r,c in target.cells))

    def test_all_six_solvers_return_valid_goal_paths_without_mutating_level(self):
        raw=LEVEL.read_bytes();b=self.board;root=b.get_initial_state();lengths={}
        for name,(module,cls) in SOLVER_SPECS.items():
            with self.subTest(solver=name):
                result=getattr(importlib.import_module(module),cls)(b).solve()
                self.assertTrue(result.success);self.assertEqual(result.start_state,root)
                self.assertTrue(b.is_goal(walk(b,result.actions)))
                self.assertEqual(result.solution_length,len(result.actions));lengths[name]=result.solution_length
        self.assertEqual(lengths['BFS'],16);self.assertEqual(lengths['IDS'],lengths['BFS'])
        self.assertEqual(lengths['A*'],lengths['BFS'])
        self.assertEqual(LEVEL.read_bytes(),raw);self.assertEqual(b.get_initial_state(),root)

    def test_bfs_resumes_from_real_split_and_changed_bridge_states(self):
        from src.solvers.bfs import BFSSolver
        for key in ('split:4:14','bridge-close:1'):
            state=walk(self.board,SCENARIOS[key]);result=BFSSolver(self.board).solve(start_state=state)
            self.assertTrue(result.success);self.assertEqual(result.start_state,state)
            for action in result.actions:
                state=self.board.transition(state,action);self.assertIsNotNone(state)
            self.assertTrue(self.board.is_goal(state))


from game_integration_support import GameIntegrationCase

class LaboratoryPipelineTests(GameIntegrationCase):
    def setUp(self):
        super().setUp();self.catalog.entries.append(LevelEntry('level_19',LEVEL,'The Mechanics Laboratory'))
        self.index=len(self.catalog)-1;self.assertTrue(self.controller.load_level(self.index))

    def test_manual_scenarios_and_restart_restore_exact_initial_flags_and_actor_mode(self):
        c=self.controller;initial=c.state
        for name in ('bridge-close:1','split:4:14','merge','fragile-break:5:6','interior-fall'):
            for action in SCENARIOS[name]:self.move(action)
            if 'fall' in name or name.startswith('fragile-break'):self.assertEqual(c.phase,'FELL')
            c.restart_level();self.assertEqual(c.state,initial);self.assertEqual(c.moves,0)
            self.assertFalse(c.state.is_split());self.assertFalse(c.manager.is_busy)
            self.assertEqual(c.manager.current_snapshot.broken_fragile_cells,())

    def test_real_laboratory_events_dispatch_audio_once_at_their_animation_cues(self):
        from src.gui.audio_events import AudioEvent as A
        played=[];audio=Mock();audio.play_sfx.side_effect=lambda event,**kw:played.append(event)
        self.app.game_audio=audio;c=self.controller
        cases={
            'bridge-open:0':(A.SOFT_SWITCH,A.BRIDGE_OPEN),
            'bridge-close:1':(A.HEAVY_SWITCH,A.BRIDGE_CLOSE),
            'fragile-break:5:6':(A.FRAGILE_CRACK,A.FRAGILE_BREAK,A.FALL_WIND),
            'split:4:14':(A.SPLIT_SWITCH,A.TELEPORT_CHARGE,A.TELEPORT_ARRIVAL),
            'merge':(A.TELEPORT_CHARGE,A.TELEPORT_ARRIVAL),
            'goal':(A.GOAL_ENERGY,A.GOAL_COMPLETE),
        }
        for name,expected in cases.items():
            self.assertTrue(c.load_level(self.index))
            for action in SCENARIOS[name][:-1]:self.move(action)
            played.clear();self.move(SCENARIOS[name][-1])
            for event in expected:self.assertEqual(played.count(event),1,(name,event,played))
            if name=='merge':self.assertNotIn(A.SPLIT_SWITCH,played)

    def test_all_six_controller_solvers_replay_through_actual_animation_and_commit_once(self):
        c=self.controller
        for name in SOLVER_SPECS:
            self.assertTrue(c.load_level(self.index));c.select_solver(name);c.start_guide('play')
            self.assertIsNotNone(c.search);self.assertTrue(c.search.success)
            self.drain();self.assertEqual(c.phase,'GOAL')
            self.assertTrue(c.board.is_goal(c.state));self.assertEqual(c.moves,c.search.solution_length)


from test_gui_stage3_6_integration import SceneFixture
class LaboratoryUiTests(SceneFixture):
    def setUp(self):
        super().setUp()
        from src.gui.controller import GameController
        from src.gui.game_scene import GameScene
        from src.gui.profile import SaveData
        from src.gui.screens import UIFlow
        from gui_task_support import TaskManagerDouble
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.app.render=self.host;self.app.userExit=Mock();self.app.taskMgr=TaskManagerDouble()
        self.catalog=LevelCatalog(ROOT/'levels');self.hud=self.app.dashboard.hud
        self.c=GameController(catalog=self.catalog,hud=self.hud,
            prepare_scene=lambda data,snapshot:GameScene(self.app,data,snapshot))
        self.addCleanup(self.c.dispose);self.assertTrue(self.c.start());self.c.bind_hud()
        self.flow=UIFlow(self.app,self.c,self.catalog,SaveData(Path(self.temp.name)/'save.json'),Mock(),Mock())
        self.addCleanup(self.flow.dispose);self.c._on_event=self.flow.on_game_event

    def test_level_select_registers_19_and_next_from_18_last_level_disables_next(self):
        from direct.gui.DirectGui import DirectButton
        def buttons(screen):return {str(w['text']):w for w in screen._owned if isinstance(w,DirectButton)}
        with patch.object(self.flow,'_ensure_par'):
            self.flow.start_level(17);self.flow.intro.finish();screen=self.flow.screens['game']
            screen.show_result();self.assertEqual(screen._result.next_level,18)
            buttons(screen)['Next']['command']();self.flow.intro.finish()
            self.assertEqual(self.c.level_index,18);self.assertEqual(self.c.board.name,'The Mechanics Laboratory')
            self.assertTrue(self.hud.model.level_label.endswith('(19/19)'))
            self.assertIn('19/19',self.hud.runtime['text'])
            self.flow.show('levels');select=self.flow.screens['levels']
            self.assertEqual(select.page,2);self.assertEqual(buttons(select)['19']['state'],'normal')
            buttons(select)['19']['command']();self.flow.intro.finish()
            for action in SCENARIOS['goal']:
                self.assertTrue(self.c.manual_move(action))
                while self.c.manager.is_busy:self.c.manager.advance(2)
            self.assertEqual(self.c.phase,'GOAL');self.assertIsNone(screen._result.next_level)
            self.assertEqual(buttons(screen)['Next']['state'],'disabled')
            self.c.restart_level();self.assertEqual(self.c.state,self.c.board.get_initial_state())
            self.flow.show('main');self.assertEqual(self.flow.name,'main')

    def test_guide_cycles_all_repeated_targets_across_themes_without_core_mutation(self):
        with patch.object(self.flow,'_ensure_par'):
            self.flow.start_level(18);self.flow.intro.finish()
        focus=self.flow.mechanics_focus;g=self.flow.mechanics;state=self.c.state,self.c.moves,self.c.revision
        for theme in ('light','dark'):
            self.flow.apply_scene_theme(theme)
            for key in ('fragile','soft_switch','heavy_switch','split_switch','bridge','goal','void'):
                focus.reset(restore=True);targets=mechanic_targets(self.c.board_data,key)
                # All repeated special targets, and the first few voids, then wrap.
                limit=len(targets) if key!='void' else 3
                for i in range(limit):
                    g.show_mechanic(key);focus.advance(.55)
                    self.assertEqual(focus.target,targets[i]);self.assertEqual(state,(self.c.state,self.c.moves,self.c.revision))
                if key!='void':
                    g.show_mechanic(key);focus.advance(.55);self.assertEqual(focus.target,targets[0])
