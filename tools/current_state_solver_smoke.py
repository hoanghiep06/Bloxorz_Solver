"""Actual Panda window + XTest input QA for solving from committed current state.

Run with xvfb-run -a .venv/bin/python -B -m tools.current_state_solver_smoke.
Only temporary fixture/save files are written; production levels stay unchanged.
"""
import argparse
import json
import shutil
import tempfile
import time
from pathlib import Path


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/current-state-ui'))
    args=parser.parse_args(argv);out=args.output;out.mkdir(parents=True,exist_ok=True)
    from panda3d.core import loadPrcFileData,PNMImage,WindowProperties
    loadPrcFileData('current-state-qa','audio-library-name null')
    from src.gui.game_app import create_game,dispose_game
    from src.gui.controller import SOLVER_SPECS,Replay
    from tools.native_input import NativeInput
    from tools.gui_stage3_6_smoke import _present
    report={'input':'X11 XTest mouse/keyboard on a real Panda3D GLX GraphicsWindow',
            'checks':[],'runs':[],'screenshots':[]}
    with tempfile.TemporaryDirectory() as tmp:
        fixtures=Path(tmp)/'levels';shutil.copytree('tests/fixtures/mechanics',fixtures)
        (fixtures/'level_12_no_solution.json').write_text(json.dumps({
            'name':'No Solution QA','grid':[[1,1,1,1,0,2]],'start':[0,0],'goal':[0,5]}))
        app,renderer,c=create_game(fixtures,save_path=Path(tmp)/'save.json')
        flow=app.game_flow;hud=app.dashboard.hud;driver=NativeInput(app)
        def check(text):report['checks'].append(text);print('PASS',text,flush=True)
        def shot(name):
            app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame()
            path=out/(name+'.png');assert app.win.saveScreenshot(str(path))
            report['screenshots'].append(str(path))
        def button(page,text):
            return next(w for w in flow.screens[page]._owned if hasattr(w,'dims') and w['text']==text)
        def enter(stem):
            index=next(i for i,e in enumerate(c._catalog.entries) if e.level_id==stem)
            flow.start_level(index);driver.step(3)
            flow.intro.finish();driver.step(3)
            assert c.input_enabled and c.moves==0
        def move(action):
            old=c.moves
            driver.key(dict(U='Up',D='Down',L='Left',R='Right',SPACE='space')[action])
            driver.wait(lambda:not c.manager.is_busy)
            assert c.moves==old+1,(action,c.phase,c.moves,c._status)
        def choose(name):
            if not hud.guide_open:driver.click_widget(hud.buttons['Guide'])
            driver.click_widget(hud.buttons[name]);assert c.selected==name,(name,c._status)
        def replay(name,prefix,stem,capture_images=False):
            enter(stem)
            for action in prefix:move(action)
            root=c.state;session=c.session_id;moves=c.moves
            poses=dict(c.manager.current_visual_poses);snapshot=c.manager.current_snapshot
            choose(name)
            assert c.state==root and c.moves==moves and c.session_id==session
            assert c.manager.current_snapshot==snapshot
            if capture_images:shot('basic-before-solve')
            solving_seen=[];commits=[];frames=[];sampled=[0.0]
            def observe():
                if c.phase=='SOLVING':
                    assert c.state==root and c.moves==moves and c.session_id==session
                    assert dict(c.manager.current_visual_poses)==poses
                    solving_seen.append(True)
                if not commits or commits[-1]!=c.moves:commits.append(c.moves)
                if (capture_images and c._mode is Replay.PLAYING and len(frames)<18
                        and time.monotonic()-sampled[0]>.12):
                    frame=PNMImage();assert app.win.getScreenshot(frame)
                    frames.append(frame);sampled[0]=time.monotonic()
            driver.on_step=observe
            try:
                driver.click_widget(hud.buttons['Step'])
                if c.phase=='SOLVING' and capture_images:shot('basic-solving-no-reset')
                driver.wait(lambda:c.phase!='SOLVING' and not c.manager.is_busy,timeout=20)
                assert solving_seen,'Async solving never observed'
                assert c.search.success,c._status
                assert c._solution_states[0]==root
                remaining=c.search.solution_length
                assert c.moves==moves+1
                if capture_images:shot('basic-first-step')
                driver.click_widget(hud.buttons['Play'])
                driver.wait(lambda:c.phase=='GOAL' and flow.screens['game'].result_visible,timeout=25)
                assert c.moves==moves+remaining
                assert c.session_id==session and c.board.is_goal(c.state)
                assert hud.model.move_count==moves+remaining and hud.model.solution_length==remaining
                assert commits==list(range(moves,moves+remaining+1)),commits
                if capture_images:
                    shot('basic-complete')
                    for i,frame in enumerate(frames):frame.write(str(out/f'replay-frame-{i:02}.png'))
                report['runs'].append(dict(solver=name,level=stem,root=repr(root),
                    manual_moves=moves,remaining=remaining,final_moves=c.moves,commits=commits))
            finally:driver.on_step=None
        try:
            wp=WindowProperties();wp.setOrigin(0,0);app.win.requestProperties(wp)
            _present(app);driver.pointer(500,300)
            driver.click_widget(button('main','Start'));assert flow.name=='levels'
            driver.click_widget(button('levels','1'));assert flow.name=='game'
            flow.intro.finish();driver.step(3)
            check('Native Main -> Start -> Level 1 navigation')
            replay('BFS',('R','L')*4+('R',),'level_01',True)
            check('BFS: 9 manual moves, horizontal root, stable pose during async solve, Step/Play, continuous Moves and final dialog')
            replay('A*',('R','R','D'),'level_01')
            check('A*: vertical current root and remaining-length HUD')
            c.set_speed(4)
            for name in SOLVER_SPECS:
                replay(name,('R','R'),'level_03_soft_bridge')
                replay(name,('R','R','SPACE'),'level_05_split')
            check('All six: changed bridge flags and split with cube-1 active, actual worker + native buttons + full animation replay')
            # Dark theme uses the same gameplay/worker flow.
            flow.show('settings');driver.step(3)
            driver.click_widget(button('settings','Dark'));driver.step(3)
            replay('A*',('R',),'level_01');shot('dark-current-state-complete')
            check('Dark theme A* from current horizontal pose')
            enter('level_12_no_solution');move('R');root=c.state;session=c.session_id
            choose('BFS');driver.click_widget(hud.buttons['Play'])
            driver.wait(lambda:c.phase!='SOLVING',timeout=20)
            assert 'NO SOLUTION' in c._status and c.state==root and c.moves==1
            assert c.session_id==session and not c.manager.is_busy
            shot('no-solution-preserved');move('L');assert c.moves==2
            driver.click_widget(hud.buttons['Restart']);driver.step(3)
            assert c.moves==0 and c.state==c.board.get_initial_state()
            check('No Solution retains state/pose/session, native manual input resumes; explicit Restart resets')
            enter('level_03_soft_bridge');move('R');choose('BFS')
            driver.click_widget(hud.buttons['Play'])
            # Closing during search or replay must retain progress at a committed boundary.
            driver.click_widget(hud.buttons['Guide'])
            driver.wait(lambda:not c.manager.is_busy)
            assert not c.guide_active and c._mode is Replay.IDLE and c.moves>=1
            previous=c.moves;driver.step(10);assert c.moves==previous
            check('Closing solver panel stops pending work/replay without rewinding manual progress')
            # Search cancellation via explicit restart while the deferred job is pending.
            enter('level_03_soft_bridge');move('R');choose('BFS')
            c.run_solver('BFS');assert c.phase=='SOLVING'
            driver.key('r');driver.wait(lambda:not c.manager.is_busy)
            driver.step(20);assert c.moves==0 and c.phase=='READY' and c.search is None
            check('Restart during search cancels/discards result and retains the new initial session')
        finally:
            driver.close();dispose_game(app,renderer,c)
    report['status']='PASS'
    (out/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print(json.dumps(report,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
