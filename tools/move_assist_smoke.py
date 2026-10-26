"""Native move-assist acceptance checks and framebuffer evidence.

Run: xvfb-run -a .venv/bin/python -B -m tools.move_assist_smoke
Uses a temporary profile. It does not alter production levels or saved progress.
"""
import argparse
import json
from pathlib import Path
import tempfile


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/bloxorz-assist-qa/manual'))
    args=parser.parse_args(argv);args.output.mkdir(parents=True,exist_ok=True)
    from panda3d.core import loadPrcFileData
    loadPrcFileData('assist-qa','audio-library-name null')
    from src.gui.game_app import create_game,dispose_game
    from src.gui.camera import project_point
    from src.gui.geometry_math import cell_to_world
    from src.gui.mouse_control import controlled_cells
    from src.gui.controller import ACTION_TO_ROLL,Replay
    from src.gui.move_assist import Severity
    from tools.native_input import NativeInput
    from tools.gui_stage3_6_smoke import _present,_resize
    report={'checks':[],'images':[],'input':'X11 XTest native keyboard and mouse'}
    with tempfile.TemporaryDirectory(prefix='assist-native-') as temp:
        app,renderer,c=create_game(save_path=Path(temp)/'save.json')
        driver=NativeInput(app);flow=app.game_flow;hud=app.dashboard.hud
        assist=flow.arrows
        def check(name):
            report['checks'].append(name);print('PASS',name,flush=True)
        def shot(name):
            driver.step(3)
            app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame()
            path=args.output/(name+'.png')
            assert app.win.saveScreenshot(str(path))
            report['images'].append(str(path))
        def idle():
            driver.wait(lambda:not c.manager.is_busy and c.phase!='SOLVING')
            driver.step(3)
            assert c.phase!='ERROR',c._status
        def enter(index=10,mode='keyboard',rate=4):
            flow.save.settings.control_mode=mode
            flow.start_level(index);driver.step(2)
            assert assist.root.isHidden()
            flow.intro.finish()
            c.set_speed(rate);driver.step(4)
        def hover(action):
            cells=controlled_cells(c.state)
            points=[cell_to_world(*cell,rows=c.board.rows,cols=c.board.cols) for cell in cells]
            x=sum(p[0] for p in points)/len(points);y=sum(p[1] for p in points)/len(points)
            dx,dy,_=ACTION_TO_ROLL[action].value
            fit=app.presentation.camera.current_fit
            px,py,_=project_point((x+dx*.8,y+dy*.8,.5),fit)
            left,right,bottom,top=app.dashboard.viewport.region.getDimensions()
            driver.pointer((left+(px+1)/2*(right-left))*app.win.getXSize(),
                           (1-bottom-(py+1)/2*(top-bottom))*app.win.getYSize())
            driver.step(3)
            assert assist._hover()==action,(action,assist._hover())
            assert assist._overlay.getNumChildren()>0
            assert assist.warning.node().getText()==assist.preview.for_action(action).message
        try:
            _present(app)
            for mode in ('keyboard','mouse'):
                for theme in ('light','dark'):
                    flow.show('settings');flow.screens['settings']._set_theme(theme)
                    for view in range(3):
                        enter(mode=mode);app.game_views.set_view(view);driver.step(12)
                        assert not assist.root.isHidden()
                        for action in ('U','D','L','R'):
                            hover(action)
                            node=assist._arrows[action][0]
                            px,py,_=project_point(tuple(node.getPos()),app.presentation.camera.current_fit)
                            left,right,bottom,top=app.dashboard.viewport.region.getDimensions()
                            driver.pointer((left+(px+1)/2*(right-left))*app.win.getXSize(),
                                           (1-bottom-(py+1)/2*(top-bottom))*app.win.getYSize())
                            assert assist._hover()==action,('visible arrow',action,assist._hover())
                        shot(f'{mode}-{theme}-view{view}')
                        for point in ((30,40),(app.win.getXSize()-100,75),
                                      (300,app.win.getYSize()-50)):
                            driver.pointer(*point);driver.step(3)
                            assert assist._hover() is None
                            assert assist._overlay.getNumChildren()==0
                        check(f'{mode}/{theme}/{app.game_views.spec.label}: four previews and HUD exclusion')
            enter()
            driver.click_widget(hud.buttons['Tutorial']);driver.step(3)
            assert app.game_tutorial.visible and assist.root.isHidden()
            shot('tutorial-move-assistance')
            driver.key('Escape');driver.step(3)
            assert not app.game_tutorial.visible and not assist.root.isHidden()
            check('Tutorial suppresses and restores manual assistance')
            for rate in (.25,1,4):
                enter(rate=rate)
                observed=[]
                driver.on_step=lambda: observed.append(assist.root.isHidden()) if c.manager.is_busy else None
                driver.key('Right')
                idle();driver.on_step=None
                assert observed and all(observed),observed
                assert c.moves==1 and not assist.root.isHidden()
                check(f'Native key at {rate}x: guide hidden until action completes')
            # Native mouse executes the red fragile warning rather than vetoing it.
            enter(mode='mouse')
            hover('D');driver.click();idle()
            hover('D')
            assert assist.preview.for_action('D').severity is Severity.DANGER
            assert assist.warning.node().getText()=='Fragile tile will break'
            shot('fragile-danger-before-click')
            driver.click();driver.wait(lambda:c.phase=='FELL')
            assert flow.screens['game'].result_visible and assist.root.isHidden()
            shot('fragile-danger-executed')
            _resize(app,(1100,760));driver.step(3)
            assert flow.screens['game'].result_visible and assist.root.isHidden()
            check('Red warning permits native click, falls, and result survives resize')
            _resize(app,(1280,720));enter(mode='mouse')
            for _ in range(2):hover('R');driver.click();idle()
            assert c.state.is_split()
            old=c.state.active_cube;driver.key('space');idle()
            assert c.state.active_cube!=old
            for active in (1,0):
                if c.state.active_cube!=active:
                    driver.key('space');idle()
                for view in range(3):
                    app.game_views.set_view(view);driver.step(12)
                    for action in ('U','D','L','R'):hover(action)
                    shot(f'selected-cube-{active}-view{view}')
            check('Space and three cameras keep previews on both selected cubes')
            # Native HUD buttons and Enter/P control multi-phase solution replay.
            enter(4,rate=.25)
            driver.click_widget(hud.buttons['Guide'])
            driver.click_widget(hud.buttons['BFS'])
            driver.click_widget(hud.buttons['Step'])
            driver.wait(lambda:c.moves==1 and not c.manager.is_busy)
            driver.step(3);assert assist.root.isHidden()
            driver.key('Return');driver.wait(lambda:c.manager.is_busy)
            driver.key('p');driver.step(3)
            assert c._mode is Replay.PAUSED
            pose=c.manager.current_visual_poses;driver.step(15)
            assert c.manager.current_visual_poses==pose and assist.root.isHidden()
            driver.click_widget(hud.buttons['Step']);idle()
            assert c.moves==2 and c.state.is_split() and c._mode is Replay.PAUSED,(c.moves,c.state,c._mode)
            shot('split-step-paused-no-guide')
            check('Native replay Pause holds pose; Step completes one multi-phase split action')
            driver.click_widget(hud.buttons['Guide']);driver.step(3)
            assert c.moves==0 and not c.manager.is_busy and not assist.root.isHidden()
            _resize(app,(800,600));driver.step(3)
            assert assist.root.isHidden() and assist.warning.isHidden()
            _resize(app,(1280,720));driver.step(3)
            assert not assist.root.isHidden()
            check('Cancel replay and unsupported-size fallback restore cleanly')
            # Cancel real Core action phases via restart, level replacement,
            # and the native Exit button, before a result dialog can be emitted.
            from src.gui.animation_contracts import EventKind
            from src.solvers.bfs import BFSSolver
            for effect in ('fragile','fall','split','goal'):
                for cancel in ('restart','level','exit'):
                    enter(0 if effect=='goal' else 10,mode='mouse')
                    app.game_views.set_view(0);driver.step(5)
                    prefix = ('D',) if effect=='fragile' else ('R',) if effect=='split' else ()
                    trigger = 'D' if effect=='fragile' else 'R' if effect=='split' else 'L'
                    if effect=='goal':
                        actions=BFSSolver(c.board).solve().actions
                        prefix,trigger=actions[:-1],actions[-1]
                    for action in prefix:
                        hover(action);driver.click();idle()
                    c.set_speed(.25);hover(trigger);driver.click()
                    expected=EventKind.SPLIT if effect=='split' else (
                        EventKind.GOAL_COMPLETE if effect=='goal' else EventKind.FALL)
                    driver.wait(lambda:c.manager.is_busy and c.manager.progress>.12
                        and any(e.kind is expected for e in c.manager._request.events))
                    assert not flow.screens['game'].result_visible
                    old=c.manager
                    if cancel=='restart':driver.click_widget(hud.buttons['Restart'])
                    elif cancel=='exit':driver.click_widget(hud.buttons['Exit'])
                    else:flow.start_level(0);flow.intro.finish()
                    driver.step(5)
                    assert not c.manager.is_busy and c.moves==0
                    assert not flow.screens['game'].result_visible
                    assert c.manager.terminal_outcome is None
                    if cancel=='level':assert old._rig.root.isEmpty()
                    if cancel=='exit':assert flow.name=='levels' and assist.root.isHidden()
                    check(f'{effect}: {cancel} mid-effect leaves no terminal or result')
            # Stable pools through repeated restart/move/cancel cycles.
            enter(rate=.25)
            hover('R');driver.pointer(600,350);driver.step(3)
            baseline=len(app.taskMgr.getTasks())
            for _ in range(10):
                driver.key('Right');driver.step(2);driver.key('r');driver.step(3)
                assert not c.manager.is_busy and c.moves==0
            assert len(app.taskMgr.getTasks())==baseline
            check('Ten native mid-animation restarts retain task count')
            report['status']='PASS'
        except BaseException:
            shot('FAILURE')
            report['status']='FAIL'
            raise
        finally:
            (args.output/'report.json').write_text(json.dumps(report,indent=2))
            driver.close();dispose_game(app,renderer,c)
    print(json.dumps({'status':report['status'],'checks':len(report['checks']),
                      'evidence':str(args.output)}),flush=True)


if __name__=='__main__':main()
