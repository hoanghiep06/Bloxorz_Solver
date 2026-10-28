"""Real Core merge on sandbox, native input, five energy beats and lifecycle QA."""
import argparse,json,tempfile,time
from pathlib import Path


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/merge-teleport-ui'))
    args=parser.parse_args(argv);out=args.output;out.mkdir(parents=True,exist_ok=True)
    from panda3d.core import loadPrcFileData,WindowProperties,PNMImage,GraphicsEngine
    loadPrcFileData('merge-qa','audio-library-name null')
    from src.gui.game_app import create_game,dispose_game
    from src.gui.animation_contracts import EventKind
    from tools.native_input import NativeInput
    from tools.gui_stage3_6_smoke import _present,_resize
    report={'input':'Panda3D GLX GraphicsWindow + X11 XTest, existing mechanics fixtures',
            'checks':[],'images':[],'runs':[]}
    with tempfile.TemporaryDirectory() as tmp:
        app,renderer,c=create_game('tests/fixtures/mechanics',save_path=Path(tmp)/'save.json')
        flow=app.game_flow;driver=NativeInput(app)
        def enter(stem='level_11_advanced_sandbox'):
            index=next(i for i,e in enumerate(c._catalog.entries) if e.level_id==stem)
            flow.start_level(index);flow.intro.finish();driver.step(3)
            app.game_views.set_view(0);driver.step(3)
        def move(action):
            old=c.moves
            driver.key(dict(R='Right',L='Left',D='Down',U='Up',SPACE='space')[action])
            driver.wait(lambda:not c.manager.is_busy,timeout=25)
            assert c.moves==old+1,(action,c.phase,c._status)
        def live():
            r=c.manager._request
            return r is not None and any(e.kind is EventKind.MERGE for e in r.events)
        def prepare(orientation):
            enter();c.set_speed(4);move('R');move('R')
            path=('D','D','D','D','R') if orientation=='horizontal' else ('D','D','D','R','R')
            for action in path[:-1]:move(action)
            assert c.state.is_split()
            return path[-1]
        def shot(name):
            app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame()
            path=out/(name+'.png');assert app.win.saveScreenshot(str(path));report['images'].append(path.name)
        def check(text):report['checks'].append(text);print('PASS',text,flush=True)
        try:
            props=WindowProperties();props.setOrigin(0,0);app.win.requestProperties(props);_present(app)
            for theme in ('light','dark'):
                flow.show('settings');driver.step(3)
                flow.screens['settings']._set_theme(theme);driver.step(3)
                for orientation in ('horizontal','vertical'):
                    action=prepare(orientation);c.set_speed(.65)
                    old,moves,session=c.state,c.moves,c.session_id
                    expected=c.board.transition(old,action);assert expected and not expected.is_split()
                    pool=c.manager._split_vfx
                    snapshots={};frames=[];last=[0.]
                    thresholds={'charge':.12,'dissolve':.31,'converge':.55,'reconstruct':.76,'settle':.93}
                    def observe():
                        if live():
                            assert c.moves==moves and c.state==old
                            for name,threshold in thresholds.items():
                                if name not in snapshots and c.manager.progress>=threshold:
                                    image=PNMImage();assert app.win.getScreenshot(image);snapshots[name]=image
                            if theme=='light' and orientation=='horizontal' and len(frames)<40 and time.monotonic()-last[0]>.065:
                                image=PNMImage();assert app.win.getScreenshot(image);frames.append(image);last[0]=time.monotonic()
                    driver.on_step=observe;move(action);driver.on_step=None
                    assert c.state==expected and c.moves==moves+1 and c.session_id==session
                    assert c.manager._split_vfx is pool and pool.root.isHidden()
                    assert c.state.orientation.name.lower()==orientation
                    assert len(snapshots)==5,snapshots.keys()
                    for name,image in snapshots.items():
                        path=out/f'{theme}-{orientation}-{name}.png';image.write(str(path));report['images'].append(path.name)
                    for i,image in enumerate(frames):image.write(str(out/f'clip-{i:03}.png'))
                    shot(theme+'-'+orientation+'-whole')
                    # A supported next move must roll one whole actor with no cube indicator.
                    follow=next(a for a in c.board.get_actions(c.state) if c.board.transition(c.state,a) is not None)
                    c.set_speed(4);move(follow)
                    assert not c.state.is_split() and set(dict(c.manager.current_visual_poses))=={None}
                    report['runs'].append(dict(theme=theme,orientation=orientation,moves_before=moves,
                        moves_after_merge=moves+1,target=repr(expected),frames=len(frames)))
                check(theme+': five fusion beats on H/V Core merges, one commit, shared split pool and continued whole movement')
            # Native solver Pause/Step in the actual merge action (fixture forces split/merge).
            enter('level_05_split');c.set_speed(4);flow.toggle_guide();hud=app.dashboard.hud
            driver.click_widget(hud.buttons['BFS'])
            for target in (1,2,3):
                driver.click_widget(hud.buttons['Step'])
                driver.wait(lambda:c.moves==target and not c.manager.is_busy,timeout=25)
            c.set_speed(1);driver.click_widget(hud.buttons['Play'])
            driver.wait(lambda:live() and c.manager.progress>.30)
            driver.click_widget(hud.buttons['Play']);assert c.manager.status.value=='PAUSED'
            progress=c.manager.progress
            transforms=tuple(n.getTransform() for n in c.manager._split_vfx.root.findAllMatches('**'))
            driver.step(8);assert c.manager.progress==progress
            assert transforms==tuple(n.getTransform() for n in c.manager._split_vfx.root.findAllMatches('**'))
            shot('native-paused-merge')
            driver.click_widget(hud.buttons['Step']);driver.wait(lambda:not c.manager.is_busy)
            assert c.moves==4 and not c.state.is_split() and c._mode.value=='PAUSED'
            driver.click_widget(hud.buttons['Play'])
            driver.wait(lambda:c.phase=='GOAL' and flow.screens['game'].result_visible)
            assert c.moves==5
            check('Native solver Pause freezes fusion; Step completes exactly one merge; Play rolls whole to Goal')
            for operation in ('restart','level'):
                action=prepare('horizontal');c.set_speed(1);driver.key('Right')
                driver.wait(lambda:live() and c.manager.progress>.46)
                pool=c.manager._split_vfx
                if operation=='restart':driver.key('r');driver.step(4);assert pool.root.isHidden()
                else:flow.start_level(0);flow.intro.finish();driver.step(4);assert pool.root.isEmpty()
                assert c.moves==0 and not c.state.is_split();driver.step(4)
            check('Restart/change level during convergence clean VFX and discard stale commit')
            for view,rate in ((0,.25),(1,4),(2,1)):
                action=prepare('vertical');c.set_speed(rate);app.game_views.set_view(view);driver.step(3)
                # Follow remaps native movement, so call the same manual input boundary with world action.
                assert c.manual_move(action)
                driver.wait(lambda:live() and c.manager.progress>.5,timeout=25)
                c.manager.pause();_resize(app,(1100,760));shot(f'view-{view}-rate-{rate}')
                c.manager.resume();driver.wait(lambda:not c.manager.is_busy)
                assert not c.state.is_split() and c.moves==7
                _resize(app,(1280,720))
            check('Iso/Top/Follow, resize and 0.25x/1x/4x end in the same Core whole state')
            report['windows']=GraphicsEngine.getGlobalPtr().getNumWindows()
        finally:
            driver.on_step=None;driver.close();dispose_game(app,renderer,c)
    report['status']='PASS';(out/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
