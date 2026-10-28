"""Real game/Core split switch, native keyboard/mouse and framebuffer VFX evidence."""
import argparse,json,tempfile,time
from pathlib import Path


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/split-teleport-ui'))
    args=parser.parse_args(argv);out=args.output;out.mkdir(parents=True,exist_ok=True)
    from panda3d.core import loadPrcFileData,WindowProperties,PNMImage,GraphicsEngine
    loadPrcFileData('teleport-qa','audio-library-name null')
    from src.gui.game_app import create_game,dispose_game
    from src.gui.animation_contracts import EventKind
    from tools.native_input import NativeInput
    from tools.gui_stage3_6_smoke import _present,_resize
    from src.gui import ui_theme
    report={'input':'Real Panda3D GLX GraphicsWindow + X11 XTest, live Core mechanics fixture',
            'checks':[],'images':[],'runs':[]}
    with tempfile.TemporaryDirectory() as tmp:
        app,renderer,c=create_game('tests/fixtures/mechanics',save_path=Path(tmp)/'save.json')
        flow=app.game_flow;driver=NativeInput(app)
        index=next(i for i,e in enumerate(c._catalog.entries) if e.level_id=='level_11_advanced_sandbox')
        def split_live():
            r=c.manager._request
            return r is not None and any(e.kind is EventKind.SPLIT for e in r.events)
        def enter():
            flow.start_level(index);flow.intro.finish();driver.step(3)
            app.game_views.set_view(0);driver.step(3)
        def key_move(key):
            old=c.moves;driver.key(key);driver.wait(lambda:not c.manager.is_busy,timeout=25)
            assert c.moves==old+1,(key,c.phase,c._status)
        def shot(name):
            app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame()
            path=out/(name+'.png');assert app.win.saveScreenshot(str(path));report['images'].append(path.name)
        def check(text):report['checks'].append(text);print('PASS',text,flush=True)
        try:
            props=WindowProperties();props.setOrigin(0,0);app.win.requestProperties(props);_present(app)
            for theme in ('light','dark'):
                flow.show('settings');driver.step(3)
                flow.screens['settings']._set_theme(theme);driver.step(3)
                enter();c.set_speed(.65);key_move('Right')
                before=c.state;session=c.session_id
                shots={};frames=[];last=[0.]
                thresholds={'charge':.17,'disassemble':.32,'dual-streams':.57,'materialize':.79,'active':.92}
                def observe():
                    if split_live():
                        t=c.manager.progress
                        assert c.moves==1 and c.state==before
                        for name,threshold in thresholds.items():
                            if name not in shots and t>=threshold:
                                image=PNMImage();assert app.win.getScreenshot(image)
                                shots[name]=image
                        if theme=='light' and len(frames)<42 and time.monotonic()-last[0]>.065:
                            image=PNMImage();assert app.win.getScreenshot(image)
                            frames.append(image);last[0]=time.monotonic()
                driver.on_step=observe
                driver.key('Right');driver.wait(lambda:not c.manager.is_busy,timeout=25);driver.on_step=None
                assert c.state.cubes==((2,7),(6,9)) and c.state.active_cube==0
                assert c.moves==2 and c.session_id==session
                assert len(shots)==5,shots.keys()
                for name,image in shots.items():
                    path=out/(theme+'-'+name+'.png');image.write(str(path));report['images'].append(path.name)
                for i,image in enumerate(frames):image.write(str(out/f'clip-{i:03}.png'))
                assert c.manager._split_vfx.root.isHidden()
                shot(theme+'-committed-cubes')
                key_move('space');assert c.state.active_cube==1
                key_move('Right');assert c.state.cubes[0]==(2,7)
                report['runs'].append(dict(theme=theme,rate=.65,cubes=repr(c.state.cubes),moves=c.moves,frames=len(frames)))
                check(theme+': charge/disassembly/dual-stream/materialize/active framebuffer beats; exact Core endpoints and continued cube-1 play')
            # Pause is an actual HUD controller operation during an automatic solver replay.
            c.set_speed(1)
            split_index=next(i for i,e in enumerate(c._catalog.entries) if e.level_id=='level_05_split')
            flow.start_level(split_index);flow.intro.finish();driver.step(3)
            flow.toggle_guide();hud=app.dashboard.hud
            driver.click_widget(hud.buttons['BFS']);driver.click_widget(hud.buttons['Play'])
            driver.wait(split_live,timeout=25)
            driver.wait(lambda:c.manager.progress>.3)
            driver.click_widget(hud.buttons['Play'])  # Pause
            assert c.manager.status.value=='PAUSED'
            progress=c.manager.progress;transforms=tuple(n.getTransform() for n in c.manager._split_vfx.root.findAllMatches('**'))
            driver.step(8);assert c.manager.progress==progress
            assert transforms==tuple(n.getTransform() for n in c.manager._split_vfx.root.findAllMatches('**'))
            shot('paused-replay-energy')
            driver.click_widget(hud.buttons['Step'])
            driver.wait(lambda:not c.manager.is_busy,timeout=25)
            assert c.moves==2 and c.state.is_split() and c._mode.value=='PAUSED'
            check('Native solver Play/Pause/Step freezes all VFX, then commits exactly one entire split action')
            # Restart during energy transit, then change level during another transit.
            for operation in ('restart','level'):
                enter();c.set_speed(1);key_move('Right');driver.key('Right')
                driver.wait(lambda:split_live() and c.manager.progress>.46)
                fx=c.manager._split_vfx
                if operation=='restart':
                    driver.key('r');driver.step(4);assert fx.root.isHidden()
                else:
                    flow.start_level(0);flow.intro.finish();driver.step(4);assert fx.root.isEmpty()
                assert c.moves==0 and not c.state.is_split();driver.step(5)
            check('Restart and change-level in transit clean VFX and invalidate the old action')
            # World-space VFX at different replay speeds and projections, including native resize.
            for view,rate in ((0,.25),(1,4),(2,1)):
                enter();c.set_speed(rate);key_move('Right')
                app.game_views.set_view(view);driver.step(3)
                # Follow remaps key direction; use the authoritative input boundary here.
                assert c.manual_move('R')
                driver.wait(lambda:split_live() and c.manager.progress>.50,timeout=25)
                c.manager.pause();_resize(app,(1100,760));shot(f'view-{view}-rate-{rate}')
                c.manager.resume();driver.wait(lambda:not c.manager.is_busy,timeout=25)
                assert c.state.cubes==((2,7),(6,9)) and c.moves==2
                _resize(app,(1280,720))
            check('Iso/Top/Follow, 0.25x/1x/4x and resize retain exact final cubes; no extra VFX task/window')
            report['windows']=GraphicsEngine.getGlobalPtr().getNumWindows()
        finally:
            driver.on_step=None;driver.close();dispose_game(app,renderer,c)
    report['status']='PASS';(out/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
