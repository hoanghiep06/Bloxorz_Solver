"""Definition-driven targets, camera ownership, GUI layout and gameplay safety."""
import copy,unittest,tempfile
from pathlib import Path
from types import SimpleNamespace
from dataclasses import replace
from unittest.mock import Mock
from src.gui.mechanics_focus import mechanic_targets,target_status,FOCUS_DURATION
from src.gui.mechanics_icons import IDS,icon_polygons,mechanic_icon
from src.gui.advanced_contracts import (AdvancedTileKind as Tile,SwitchVisualKind,
    create_advanced_board_data,BridgeVisualDefinition,SwitchVisualDefinition,BridgeVisualState)
from src.gui.advanced_mesh_factory import PALETTES,FLAG_CLOTH
from src.gui.camera import CameraConfig,project_point
from src.gui.geometry_math import cell_to_world
from test_gui_stage3_6_integration import SceneFixture


class MechanicsLookupTests(unittest.TestCase):
    def setUp(self):
        tiles=((Tile.VOID,Tile.FRAGILE,Tile.FLOOR,Tile.FLOOR),
               (Tile.BRIDGE,Tile.FLOOR,Tile.FLOOR,Tile.FLOOR),
               (Tile.FLOOR,Tile.FLOOR,Tile.FRAGILE,Tile.FLOOR))
        self.board=create_advanced_board_data('test',tiles,goal_cells=((0,2),),
            bridges=(BridgeVisualDefinition('bridge',((1,0),)),),switches=(
                SwitchVisualDefinition('soft',(0,3),SwitchVisualKind.SOFT),
                SwitchVisualDefinition('heavy',(1,1),SwitchVisualKind.HEAVY),
                SwitchVisualDefinition('split',(1,2),SwitchVisualKind.SPLIT)))

    def test_all_seven_kinds_lookup_exact_definitions_in_row_major_order(self):
        expected={'goal':[(0,2)],'bridge':[(1,0)],'soft_switch':[(0,3)],
            'heavy_switch':[(1,1)],'split_switch':[(1,2)],'fragile':[(0,1),(2,2)],'void':[(0,0)]}
        for key,cells in expected.items():
            self.assertEqual([t.cell for t in mechanic_targets(self.board,key)],cells)
        self.assertEqual(mechanic_targets(self.board,'bridge')[0].identity,'bridge')

    def test_bridge_group_picks_a_real_near_centre_cell_and_dynamic_status_only(self):
        rows=[list(row) for row in self.board.tiles]
        rows[2][0]=rows[2][1]=Tile.BRIDGE
        board=replace(self.board,tiles=tuple(tuple(r) for r in rows),
                      bridges=(BridgeVisualDefinition('multi',((1,0),(2,1),(2,0))),))
        target=mechanic_targets(board,'bridge')[0]
        self.assertIn(target.cell,target.cells);self.assertEqual(target.cells,((1,0),(2,0),(2,1)))
        inactive=SimpleNamespace(bridge_states=(BridgeVisualState('multi',False),))
        self.assertEqual(target_status(target,inactive),'Currently inactive')
        self.assertEqual(target_status(target,SimpleNamespace(bridge_states=(BridgeVisualState('multi',True),))),'')
        fragile=mechanic_targets(board,'fragile')[0]
        self.assertEqual(target_status(fragile,SimpleNamespace(broken_fragile_cells=(fragile.cell,))),'Currently broken')

    def test_void_excludes_absent_bridges_and_out_of_bounds_and_basic_data_supported(self):
        target=mechanic_targets(self.board,'void')[0];self.assertEqual(target.cells,((0,0),))
        for t in mechanic_targets(self.board,'void'):
            self.assertTrue(all(0<=r<self.board.rows and 0<=c<self.board.cols for r,c in t.cells))
        from src.gui.contracts import StaticBoardData,BasicTileKind
        basic=StaticBoardData(1,'basic','v1',1,2,((BasicTileKind.VOID,BasicTileKind.FLOOR),),((0,1),))
        self.assertEqual(mechanic_targets(basic,'split_switch'),())
        self.assertEqual(mechanic_targets(basic,'goal')[0].cell,(0,1))

    def test_multicolour_icon_specs_match_mesh_identity_in_both_themes(self):
        self.assertEqual(len(IDS),7)
        for theme in ('light','dark'):
            specs={key:icon_polygons(key,theme) for key in IDS}
            self.assertIn(FLAG_CLOTH,[c for _,c in specs['goal']])
            for key,token in (('bridge','BRIDGE_RIB'),('heavy_switch','HEAVY_COLOR'),
                              ('split_switch','SPLIT_COLOR'),('fragile','CRACK'),('soft_switch','SOFT_COLOR')):
                self.assertIn(PALETTES[theme][token],[c for _,c in specs[key]])
            self.assertEqual(len(specs['heavy_switch']),4) # base/edge and exactly two bars
            self.assertEqual(len(specs['split_switch']),4) # actual rectangular twin plates
            self.assertEqual(len(specs['void']),4) # outline only, no centre fill
        for key in IDS:
            self.assertEqual([p for p,c in icon_polygons(key,'light')],[p for p,c in icon_polygons(key,'dark')])
        a,b=mechanic_icon('goal'),mechanic_icon('goal');a.setX(99)
        self.assertEqual(b.getX(),0);a.removeNode();b.removeNode()

    def test_fragile_rail_and_card_reuse_actual_opaque_stone_texture_in_both_themes(self):
        from panda3d.core import Filename,PNMImage,TextureAttrib
        from src.gui.visual_materials import ROOT
        source=PNMImage()
        self.assertTrue(source.read(Filename.fromOsSpecific(str(ROOT/'materials/fragile.png'))))
        textures=[]
        for theme in ('light','dark'):
            rail,card=mechanic_icon('fragile',theme),mechanic_icon('fragile',theme)
            self.addCleanup(rail.removeNode);self.addCleanup(card.removeNode)
            rail.setScale(17);card.setScale(18);card.setX(99)
            self.assertEqual(rail.getX(),0)
            self.assertEqual(rail.getScale().x,17)
            node=rail.getChild(0).node()
            textured=[node.getGeomState(i).getAttrib(TextureAttrib)
                      for i in range(node.getNumGeoms())
                      if node.getGeomState(i).hasAttrib(TextureAttrib)]
            self.assertEqual(len(textured),1)
            texture=textured[0].getOnTexture(textured[0].getOnStage(0));textures.append(texture)
            # Emission mask must never make the stone disappear in the HUD.
            self.assertEqual(texture.getNumComponents(),3)
            actual=PNMImage();self.assertTrue(texture.store(actual))
            self.assertEqual((actual.getXSize(),actual.getYSize()),(source.getXSize(),source.getYSize()))
            for x,y in ((0,0),(100,200),(256,256),(400,450)):
                for channel in range(3):
                    self.assertAlmostEqual(actual.getXel(x,y)[channel],source.getXel(x,y)[channel],delta=1/255)
            self.assertEqual(rail.getChild(0).node(),card.getChild(0).node())
            self.assertEqual(rail.findAllMatches('**').getNumPaths(),2)
        self.assertEqual(textures[0],textures[1])


class MechanicsFocusTests(SceneFixture):
    def setUp(self):
        super().setUp()
        from gui_task_support import TaskManagerDouble
        from src.gui.controller import GameController,LevelCatalog
        from src.gui.game_scene import GameScene
        from src.gui.profile import SaveData
        from src.gui.screens import UIFlow
        from src.gui.advanced_preview import build_framing_data
        from src.gui.temple_environment import visible_board_bounds
        from src.gui.camera_views import CameraViewController
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.app.taskMgr=TaskManagerDouble();self.app.render=self.host
        self.app.accept=Mock();self.app.ignore=Mock();self.app.userExit=Mock()
        self.catalog=LevelCatalog(Path(__file__).parent/'fixtures/mechanics')
        camera=self.app.presentation.camera
        def prepare(board,snapshot):
            return GameScene(self.app,board,snapshot,on_activate=lambda data:camera.fit_board(
                build_framing_data(data),1190,720,bounds=visible_board_bounds(data)))
        self.c=GameController(catalog=self.catalog,hud=self.app.dashboard.hud,prepare_scene=prepare)
        self.addCleanup(self.c.dispose);self.c.start();self.c.bind_hud()
        self.views=CameraViewController(self.app,self.c,camera);self.app.game_views=self.views
        self.addCleanup(self.views.dispose)
        self.flow=UIFlow(self.app,self.c,self.catalog,SaveData(Path(self.temp.name)/'save.json'),Mock(),Mock())
        self.addCleanup(self.flow.dispose);self.c._on_event=self.flow.on_game_event
        self.flow.show('game');self.g=self.flow.mechanics;self.focus=self.flow.mechanics_focus;self.camera=camera

    def load(self,name):
        self.c.load_level(next(i for i,e in enumerate(self.catalog.entries) if e.level_id==name))
        self.focus.advance(0)

    def click(self,key):self.g.buttons[key]['command']()

    def advance(self,t=FOCUS_DURATION):self.focus.advance(t)

    def test_goal_focus_projects_in_safe_area_then_back_restores_exact_view_and_state(self):
        self.load('level_11_advanced_sandbox');start=self.camera.capture_presentation()
        original=copy.deepcopy(vars(self.c.board));state=self.c.state
        self.click('goal');self.assertEqual(self.focus.target.cell,self.c.board_data.goal_cells[0])
        self.advance(.275);middle=self.camera.capture_presentation()
        self.assertNotEqual(middle.position,start.position)
        self.advance(.275)
        xy=cell_to_world(*self.focus.target.cell,rows=self.c.board_data.rows,cols=self.c.board_data.cols,pitch=1.)
        x,y,z=project_point((*xy,.06),self.camera.current_fit)
        vx,vy,vw,vh=self.focus._viewport();px,py=vx+(x+1)*vw/2,vy+(1-y)*vh/2
        sx,sy,sw,sh=self.focus._safe_area()
        self.assertAlmostEqual(px,sx+sw/2,delta=.01);self.assertAlmostEqual(py,sy+sh/2,delta=.01)
        self.assertFalse(self.g.layout.card.x<=px<=self.g.layout.card.right)
        self.g.back_button['command']();self.advance()
        self.assertEqual(self.camera.capture_presentation(),start)
        self.assertEqual(vars(self.c.board),original);self.assertEqual(self.c.state,state);self.assertEqual(self.c.moves,0)
        self.assertFalse(self.focus.has_focus)

    def test_cycle_row_major_wraps_reset_on_restart_and_level_change(self):
        self.load('level_11_advanced_sandbox')
        targets=mechanic_targets(self.c.board_data,'fragile');seen=[]
        for _ in range(len(targets)+1):
            self.click('fragile');seen.append(self.focus.target);self.advance()
        self.assertEqual(seen, list(targets)+[targets[0]])
        self.c.restart_level();self.assertIsNone(self.g.selected)
        self.click('fragile');self.assertEqual(self.focus.target,targets[0])
        self.load('level_01');self.assertFalse(self.focus.has_focus);self.assertEqual(self.focus._indices,{})

    def test_absent_only_shows_info_no_camera_move_or_fake_highlight(self):
        self.load('level_01');start=self.camera.capture_presentation()
        self.click('split_switch');self.advance(2)
        self.assertEqual(self.g.selected,'split_switch');self.assertIn('Not present',self.g.locator['text'])
        self.assertEqual(self.camera.capture_presentation(),start)
        self.assertIsNone(self.focus._highlight);self.assertFalse(self.focus.has_focus)

    def test_inactive_bridge_has_outline_no_platform_and_broken_fragile_status(self):
        self.load('level_03_soft_bridge');before=self.c.manager.current_snapshot
        self.click('bridge');self.advance()
        self.assertIn('Currently inactive',self.g.locator['text'])
        self.assertEqual(self.c.manager.current_snapshot,before)
        self.assertEqual(self.focus._highlight.node().getNumGeoms(),1)
        self.assertTrue(self.c.manager.renderer._bridges['0'].isHidden())
        self.assertEqual(self.c.state.bridges_state,(False,))
        self.advance(2);self.assertIsNone(self.focus._highlight)

    def test_busy_help_opens_but_does_not_cancel_roll_or_take_camera(self):
        start=self.camera.capture_presentation();self.c.manual_move('R')
        request=self.c.manager.current_request_id
        self.click('goal');self.advance(.2)
        self.assertIn('unavailable',self.g.locator['text'])
        self.assertEqual(self.camera.capture_presentation(),start)
        self.assertEqual(self.c.manager.current_request_id,request);self.assertTrue(self.c.manager.is_busy)
        self.assertIsNone(self.focus._highlight)

    def test_user_view_change_and_direct_camera_input_cancel_lease_without_fighting(self):
        for change in ('view','raw'):
            self.click('goal');self.advance(.2)
            if change=='view':self.views.set_view(1)
            else:self.camera.camera.setH(self.camera.camera.getH()+20)
            pose=tuple(self.camera.camera.getQuat());self.advance(2)
            self.assertEqual(tuple(self.camera.camera.getQuat()),pose)
            self.assertFalse(self.focus.has_focus);self.assertIsNone(self.views._presentation_owner)

    def test_restore_custom_rotated_view_follow_ownership_and_x_close(self):
        self.camera.configure(CameraConfig(azimuth=137,elevation=50))
        start=self.camera.capture_presentation();self.click('goal');self.advance()
        self.g.close_button['command']();self.advance()
        self.assertEqual(self.camera.capture_presentation(),start)
        self.views.set_view(2);start=self.camera.capture_presentation()
        self.click('goal');self.advance();focused=self.camera.capture_presentation()
        self.views._update(SimpleNamespace(cont='cont'))
        self.assertEqual(self.camera.capture_presentation(),focused)
        self.focus.restore();self.advance();self.assertEqual(self.camera.capture_presentation(),start)
        self.assertIsNone(self.views._presentation_owner)

    def test_same_elapsed_time_at_30_60_120_fps_has_identical_focus_endpoint(self):
        endings=[]
        start=self.camera.capture_presentation()
        for fps in (30,60,120):
            self.camera.apply_presentation(start);self.click('goal')
            for _ in range(round(FOCUS_DURATION*fps)+2):self.advance(1/fps)
            endings.append(self.camera.capture_presentation())
            self.focus.restore();self.advance()
        self.assertTrue(all(view==endings[0] for view in endings))

    def test_focus_during_six_solvers_never_changes_search_root_or_replay(self):
        from src.gui.controller import SOLVER_SPECS
        for name in SOLVER_SPECS:
            self.load('level_03_soft_bridge');root=self.c.state
            self.click('bridge');self.advance(.2)
            self.c.run_solver(name);self.advance(.1)
            self.assertFalse(self.focus.has_focus)
            for _ in range(100):
                if not self.c.manager.is_busy:break
                self.c.manager.advance(2)
            self.assertEqual(self.c.phase,'GOAL');self.assertEqual(self.c.search.start_state,root)

    def test_many_cycles_highlights_cleanup_rail_fixed_and_themes_share_geometry(self):
        rail=self.g.layout.rail;positions={key:tuple(b.getPos(self.app.pixel2d)) for key,b in self.g.buttons.items()}
        for i in range(20):
            self.g.apply_theme('dark' if i%2 else 'light')
            self.click('goal');self.advance(1.2)
            self.assertIsNone(self.focus._highlight)
            self.assertEqual(self.g.layout.rail,rail)
            self.assertEqual({k:tuple(b.getPos(self.app.pixel2d)) for k,b in self.g.buttons.items()},positions)
            self.focus.restore();self.advance()
        self.assertEqual(self.app.effects_root.getNumChildren(),0)

    def test_actual_fragile_failure_locates_broken_cell_without_restoring_floor(self):
        import json
        from src.gui.controller import LevelEntry
        path=Path(self.temp.name)/'fragile-failure.json'
        path.write_text(json.dumps({'grid':[[1,1,1,3,1,1,2]],'start':[0,0],'goal':[0,6]}))
        self.catalog.entries.append(LevelEntry('fragile-failure',path,'Fragile Failure QA'))
        self.c.load_level(len(self.catalog.entries)-1)
        for action in ('R','R'):
            self.c.manual_move(action)
            while self.c.manager.is_busy:self.c.manager.advance(2)
        self.assertEqual(self.c.phase,'FELL')
        before=(self.c.state,self.c.moves,self.c.manager.current_snapshot)
        self.click('fragile');self.advance()
        self.assertEqual(self.focus.target.cell,(0,3))
        self.assertIn('Currently broken',self.g.locator['text'])
        self.assertEqual((self.c.state,self.c.moves,self.c.manager.current_snapshot),before)
        intact,broken=self.c.manager.renderer._fragile[(0,3)]
        self.assertTrue(intact.isHidden());self.assertFalse(broken.isHidden())

    def test_equal_elapsed_midpoint_and_task_budget_across_frame_rates(self):
        initial=self.camera.capture_presentation();poses=[]
        tasks=len(self.app.taskMgr.tasks)
        for fps in (30,60,120):
            self.camera.apply_presentation(initial);self.click('goal')
            for _ in range(round(.3*fps)):self.advance(1/fps)
            poses.append(self.camera.capture_presentation().position)
            self.focus.restore();self.advance()
            self.assertEqual(len(self.app.taskMgr.tasks),tasks)
        for pose in poses:
            for a,b in zip(pose,poses[0]):self.assertAlmostEqual(a,b,places=5)

    def test_exit_and_dispose_leave_no_highlights_or_camera_hook(self):
        self.click('goal');self.advance(.2)
        self.flow.show('levels')
        self.assertFalse(self.focus.has_focus);self.assertIsNone(self.focus._highlight)
        self.focus.dispose();self.focus.dispose();self.assertIsNone(self.camera.on_user_view_change)
