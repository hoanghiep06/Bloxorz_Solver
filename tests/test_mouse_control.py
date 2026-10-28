"""Mouse directions belong to the selected cube, independent of the other cube."""
import importlib.util
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from src.core.state import BloxorzState, Orientation
from src.gui.camera import fit_camera, project_point
from src.gui.contracts import BasicTileKind, StaticBoardData
from src.gui.mouse_control import controlled_cells, pick_action


class MouseControlTests(unittest.TestCase):
    def test_whole_block_keeps_its_full_footprint(self):
        for orientation in Orientation:
            state = BloxorzState(3, 3, orientation)
            self.assertEqual(controlled_cells(state), state.get_occupied_cells())

    def test_each_split_cube_has_its_own_input_footprint(self):
        for active in (0, 1):
            state = BloxorzState.create_split((2, 3), (6, 9), active)
            self.assertEqual(controlled_cells(state), [state.cubes[active]])
            self.assertEqual(state.get_occupied_cells(), [(2, 3), (6, 9)])

    def test_projected_clicks_in_all_directions_for_either_cube(self):
        from src.gui.controller import ACTION_TO_ROLL
        from src.gui.geometry_math import cell_to_world
        board = StaticBoardData(1, 'mouse', 'mouse', 9, 13,
            tuple((BasicTileKind.FLOOR,) * 13 for _ in range(9)), ())
        watcher = Mock()
        watcher.hasMouse.return_value = True
        app = SimpleNamespace(mouseWatcherNode=watcher)
        region = Mock()
        # A viewport offset from the window origin also exercises NDC conversion.
        region.getDimensions.return_value = (.2, .95, .1, .9)
        for size in ((1280, 720), (1024, 720), (1920, 1080)):
            fit = fit_camera(board, *size)
            for cubes in (((4, 5), (4, 9)), ((2, 4), (6, 4)), ((2, 3), (6, 9))):
                for active in (0, 1):
                    state = BloxorzState.create_split(*cubes, active)
                    x, y = cell_to_world(*cubes[active], rows=9, cols=13)
                    for action, direction in ACTION_TO_ROLL.items():
                        with self.subTest(size=size, cubes=cubes, active=active, action=action):
                            dx, dy, _ = direction.value
                            px, py, _ = project_point((x + dx * .6, y + dy * .6, .5), fit)
                            watcher.getMouse.return_value = (
                                2 * (.2 + (px + 1) / 2 * .75) - 1,
                                2 * (.1 + (py + 1) / 2 * .8) - 1)
                            self.assertEqual(pick_action(app, region, fit,
                                controlled_cells(state), 9, 13), action)


@unittest.skipUnless(importlib.util.find_spec('panda3d'), 'Panda3D required for arrows.')
class SplitArrowTests(unittest.TestCase):
    def test_arrow_positions_and_hover_follow_space_and_merge(self):
        from panda3d.core import NodePath
        from src.gui.move_arrows import MoveArrows
        from src.gui.geometry_math import cell_to_world
        from unittest.mock import patch
        from src.core.board import Board
        from pathlib import Path
        board = Board(str(Path(__file__).resolve().parent / 'fixtures/mechanics/level_11_advanced_sandbox.json'))
        controller = SimpleNamespace(board=board, state=BloxorzState.create_split((4, 5), (4, 9)),
            board_data=SimpleNamespace(rows=9, cols=13), session_id='arrows', revision=0)
        app = SimpleNamespace(render=NodePath('arrow-test'), pixel2d=NodePath('overlay-test'),
            mouseWatcherNode=Mock(), win=Mock(getXSize=lambda:1280, getYSize=lambda:720), taskMgr=Mock(),
            dashboard=SimpleNamespace(viewport=SimpleNamespace(region=Mock())),
            presentation=SimpleNamespace(camera=SimpleNamespace(current_fit=fit_camera(
                StaticBoardData(1,'arrow-fit','arrow-fit',9,13,
                    tuple((BasicTileKind.FLOOR,)*13 for _ in range(9)),()),1280,720))))
        app.dashboard.viewport.region.getDimensions.return_value=(0,1,0,1)
        arrows = MoveArrows(app, controller, lambda: True, enabled=True)
        self.addCleanup(app.render.removeNode)
        self.addCleanup(app.pixel2d.removeNode)
        self.addCleanup(arrows.dispose)
        task = SimpleNamespace(cont='cont')
        states = (controller.state, BloxorzState.create_split((4, 5), (4, 9), 1),
                  BloxorzState(4, 5, Orientation.HORIZONTAL))
        for revision, state in enumerate(states):
            controller.state, controller.revision = state, revision
            with patch('src.gui.move_arrows.pick_action', return_value='R') as pick:
                arrows._update(task)
                self.assertEqual(pick.call_args.args[3], controlled_cells(state))
            points = [cell_to_world(*cell, rows=9, cols=13) for cell in controlled_cells(state)]
            self.assertEqual(arrows._base['R'], (max(p[0] for p in points) + 1, points[0][1]))
            self.assertEqual(arrows._base['L'], (min(p[0] for p in points) - 1, points[0][1]))



@unittest.skipUnless(importlib.util.find_spec('panda3d'), 'Panda3D required.')
class VisibleArrowPickingTests(unittest.TestCase):
    def test_visible_arrow_centers_match_input_in_every_pose_and_camera(self):
        from panda3d.core import NodePath
        from src.gui.move_arrows import MoveAssistLayer
        from src.gui.camera import CameraConfig,SceneBounds
        from src.gui.geometry_math import cell_to_world
        states=[BloxorzState(4,5,o) for o in Orientation]
        states += [BloxorzState.create_split((2,7),(6,9),i) for i in (0,1)]
        controller=SimpleNamespace(state=states[0],board_data=SimpleNamespace(rows=9,cols=13))
        watcher=Mock();watcher.getOverRegion.return_value=None;watcher.hasMouse.return_value=True
        region=Mock();region.getDimensions.return_value=(0,1,0,1)
        app=SimpleNamespace(render=NodePath('arrows'),pixel2d=NodePath('labels'),taskMgr=Mock(),
            win=Mock(getXSize=lambda:1280,getYSize=lambda:720),mouseWatcherNode=watcher,
            dashboard=SimpleNamespace(viewport=SimpleNamespace(region=region)),
            presentation=SimpleNamespace(camera=SimpleNamespace(current_fit=None)))
        layer=MoveAssistLayer(app,controller,lambda:True,enabled=True)
        self.addCleanup(app.render.removeNode);self.addCleanup(app.pixel2d.removeNode);self.addCleanup(layer.dispose)
        board=StaticBoardData(1,'picking','picking',9,13,
            tuple((BasicTileKind.FLOOR,)*13 for _ in range(9)),())
        views=(CameraConfig(),CameraConfig(azimuth=0,elevation=88),CameraConfig(azimuth=-45,elevation=55))
        for state in states:
            controller.state=state;layer._place()
            points=[cell_to_world(*cell,rows=9,cols=13) for cell in controlled_cells(state)]
            x=sum(p[0] for p in points)/len(points);y=sum(p[1] for p in points)/len(points)
            for i,config in enumerate(views):
                bounds=SceneBounds((x-2.6,y-2.6,-.18),(x+2.6,y+2.6,2.3)) if i==2 else None
                fit=fit_camera(board,1280,720,config=config,bounds=bounds)
                app.presentation.camera.current_fit=fit
                for action in ('U','D','L','R'):
                    with self.subTest(pose=state,view=i,action=action):
                        px,py,_=project_point((*layer._present_arrow(action)[:2],.04),fit)
                        watcher.getMouse.return_value=(px,py)
                        self.assertEqual(layer._hover(),action)


if __name__ == '__main__':
    unittest.main()
