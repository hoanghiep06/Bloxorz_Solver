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
        controller = SimpleNamespace(state=BloxorzState.create_split((4, 5), (4, 9)),
            board_data=SimpleNamespace(rows=9, cols=13), session_id='arrows', revision=0)
        app = SimpleNamespace(render=NodePath('arrow-test'), taskMgr=Mock(),
            dashboard=SimpleNamespace(viewport=SimpleNamespace(region=Mock())),
            presentation=SimpleNamespace(camera=SimpleNamespace(current_fit=Mock())))
        arrows = MoveArrows(app, controller, lambda: True)
        self.addCleanup(app.render.removeNode)
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


if __name__ == '__main__':
    unittest.main()
