"""Native end-to-end game QA. Run with python -m tools.game_integration_smoke --all.

Uses real game callbacks, worker processes, keyboard messenger and frame clock.
No production save files are read/written. Evidence goes to /tmp by default.
"""
import argparse
import json
import tempfile
import time
from pathlib import Path


class DelayedSolver:
    """QA-only slow computation for checking that render/input stay responsive."""
    def __init__(self,board):
        self.board=board
    def solve(self):
        time.sleep(2)
        from src.solvers.bfs import BFSSolver
        return BFSSolver(self.board).solve()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all',action='store_true',help='All 10 levels x all 6 solvers.')
    parser.add_argument('--interactions-only',action='store_true',help='Skip repeated solver runs; check manual/UI lifecycle paths.')
    parser.add_argument('--output',type=Path,default=Path('/tmp/bloxorz-game-integration'))
    args=parser.parse_args(argv);args.output.mkdir(parents=True,exist_ok=True)
    from panda3d.core import loadPrcFileData,GraphicsEngine,GraphicsWindow
    loadPrcFileData('game-qa-silent','audio-library-name null')
    from direct.gui.DirectGuiBase import DirectGuiWidget
    from direct.showbase.MessengerGlobal import messenger
    from src.gui.game_app import create_game,dispose_game
    from src.gui.controller import SOLVER_SPECS,LevelEntry,Replay
    from src.solvers.bfs import BFSSolver
    from tools.gui_stage3_6_smoke import _present,_resize
    report={'solver_runs':[],'manual':{},'images':[],'observed_events':[]}
    observed=set();goals=[]
    with tempfile.TemporaryDirectory(prefix='game-native-qa-') as temp:
        app,renderer,c=create_game(save_path=Path(temp)/'save.json')
        original=c._on_event
        def on_event(event):
            if event=='goal':goals.append((c.search_name,c.moves,c.session_id))
            original(event)
        c._on_event=on_event
        flow,hud=app.game_flow,app.dashboard.hud
        def step():
            request=c.manager._request if c.manager else None
            if request is not None:
                observed.update(event.kind.value for event in request.events)
            app.taskMgr.step()
            time.sleep(.001)
        def wait_for(predicate,timeout=15):
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                step()
                if c.phase=='ERROR':raise AssertionError(c._status)
                if predicate():return
            raise AssertionError(f'Timed out: {c.phase}, {c._status}, index={c._index}, moves={c.moves}')
        def click(name):
            callback=hud.buttons[name]['command'];assert callable(callback),name
            callback()
        def enter(index):
            flow.start_level(index);flow.intro.finish()
            c.set_speed(4)
            assert flow.name=='game' and c.input_enabled
        def image(name):
            path=args.output/(name+'.png')
            deadline=time.monotonic()+3
            while True:
                for _ in range(3):app.graphicsEngine.renderFrame()
                app.graphicsEngine.syncFrame()
                if app.win.saveScreenshot(str(path)):break
                if time.monotonic()>=deadline:raise AssertionError('Native framebuffer was not ready for capture.')
                step()
                time.sleep(.01)
            report['images'].append(str(path))
        def stats():
            return {'widgets':len(DirectGuiWidget.guiDict),
                    'subscriptions':sum(len(messenger.whoAccepts(e) or {}) for e in messenger.getEvents())}
        def move_pointer(x,y):
            # Native focus/configure events are asynchronous, especially after
            # exercising the small-window fallback. Do not treat a WM delay as
            # an application input failure, and never fake the pointer position.
            _present(app)
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                if app.win.movePointer(0,x,y):
                    for _ in range(4):step()
                    return
                step()
                time.sleep(.01)
            raise AssertionError('Window manager did not accept native pointer movement.')
        try:
            assert isinstance(app.win,GraphicsWindow)
            _present(app);image('main-menu')
            indices=() if args.interactions_only else range(len(c._catalog)) if args.all else (2,4,5,9)
            for index in indices:
                for name in SOLVER_SPECS:
                    enter(index);hud.set_hint_ready(True);hud.set_guide_visible(True)
                    click(name);hud.speed['value']=4;hud.speed['command']()
                    before=len(goals);started=time.monotonic();click('Play')
                    wait_for(lambda:len(goals)>before,timeout=30)
                    assert len(goals)==before+1
                    expected=c.search.solution_length
                    assert goals[-1][1]==expected
                    wait_for(lambda:c.phase=='READY' and not c.guide_active)
                    assert c.search is not None
                    assert hud.metric_values[3]['text']==str(expected)
                    assert hud.metric_values[1]['text']!='—'
                    row={'level':c._catalog[index].level_id,'solver':name,
                         'moves':expected,'seconds':round(time.monotonic()-started,3),'status':'PASS'}
                    report['solver_runs'].append(row)
                    print(json.dumps(row),flush=True)
                    if index==5 and name=='A*':image('combined-astar-metrics')
            # Manual play through all mechanics, including the actual Space binding.
            for index in (1,2,3,4,5,7,9):
                enter(index)
                actions=BFSSolver(c.board).solve().actions
                for action in actions:
                    app.messenger.send({'U':'arrow_up','D':'arrow_down','L':'arrow_left',
                                        'R':'arrow_right','SPACE':'space'}[action])
                    wait_for(lambda:not c.manager.is_busy)
                    assert c.phase in ('READY','GOAL'),c._status
                    if c.state.is_split():image(f'manual-{index}-cube-{c.state.active_cube}')
                assert c.phase=='GOAL'
                assert c.moves==len(actions)
                report['manual'][c._catalog[index].level_id]='PASS'
            # Fragile break then fall at the attempted tile.
            enter(6)
            app.messenger.send('arrow_right');wait_for(lambda:not c.manager.is_busy)
            app.messenger.send('arrow_right')
            wait_for(lambda:c.phase=='FELL')
            assert c.manager.current_snapshot.broken_fragile_cells
            image('fragile-failed')
            report['manual']['fragile_break_fall']='PASS'
            # Toggle the bridge OFF and then attempt to roll onto the absent floor.
            enter(7)
            for action in ('R','R','L','R'):
                c.manual_move(action);wait_for(lambda:not c.manager.is_busy)
            assert c.state.bridges_state==(False,)
            image('bridge-closed')
            c.manual_move('R');wait_for(lambda:c.phase=='FELL')
            report['manual']['bridge_close_fall']='PASS'
            # Pause in the middle of an action; Step must finish that action only.
            enter(4);hud.set_guide_visible(True);click('BFS');click('Step')
            wait_for(lambda:c.search is not None and c.moves==1 and not c.manager.is_busy)
            c.set_speed(.25)  # Leave a reliable observation interval on real frame clocks.
            click('Play');wait_for(lambda:c.manager.is_busy and c.manager.progress>.05)
            click('Play');assert c._mode is Replay.PAUSED
            c.set_speed(4)
            click('Step');wait_for(lambda:not c.manager.is_busy)
            assert c.moves==2 and c.state.is_split() and c._mode is Replay.PAUSED,(c.moves,c.state,c._mode)
            image('split-step-paused')
            click('Close');assert c.moves==0 and not c.manager.is_busy
            report['manual']['pause_step_split_and_cancel']='PASS'
            # Resize: verify the actual native size and the fallback warning.
            report['resize']={}
            for size in ((1024,720),(800,600),(1280,720)):
                _resize(app,size)
                expected=size[0]>=1024 and size[1]>=720
                assert app.dashboard.viewport.layout.supported==expected
                assert app.dashboard.viewport.region.isActive()==expected
                assert hud.warning.isHidden()==expected
                report['resize'][str(size)]='PASS'
            # Warm menu widgets once; repeated rebuilds must not accumulate registrations.
            for _ in range(2):
                flow.show('settings');step();flow.show('main');step()
            baseline=stats()
            for _ in range(20):
                flow.show('settings');step();flow.show('main');step()
            after=stats();assert baseline==after,(baseline,after)
            report['menu_cycles']={'cycles':20,'before':baseline,'after':after,'status':'PASS'}
            flow.show('settings')
            flow.screens['settings']._set_theme('dark');step();image('settings-dark')
            flow.screens['settings']._set_mode('mouse')
            enter(4);assert not c.keyboard_enabled and flow._arrows_visible()
            report['manual']['theme_and_mouse_mode']='PASS'
            for action in ('R','R'):
                c.manual_move(action);wait_for(lambda:not c.manager.is_busy)
            app.messenger.send('space');wait_for(lambda:not c.manager.is_busy)
            assert c.state.is_split() and c.state.active_cube==1
            report['manual']['space_in_mouse_mode']='PASS'
            # Exercise actual native pointer projection and the UI click guard.
            move_pointer(45,40)
            wait_for(lambda:app.mouseWatcherNode.getOverRegion() is not None)
            old_moves=c.moves
            app.messenger.send('mouse1');step()
            assert c.moves==old_moves and not c.manager.is_busy
            report['manual']['mouse_over_hud_is_not_a_move']='PASS'
            enter(1)
            from src.gui.camera import project_point
            from src.gui.geometry_math import cell_to_world
            fit=app.presentation.camera.current_fit
            x,y=cell_to_world(c.state.r,c.state.c,rows=c.board.rows,cols=c.board.cols,pitch=1)
            px,py,_=project_point((x+1,y,.5),fit)
            left,right,bottom,top=app.dashboard.viewport.region.getDimensions()
            pointer_x=round((left+(px+1)/2*(right-left))*app.win.getXSize())
            pointer_y=round((1-(bottom+(py+1)/2*(top-bottom)))*app.win.getYSize())
            move_pointer(pointer_x,pointer_y)
            for _ in range(8):step()
            expected=c.board.transition(c.state,'R')
            app.messenger.send('mouse1')
            wait_for(lambda:not c.manager.is_busy)
            assert c.state==expected
            report['manual']['native_mouse_direction_projection']='PASS'
            c._solver_specs['QA slow']=('tools.game_integration_smoke','DelayedSolver')
            c.run_solver('QA slow')
            wait_for(lambda:c._job is not None)
            job=c._job;deadline=time.monotonic()+.15;frames=0
            while time.monotonic()<deadline:
                step();frames+=1
            assert frames>=3 and c.phase=='SOLVING'
            image('solver-working-ui-responsive')
            click('Restart')
            assert c.phase=='READY' and c._job is None and job._closed
            report['manual']['slow_solver_ui_responsive_and_restart_cancels']={'status':'PASS','frames':frames}
            report['observed_events']=sorted(observed)
        finally:
            dispose_game(app,renderer,c)
        report['after_dispose']={**stats(),'graphics_outputs':GraphicsEngine.getGlobalPtr().getNumWindows(),
                                 'tasks':len(app.taskMgr.getTasks())}
        assert all(value==0 for value in report['after_dispose'].values()),report['after_dispose']
    report['status']='PASS'
    (args.output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'status':'PASS','solver_runs':len(report['solver_runs']),
                      'after_dispose':report['after_dispose'],'evidence':str(args.output)}),flush=True)


if __name__=='__main__':main()
