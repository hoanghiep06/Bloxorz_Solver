"""Advanced mapping preserves authoritative identities, definitions and state."""
import json
import tempfile
import unittest
from pathlib import Path
from src.core.board import Board
from src.core.state import BloxorzState, Orientation
from src.gui.game_adapter import build_board_data, build_game_snapshot, prepare_level
from src.gui.advanced_contracts import AdvancedBlockMode, AdvancedTileKind, SwitchVisualKind

class GameAdapterTests(unittest.TestCase):
    def board(self,**updates):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        data={'grid':[[1]*8 for _ in range(3)],'start':[1,0],'goal':[1,7]}
        data.update(updates)
        path=Path(temp.name)/'level.json';path.write_text(json.dumps(data))
        return Board(str(path))
    def test_numeric_codes_and_metadata_are_preserved(self):
        board=self.board(grid=[[1,3,4,5,6,7,1,2],[1]*8,[1]*8],
            bridges=[{'id':0,'cells':[[0,5]],'initial_state':False}],
            switches=[{'cell':[0,2],'type':'soft','target':0},
                      {'cell':[0,3],'type':'heavy','target':0}],
            split_switch={'cell':[0,4],'split_positions':[[2,0],[2,7]]})
        data=build_board_data(board,level_id='codes')
        self.assertEqual(data.tiles[0][1],AdvancedTileKind.FRAGILE)
        self.assertEqual(data.tiles[0][5],AdvancedTileKind.BRIDGE)
        self.assertEqual([s.kind for s in data.switches],
                         [SwitchVisualKind.SOFT,SwitchVisualKind.HEAVY,SwitchVisualKind.SPLIT])
        self.assertEqual(data.bridges[0].bridge_id,'0')
    def test_metadata_with_basic_codes_is_not_dropped(self):
        board=self.board(fragile_tiles=[[0,1]],bridges=[{'id':'bridge','cells':[[0,2]]}],
            switches=[{'cell':[0,3],'type':'soft'}])
        data=build_board_data(board,level_id='metadata')
        self.assertEqual(data.fragile_cells,((0,1),))
        self.assertEqual(data.tiles[0][2],AdvancedTileKind.BRIDGE)
        self.assertEqual(data.switches[0].cell,(0,3))
    def test_snapshot_keeps_cube_order_active_id_and_bridge_flags(self):
        board=self.board(bridges=[{'id':2,'cells':[[2,0]],'initial_state':True},
                                 {'id':1,'cells':[[2,1]],'initial_state':False}])
        data=build_board_data(board,level_id='ids')
        state=BloxorzState.create_split((1,4),(1,2),1,(True,False))
        snapshot=build_game_snapshot(state,board_data=data,session_id='s',state_revision=4)
        self.assertEqual(snapshot.block_mode,AdvancedBlockMode.SPLIT)
        self.assertEqual([(c.cube_id,c.cell) for c in snapshot.cubes],
                         [('cube-0',(1,4)),('cube-1',(1,2))])
        self.assertEqual(snapshot.active_cube_id,'cube-1')
        self.assertEqual([(b.bridge_id,b.present) for b in snapshot.bridge_states],[('2',True),('1',False)])
    def test_whole_heavy_and_cube_soft_switch_activation(self):
        board=self.board(switches=[{'cell':[1,3],'type':'heavy'},{'cell':[1,4],'type':'soft'}])
        data=build_board_data(board,level_id='switches')
        def snapshot(state):return build_game_snapshot(state,board_data=data,session_id='s',state_revision=0)
        self.assertEqual(snapshot(BloxorzState(1,3,Orientation.STANDING)).activated_switch_ids,('switch:1:3',))
        self.assertEqual(snapshot(BloxorzState(1,3,Orientation.HORIZONTAL)).activated_switch_ids,('switch:1:4',))
        self.assertEqual(snapshot(BloxorzState.create_split((1,3),(1,4))).activated_switch_ids,('switch:1:4',))
    def test_mismatched_bridge_count_is_rejected(self):
        data=build_board_data(self.board(bridges=[{'id':0,'cells':[[2,0]]}]),level_id='invalid')
        with self.assertRaisesRegex(ValueError,'bridge flags'):
            build_game_snapshot(BloxorzState(1,0,Orientation.STANDING),board_data=data,session_id='s',state_revision=0)
    def test_bad_mechanic_definitions_fail_before_scene_changes(self):
        for updates in (
            {'split_switch':{'cell':[1,3],'split_positions':[[1,4],[1,4]]}},
            {'split_switch':{'cell':[1,3],'split_positions':[[1,4],[-1,0]]}},
            {'switches':[{'cell':[1,3],'type':'soft'},{'cell':[1,3],'type':'heavy'}]},
            {'grid':[[1,1,1,7,1,1,1,2],[1]*8,[1]*8]},
            {'grid':[[1,1,1,4,1,1,1,2],[1]*8,[1]*8]},
            {'fragile_tiles':[[99,99]]},
        ):
            with self.subTest(updates=updates),self.assertRaises((ValueError,TypeError)):
                build_board_data(self.board(**updates),level_id='bad')
    def test_invalid_fragile_initial_state_is_rejected(self):
        board=self.board(fragile_tiles=[[1,0]])
        with self.assertRaisesRegex(ValueError,'Initial block'):
            prepare_level(board,level_id='bad-start',session_id='s')
    def test_visual_revision_is_deterministic_and_tracks_definitions(self):
        first=build_board_data(self.board(),level_id='same')
        second=build_board_data(self.board(),level_id='same')
        third=build_board_data(self.board(switches=[{'cell':[1,3],'type':'soft'}]),level_id='same')
        self.assertEqual(first.board_revision,second.board_revision)
        self.assertNotEqual(first.board_revision,third.board_revision)

if __name__=='__main__':unittest.main()
