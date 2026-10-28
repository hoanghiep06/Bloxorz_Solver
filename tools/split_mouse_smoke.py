"""Native mouse regression: independent split cubes, Space, arrows and rejoin.

Run with ``python -B -m tools.split_mouse_smoke``. Temporary levels/profile keep
production levels and player progress untouched; evidence is saved under /tmp.
"""
import argparse
import json
from pathlib import Path
import tempfile
import time


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/bloxorz-split-mouse-fixed'))
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    from panda3d.core import loadPrcFileData
    loadPrcFileData('split-mouse-qa', 'audio-library-name null')
    from src.gui.game_app import create_game, dispose_game, DEFAULT_LEVELS
    from src.gui.camera import project_point
    from src.gui.geometry_math import cell_to_world
    from src.gui.mouse_control import controlled_cells
    from src.gui.controller import ACTION_TO_ROLL
    from tools.gui_stage3_6_smoke import _present

    results = []
    layouts = (((4, 5), (4, 9)), ((2, 5), (6, 5)), ((2, 3), (6, 9)))
    with tempfile.TemporaryDirectory(prefix='split-mouse-qa-') as temporary:
        directory = Path(temporary)
        levels = directory / 'levels'
        levels.mkdir()
        for index, positions in enumerate(layouts):
            grid = [[1] * 13 for _ in range(9)]
            grid[4][3] = 6
            grid[8][12] = 2
            data = dict(grid=grid, start=[4, 0], goal=[8, 12],
                        split_switch=dict(cell=[4, 3], split_positions=positions))
            (levels / f'level_{index}.json').write_text(json.dumps(data))
        (levels / 'level_3.json').write_bytes((DEFAULT_LEVELS / 'level_05.json').read_bytes())
        app, renderer, controller = create_game(levels, save_path=directory / 'save.json')
        flow = app.game_flow
        try:
            def step():
                app.taskMgr.step()
                time.sleep(.002)

            def wait_idle():
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    step()
                    if controller.phase == 'ERROR':
                        raise AssertionError(controller._status)
                    if controller.is_idle:
                        return
                raise AssertionError('Animation did not finish.')

            def enter(index, active=0):
                flow.start_level(index)
                flow.intro.finish()
                controller.set_speed(4)
                for action in ('R', 'R'):
                    assert controller.manual_move(action)
                    wait_idle()
                assert controller.state.is_split()
                if active:
                    app.messenger.send('space')
                    wait_idle()
                assert controller.state.active_cube == active

            def mouse_move(action):
                _present(app)
                for _ in range(8):
                    step()
                before = controller.state
                fit = app.presentation.camera.current_fit
                points = [cell_to_world(*cell, rows=controller.board.rows, cols=controller.board.cols)
                          for cell in controlled_cells(before)]
                x = sum(p[0] for p in points) / len(points)
                y = sum(p[1] for p in points) / len(points)
                dx, dy, _ = ACTION_TO_ROLL[action].value
                px, py, _ = project_point((x + dx * .6, y + dy * .6, .5), fit)
                left, right, bottom, top = app.dashboard.viewport.region.getDimensions()
                sx = round((left + (px + 1) / 2 * (right - left)) * app.win.getXSize())
                sy = round((1 - bottom - (py + 1) / 2 * (top - bottom)) * app.win.getYSize())
                deadline = time.monotonic() + 5
                # movePointer success acknowledges the request, not delivery of
                # the native motion event. Wait until MouseWatcher sees it.
                target_mouse = (2 * sx / app.win.getXSize() - 1,
                                1 - 2 * sy / app.win.getYSize())
                while time.monotonic() < deadline:
                    if not app.win.getProperties().getForeground():
                        _present(app)
                    app.win.movePointer(0, sx, sy)
                    for _ in range(4):
                        step()
                    if app.mouseWatcherNode.hasMouse():
                        actual = app.mouseWatcherNode.getMouse()
                        if max(abs(actual[i] - target_mouse[i]) for i in (0, 1)) < .005:
                            break
                else:
                    pointer = app.win.getPointer(0)
                    raise AssertionError(('Native pointer motion event was not delivered.',
                        before, action, (sx, sy), (pointer.getX(), pointer.getY()),
                        tuple(app.mouseWatcherNode.getMouse()) if app.mouseWatcherNode.hasMouse() else None))
                assert flow.arrows._hover() == action, (before, action, flow.arrows._hover(),
                    (px, py), (sx, sy), tuple(app.mouseWatcherNode.getMouse()),
                    tuple(app.dashboard.viewport.region.getDimensions()),
                    (app.win.getXSize(), app.win.getYSize()))
                assert app.mouseWatcherNode.getOverRegion() is None
                expected = controller.board.transition(before, action)
                assert expected is not None
                app.messenger.send('mouse1')
                wait_idle()
                assert controller.state == expected, (action, before, controller.state, expected)
                return before, controller.state

            def screenshot(name):
                path = args.output / f'{name}.png'
                for _ in range(3):
                    step()  # Refresh arrows after the final animation commits.
                    app.graphicsEngine.renderFrame()
                app.graphicsEngine.syncFrame()
                assert app.win.saveScreenshot(str(path))

            _present(app)
            flow.save.settings.control_mode = 'mouse'
            for index, positions in enumerate(layouts):
                for active in (0, 1):
                    for action in ACTION_TO_ROLL:
                        enter(index, active)
                        before, after = mouse_move(action)
                        assert after.is_split()
                        assert after.cubes[1-active] == before.cubes[1-active]
                        assert after.cubes[active] != before.cubes[active]
                        results.append(dict(layout=index, active=active, action=action, status='PASS'))
                        if index == 0 and action == 'R':
                            screenshot(f'cube-{active}-right')
            # Approach horizontally/vertically: merge only on the third step.
            for index, action, whole_action in ((0, 'L', 'R'), (1, 'U', 'D')):
                enter(index, 1)
                for _ in range(2):
                    mouse_move(action)
                    assert controller.state.is_split()
                mouse_move(action)
                assert not controller.state.is_split()
                screenshot(f'merged-layout-{index}')
                mouse_move(whole_action)
                assert not controller.state.is_split()
                assert [key for key, _ in controller.manager.current_visual_poses] == [None]
            # Original reported case: the cube at column 4 must move RIGHT to
            # column 5 and merge with column 6, rather than moving LEFT to 3.
            enter(3, 1)
            before, after = mouse_move('R')
            assert before.cubes[1] == (0, 4) and not after.is_split()
            assert (after.r, after.c) == (0, 5)
            screenshot('original-level-right-merge')
            results.append(dict(original_level_right_click='PASS', horizontal_merge='PASS',
                                vertical_merge='PASS', unified_movement='PASS'))
        finally:
            dispose_game(app, renderer, controller)
    (args.output / 'result.json').write_text(json.dumps(dict(status='PASS', checks=results), indent=2))
    print(json.dumps(dict(status='PASS', independent_mouse_moves=24, merge_checks=3,
                          output=str(args.output))))


if __name__ == '__main__':
    main()
