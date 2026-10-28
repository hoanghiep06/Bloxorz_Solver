"""Actual DirectGUI clicks, definition-driven camera focus and live framebuffer QA."""
import argparse,json,tempfile,time
from pathlib import Path


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/mechanics-focus-ui'))
    args=parser.parse_args(argv);out=args.output;out.mkdir(parents=True,exist_ok=True)
    from panda3d.core import loadPrcFileData,WindowProperties,PNMImage
    loadPrcFileData('locator-qa','audio-library-name null')
    from src.gui.game_app import create_game,dispose_game
    from src.gui.mechanics_focus import mechanic_targets
    from src.gui.geometry_math import cell_to_world
    from src.gui.camera import project_point,CameraConfig
    from tools.native_input import NativeInput
    from tools.gui_stage3_6_smoke import _present,_resize
    report={'input':'Panda3D GLX GraphicsWindow; actual X11 XTest mouse/key input',
            'checks':[],'images':[],'targets':[]}
    with tempfile.TemporaryDirectory() as tmp:
        app,renderer,c=create_game('tests/fixtures/mechanics',save_path=Path(tmp)/'save.json')
        flow=app.game_flow;g=flow.mechanics;focus=flow.mechanics_focus;camera=app.presentation.camera
        driver=NativeInput(app)
        def check(text):report['checks'].append(text);print('PASS',text,flush=True)
        def shot(name):
            app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame()
            path=out/(name+'.png');assert app.win.saveScreenshot(str(path));report['images'].append(path.name)
        def enter(stem):
            index=next(i for i,e in enumerate(c._catalog.entries) if e.level_id==stem)
            flow.start_level(index);flow.intro.finish();driver.step(4)
        def click(key):
            driver.click_widget(g.buttons[key]);driver.wait(lambda:focus._animation is None)
        def back():
            driver.click_widget(g.back_button);driver.wait(lambda:not focus.has_focus)
        def verify_target():
            data=c.board_data;cell=focus.target.cell
            assert 0<=cell[0]<data.rows and 0<=cell[1]<data.cols
            x,y=cell_to_world(*cell,rows=data.rows,cols=data.cols,pitch=1.)
            nx,ny,depth=project_point((x,y,.06),camera.current_fit)
            vx,vy,vw,vh=focus._viewport();px,py=vx+(nx+1)*vw/2,vy+(1-ny)*vh/2
            sx,sy,sw,sh=focus._safe_area()
            assert sx<=px<=sx+sw and sy<=py<=sy+sh,(px,py,focus._safe_area())
            assert px<g.layout.card.x
            report['targets'].append(dict(mechanic=focus.target.mechanic,cell=cell,pixel=(px,py)))
        def rail_positions():return {key:tuple(b.getPos(app.pixel2d)) for key,b in g.buttons.items()}
        try:
            wp=WindowProperties();wp.setOrigin(0,0);app.win.requestProperties(wp);_present(app)
            for theme in ('light','dark'):
                flow.show('settings');driver.step(3)
                flow.screens['settings']._set_theme(theme);driver.step(3)
                enter('level_11_advanced_sandbox');start=camera.capture_presentation()
                original=(c.state,c.moves,c.session_id,c.revision,c.manager.current_snapshot)
                rail=rail_positions();shot(theme+'-before-focus')
                frames=[];sampled=[0.]
                def observe():
                    if theme=='light' and focus._animation and len(frames)<30 and time.monotonic()-sampled[0]>.04:
                        image=PNMImage();assert app.win.getScreenshot(image);frames.append(image);sampled[0]=time.monotonic()
                driver.on_step=observe
                click('goal');verify_target();shot(theme+'-goal-focused')
                back();driver.on_step=None
                assert camera.capture_presentation()==start
                for i,image in enumerate(frames):image.write(str(out/f'clip-{i:03}.png'))
                for key in ('bridge','soft_switch','heavy_switch','split_switch','fragile','void'):
                    click(key);verify_target()
                    assert rail_positions()==rail
                    shot(theme+'-'+key+'-focused')
                    if key=='bridge':
                        from src.gui.mechanics_focus import target_status
                        status=target_status(focus.target,c.manager.current_snapshot)
                        assert ('Currently inactive' in g.locator['text'])==(status=='Currently inactive')
                    if key=='fragile':
                        targets=mechanic_targets(c.board_data,key)
                        click(key);assert focus.target==targets[1];verify_target()
                        assert '2 /' in g.locator['text']
                    back();assert camera.capture_presentation()==start
                assert (c.state,c.moves,c.session_id,c.revision,c.manager.current_snapshot)==original
                # X must animate back, not leave the camera leased.
                click('goal');driver.click_widget(g.close_button)
                driver.wait(lambda:not focus.has_focus)
                assert camera.capture_presentation()==start
                check(theme+': seven mesh-matching icons, exact safe targets, stable rail, cycling, Back/X restore and unchanged Core/Moves')
            # A floor/Goal-only level: nonexistent mechanic opens information only.
            enter('level_01');start=camera.capture_presentation()
            click('split_switch');assert 'Not present' in g.locator['text']
            assert not focus.has_focus and focus._highlight is None and camera.capture_presentation()==start
            shot('absent-split-information-only')
            click('goal');verify_target();back()
            check('Basic level: Goal focus works; absent Split opens card without moving camera/creating a marker')
            enter('level_03_soft_bridge');before=c.manager.current_snapshot
            click('bridge');verify_target();shot('inactive-bridge-outline-only')
            assert c.manager.current_snapshot==before and c.state.bridges_state==(False,)
            back()
            driver.key('Right');driver.wait(lambda:not c.manager.is_busy)
            driver.key('Right');driver.wait(lambda:not c.manager.is_busy)
            assert c.state.bridges_state==(True,)
            click('bridge');verify_target();assert 'Currently inactive' not in g.locator['text'];back()
            check('Bridge absent/present both locate definition; focus does not open platforms or toggle state')
            enter('level_07_fragile_detour');click('fragile');verify_target();back()
            click('split_switch');assert 'Not present' in g.locator['text']
            check('Fragile level focuses real tile; level without Split has no phantom target')
            # Custom angle and actual C key camera takeover.
            g.close_card();camera.configure(CameraConfig(azimuth=137,elevation=50));start=camera.capture_presentation()
            click('goal');back();assert camera.capture_presentation()==start
            click('goal');driver.key('c');driver.step(5)
            assert not focus.has_focus and app.game_views._presentation_owner is None
            pose=tuple(app.camera.getQuat());driver.step(8);assert tuple(app.camera.getQuat())==pose
            check('Rotated camera restores exactly; native C takes ownership and cancels Guide movement')
            # Click during a real roll: card still opens, camera does not claim it.
            enter('level_01');c.set_speed(.25);driver.key('Right')
            assert c.manager.is_busy
            driver.click_widget(g.buttons['goal']);assert g.selected=='goal'
            assert not focus.has_focus and 'unavailable' in g.locator['text']
            driver.wait(lambda:not c.manager.is_busy);c.set_speed(1)
            check('Guide click during live roll opens help, rejects focus and preserves the gameplay action')
            # Restart / change level / resize clean up stale state and markers.
            click('goal');driver.key('r');driver.step(4)
            assert not focus.has_focus and focus._highlight is None and not focus._indices
            click('goal');enter('level_03_soft_bridge')
            assert not focus.has_focus and focus._highlight is None and g.selected is None
            for size in ((1024,720),(1366,768),(1920,1080),(1280,720)):
                driver.pointer(450,300);_resize(app,size);_present(app);driver.step(3)
                driver.pointer(size[0]/2,size[1]/2);click('bridge');verify_target()
                positions=rail_positions();driver.click_widget(g.buttons['bridge'])
                driver.wait(lambda:focus._animation is None);assert rail_positions()==positions
                back();driver.wait(lambda:focus._highlight is None)
            check('Restart, level changes and four sizes clear/renew context safely, with no rail shifts or ghost highlights')
            # Six real spawned solvers: Guide stays information-only throughout replay.
            hud=app.dashboard.hud
            for name in ('BFS','DFS','IDS','UCS','Greedy','A*'):
                enter('level_03_soft_bridge');c.set_speed(.5)
                driver.click_widget(hud.buttons['Guide']);driver.click_widget(hud.buttons[name])
                driver.click_widget(hud.buttons['Play'])
                driver.click_widget(g.buttons['bridge'])
                assert not focus.has_focus and 'unavailable' in g.locator['text']
                driver.wait(lambda:c.phase=='GOAL' and flow.screens['game'].result_visible,timeout=25)
                assert c.moves==4 and c.board.is_goal(c.state)
            check('Six spawned solvers reach Goal; Guide focus rejected during search/replay without changing roots/Moves')
            for theme in ('light','dark'):
                flow.show('settings');driver.step(3)
                flow.screens['settings']._set_theme(theme);driver.step(3)
                enter('level_01');click('split_switch')
                assert 'Not present' in g.locator['text'] and not focus.has_focus
                shot(theme+'-basic-no-split');click('goal');verify_target();back()
                enter('level_03_soft_bridge');click('bridge');verify_target()
                assert 'Currently inactive' in g.locator['text'];shot(theme+'-inactive-bridge');back()
                enter('level_07_fragile_detour');click('fragile');verify_target()
                shot(theme+'-fragile-level');back()
                check(theme+': basic Goal/absent Split, inactive Bridge and Fragile levels validated separately')
        finally:
            driver.on_step=None;driver.close();dispose_game(app,renderer,c)
    report['status']='PASS';(out/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
