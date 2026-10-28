"""Reported production poses + GUI-only fixes; Core rules stay authoritative."""
from pathlib import Path
import unittest
from game_integration_support import GameIntegrationCase
from src.gui.controller import LevelEntry
from src.gui.animation_contracts import AnimationKind,EventKind

ROOT=Path(__file__).resolve().parents[1]
FALL_CASES={'F1':('D','D',[(1,1),(2,1)]),
            'F2':('DUDRRDRRDL','L',[(4,5),(5,5)])}

class ReportedFallTests(GameIntegrationCase):
    def reported(self,name):
        path=ROOT/'levels/level_04.json'
        self.catalog.entries.append(LevelEntry(path.stem,path,path.stem))
        self.assertTrue(self.controller.load_level(len(self.catalog.entries)-1))
        route,action,cells=FALL_CASES[name]
        for move in route:self.move(move)
        c=self.controller
        self.assertEqual(c.state.get_occupied_cells(),cells)
        self.assertEqual(c.moves,len(route))
        outcome=c.board.describe_transition(c.state,action)
        self.assertIsNone(outcome.next_state);self.assertEqual(outcome.failure_reason,'fall')
        return action

    def test_f1_down_and_f2_left_emit_continuous_fall_in_production_controller(self):
        for name in FALL_CASES:
            with self.subTest(case=name):
                action=self.reported(name);c=self.controller;before=c.state;moves=c.moves
                initial=c.manager.current_visual_poses;self.events.clear()
                self.assertTrue(c.manual_move(action))
                m=c.manager
                self.assertEqual(m.current_visual_poses,initial)
                self.assertEqual(m._request.kind,AnimationKind.TERMINAL)
                self.assertEqual(m._request.terminal.kind,EventKind.FALL)
                self.assertEqual(m._fall.case,'roll-off')
                m.advance(.75)
                self.assertLess(dict(m.current_visual_poses)[None].center[2],-.5)
                self.assertFalse(m._rig._whole.isHidden())
                self.assertNotEqual(dict(m.current_visual_poses)[None].quaternion,dict(initial)[None].quaternion)
                self.assertEqual(c.phase,'READY')  # Result waits for terminal.
                self.drain();m.advance(1)
                self.assertEqual(c.phase,'FELL');self.assertEqual(self.events.count('fall'),1)
                self.assertIs(c.state,before);self.assertEqual(c.moves,moves)
                self.assertTrue(m._rig._whole.isHidden())
                self.assertFalse(m.renderer._actor_visuals_visible)

    def test_reported_falls_pause_restart_and_resync_without_stale_terminal(self):
        for name in FALL_CASES:
            for elapsed in (.1,.5,.85):
                action=self.reported(name);c=self.controller;self.events.clear()
                c.manual_move(action);c.manager.advance(elapsed)
                c.manager.pause();pose=c.manager.current_visual_poses
                c.manager.advance(2);self.assertEqual(c.manager.current_visual_poses,pose)
                c.manager.resume();c.restart_level();c.manager.advance(2)
                self.assertEqual(c.phase,'READY');self.assertFalse(c.manager.is_busy)
                self.assertIsNone(c.manager.terminal_outcome);self.assertNotIn('fall',self.events)
                self.assertFalse(c.manager._rig._whole.isHidden())

    def test_enclosed_hole_and_nonlosing_rejection_keep_their_existing_profiles(self):
        self.reported('F1');c=self.controller;c.restart_level()
        self.assertFalse(c.manual_move('SPACE'));self.assertFalse(c.manager.is_busy)
        self.assertIsNone(c.manager.terminal_outcome)
        for action in 'RDDRRDDDRR':self.move(action)
        self.assertTrue(c.manual_move('U'))
        self.assertEqual(c.manager._request.kind,AnimationKind.ROLL)
        self.drain();self.assertEqual(c.phase,'FELL')

class ToolbarAssetTests(unittest.TestCase):
    def test_supplied_robot_keeps_real_alpha_and_white_interior(self):
        from panda3d.core import PNMImage,Filename
        image=PNMImage();self.assertTrue(image.read(Filename.fromOsSpecific(str(ROOT/'assets/icons/ai-robot.png'))))
        self.assertTrue(image.hasAlpha());self.assertGreater(image.getYSize(),100)
        self.assertEqual(image.getAlpha(0,0),0)
        opaque_white=soft=0
        for y in range(image.getYSize()):
            for x in range(image.getXSize()):
                alpha=image.getAlpha(x,y)
                soft+=0<alpha<1
                opaque_white+=alpha==1 and min(image.getXel(x,y))>.85
        self.assertGreater(soft,100);self.assertGreater(opaque_white,1000)

    def test_toolbar_vectors_are_explicitly_antialiased_and_robot_is_aspect_correct(self):
        from panda3d.core import AntialiasAttrib
        from src.gui.icons import make_icon,make_robot_icon
        for name in ('exit','restart','view','help'):
            n=make_icon(name);self.addCleanup(n.removeNode)
            self.assertEqual(n.getAntialias(),AntialiasAttrib.MMultisample)
        robot=make_robot_icon();self.addCleanup(robot.removeNode)
        lo,hi=robot.getTightBounds()
        self.assertLess(hi.x-lo.x,hi.z-lo.z)
        self.assertEqual(robot.getTexture().getNumComponents(),4)
