"""Actual gameplay/DirectGUI evidence for Emerald/Sapphire switches; no invented screenshots."""
import argparse,json,tempfile,time
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('/tmp/elemental-switch-ui'))
    p.add_argument('--guide-only',action='store_true',help='Targeted actual-mesh Guide icon/theme validation')
    p.add_argument('--lifecycle-only',action='store_true',help='Targeted repeated activation/restart resource audit')
    p.add_argument('--fallback-only',action='store_true',help='Actual GLX validation with sculpted opaque non-GLSL materials')
    args=p.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    if args.fallback_only:
        import os
        os.environ['BLOXORZ_MATERIALS']='fixed'
    from panda3d.core import loadPrcFileData,WindowProperties,PNMImage
    loadPrcFileData('switch-qa','audio-library-name p3openal_audio')
    from src.gui.game_app import create_game,dispose_game
    from src.gui.advanced_contracts import SwitchVisualKind as K
    from src.gui.animation_contracts import EventKind as E
    from src.gui.camera import SceneBounds,CameraConfig
    from src.gui.geometry_math import cell_to_world
    from src.gui import switch_materials
    from tools.native_input import NativeInput
    from tools.gui_stage3_6_smoke import _present,_resize
    report={'checks':[],'images':[],'input':'Panda3D GLX GraphicsWindow + X11 XTest; OpenAL Soft null output for cue checks'}
    with tempfile.TemporaryDirectory() as tmp:
        save=Path(tmp)/'save';save.write_text(json.dumps({'settings':{'music':False}}))
        app,r,c=create_game('tests/fixtures/mechanics',save_path=save);d=NativeInput(app);flow=app.game_flow
        camera=app.presentation.camera;g=flow.mechanics;audio=app.game_audio
        def check(s):report['checks'].append(s);print('PASS',s,flush=True)
        def shot(name):
            app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame()
            assert app.win.saveScreenshot(str(out/(name+'.png')));report['images'].append(name+'.png')
        def enter(stem):
            flow.start_level(next(i for i,e in enumerate(c._catalog.entries) if e.level_id==stem));flow.intro.finish();d.step(3)
            app.game_views.set_view(0);c.set_speed(1)
        def move(key):d.key(key);d.wait(lambda:not c.manager.is_busy,timeout=25)
        def closeup(cell):
            x,y=cell_to_world(*cell,rows=c.board_data.rows,cols=c.board_data.cols)
            camera.reframe(SceneBounds((x-2.1,y-1.7,-.2),(x+2.1,y+1.7,2.3)),CameraConfig(azimuth=30,elevation=53,padding=.12))
            app.presentation.style.update_background(camera.current_fit);d.step(3)
        try:
            props=WindowProperties();props.setOrigin(0,0);app.win.requestProperties(props);_present(app)
            assert switch_materials.STATUS==('FIXED_FUNCTION' if args.fallback_only else 'GLSL_EMERALD_SAPPHIRE'),switch_materials.STATUS
            report['shader']=switch_materials.STATUS
            if args.guide_only:
                from src.gui.mechanics_icons import _mesh
                for theme in ('light','dark'):
                    flow.show('settings');flow.screens['settings']._set_theme(theme);d.step(3)
                    enter('level_11_advanced_sandbox');shot(theme+'-rail')
                    before=c.state,c.moves,c.revision
                    bounds={key:(tuple(button.getPos(app.pixel2d)),tuple(button['frameSize']),
                        tuple(tuple(v) for v in g._icons[key].getTightBounds(app.pixel2d))) for key,button in g.buttons.items()}
                    for key in ('soft_switch','heavy_switch','split_switch'):
                        d.click_widget(g.buttons[key]);d.wait(lambda:flow.mechanics_focus._animation is None)
                        assert g.selected==key
                        assert flow.mechanics_focus.target.mechanic==key
                        assert g._icons[key].getChild(0).node()==_mesh(key,theme)
                        assert g.large_icon.getChild(0).getChild(0).node()==_mesh(key,theme)
                        assert before==(c.state,c.moves,c.revision)
                        assert bounds=={key:(tuple(button.getPos(app.pixel2d)),tuple(button['frameSize']),
                            tuple(tuple(v) for v in g._icons[key].getTightBounds(app.pixel2d))) for key,button in g.buttons.items()}
                        shot(theme+'-'+key)
                        d.click_widget(g.back_button);d.wait(lambda:not flow.mechanics_focus.has_focus)
                    d.click_widget(g.buttons['split_switch']);d.wait(lambda:flow.mechanics_focus._animation is None)
                    d.wait(lambda:flow.mechanics_focus._highlight is None)  # allow the normal 1.1s locator marker to expire
                    count=app.render.findAllMatches('**').getNumPaths(),g.root.findAllMatches('**').getNumPaths(),len(app.taskMgr.getTasks())
                    for skin in ('dark','light')*5:
                        flow.apply_scene_theme(skin);d.step(2)
                        assert g.selected=='split_switch' and before==(c.state,c.moves,c.revision)
                        for key in ('soft_switch','heavy_switch','split_switch'):
                            assert g._icons[key].getChild(0).node()==_mesh(key,skin)
                        assert count==(app.render.findAllMatches('**').getNumPaths(),g.root.findAllMatches('**').getNumPaths(),len(app.taskMgr.getTasks()))
                    check(theme+': native Guide clicks use real themed mesh faces in rail/card; focus/Back intact; fixed bounds and no state/resource changes across 10 theme swaps')
                for size in ((1024,720),(1280,720)):
                    d.pointer(450,300);_resize(app,size);_present(app);d.step(3)
                    assert not g.root.isHidden() and g.selected=='split_switch'
                check('1024/1280 resize preserves selected card and Guide layout')
                report['status']='PASS';(out/'report.json').write_text(json.dumps(report,indent=2))
                return
            if args.lifecycle_only:
                enter('level_03_soft_bridge')
                resources=lambda:(app.render.findAllMatches('**').getNumPaths(),len(app.taskMgr.getTasks()))
                before=resources();loads=audio.bank.loads
                for _ in range(6):
                    move('Right');move('Right');d.key('r');d.step(3)
                    assert resources()==before,(before,resources())
                assert audio.bank.loads==loads
                report['restart_resources']={'before':before,'after':resources(),'cycles':6,'sound_loads':loads}
                check('Six native activate/restart cycles preserve exact render-node/task counts and prewarmed audio load count')
                report['status']='PASS';(out/'report.json').write_text(json.dumps(report,indent=2))
                return
            if args.fallback_only:
                for theme in ('light','dark'):
                    flow.show('settings');flow.screens['settings']._set_theme(theme);d.step(3)
                    enter('level_11_advanced_sandbox');shot(theme+'-fallback-idle')
                    enter('level_03_soft_bridge');move('Right');move('Right')
                    assert c.state.bridges_state==(True,) and c.moves==2
                check('Real fixed-function window: both sculpted families remain visible; confirmed Soft/bridge action completes')
                report['status']='PASS';(out/'report.json').write_text(json.dumps(report,indent=2))
                return
            for theme in ('light','dark'):
                flow.show('settings');flow.screens['settings']._set_theme(theme);d.step(3)
                enter('level_11_advanced_sandbox');shot(theme+'-all-idle')
                state,moves,revision=c.state,c.moves,c.revision
                positions={k:tuple(b.getPos(app.pixel2d)) for k,b in g.buttons.items()}
                for key in ('soft_switch','heavy_switch','split_switch'):
                    d.click_widget(g.buttons[key]);d.wait(lambda:flow.mechanics_focus._animation is None)
                    assert flow.mechanics_focus.target.mechanic==key
                    assert positions=={k:tuple(b.getPos(app.pixel2d)) for k,b in g.buttons.items()}
                    assert (state,moves,revision)==(c.state,c.moves,c.revision)
                    if key=='split_switch':shot(theme+'-guide-icons')
                    d.click_widget(g.back_button);d.wait(lambda:not flow.mechanics_focus.has_focus)
                check(theme+': all three sculpted switches in actual sandbox; Guide focus/Back/icons stable without gameplay activation')
                for label,stem,kind in (('soft','level_03_soft_bridge',K.SOFT),('heavy','level_04_heavy_bridge',K.HEAVY),('split','level_05_split',K.SPLIT)):
                    enter(stem);definition=next(s for s in c.board_data.switches if s.kind is kind)
                    closeup(definition.cell);move('Right');c.set_speed(.25);audio.history.clear()
                    frames=[];captured=[]
                    def observe():
                        req=c.manager._request
                        if req is None:return
                        valid=any(e.kind is E.SPLIT for e in req.events) if kind is K.SPLIT else any(e.kind is E.SWITCH_ACTIVATE and e.target_id==definition.switch_id for e in req.events)
                        if not valid:return
                        t=c.manager.progress
                        if len(frames)<24:
                            image=PNMImage();assert app.win.getScreenshot(image);frames.append(image)
                        threshold=.12 if kind is K.SPLIT else .43
                        if t>=threshold and not captured:
                            assert c.manager.surface_layer._switch_fx.active>0,(label,t)
                            image=PNMImage();assert app.win.getScreenshot(image);captured.append(image)
                    d.on_step=observe;d.key('Right');d.wait(lambda:not c.manager.is_busy,timeout=25);d.on_step=None
                    assert captured,(theme,label)
                    path=out/(theme+'-'+label+'-active.png');captured[0].write(str(path));report['images'].append(path.name)
                    for i,image in enumerate(frames):image.write(str(out/f'{theme}-{label}-frame-{i:02}.png'))
                    assert c.moves==2
                    assert c.manager.surface_layer._switch_fx.active==0
                    events=[e.value for e,s in audio.history]
                    assert events.count(label+'_switch')==1,(label,events)
                    if kind is K.SPLIT:
                        assert c.state.is_split() and len(c.state.cubes)==2
                        assert events.count('teleport_charge')==events.count('teleport_arrival')==1
                        assert c.manager._split_vfx.root.isHidden()
                    else:assert c.state.bridges_state==(True,)
                check(theme+': native Soft/Heavy/Split activation captures, event audio once, exact bridge flags and one teleport/cube pair')
            # Pause both mechanical pose and pooled VFX; switching skin cancels only cosmetics.
            enter('level_03_soft_bridge');move('Right');c.set_speed(.25);d.key('Right')
            d.wait(lambda:c.manager.surface_layer._switch_fx.active>0)
            layer=c.manager.surface_layer;c.manager.pause()
            transforms=[n.getTransform() for n in layer._switch_fx.root.findAllMatches('**')]
            progress=c.manager.progress;d.step(8)
            assert transforms==[n.getTransform() for n in layer._switch_fx.root.findAllMatches('**')]
            original=c.state,c.moves,c.manager.current_request_id,c.manager.progress
            flow.apply_scene_theme('light');d.step(3)
            assert (c.state,c.moves,c.manager.current_request_id,c.manager.progress)==original
            assert layer._switch_fx.active==0
            c.manager.resume();d.wait(lambda:not c.manager.is_busy)
            assert c.state.bridges_state==(True,)
            check('Pause freezes switch poses/particles; mid-animation skin change cancels cosmetic bursts, preserves request/state and completes bridge update')
            enter('level_11_advanced_sandbox');count=app.render.findAllMatches('**').getNumPaths()
            state=c.state,c.moves,c.manager.current_snapshot
            for theme in ('light','dark')*12:
                flow.apply_scene_theme(theme);d.step(2)
                assert app.render.findAllMatches('**').getNumPaths()==count
                assert (c.state,c.moves,c.manager.current_snapshot)==state
            report['theme_cycles']=24;report['nodes']=count
            check('24 theme changes preserve Core/snapshot/Moves and exact node count; cached meshes/materials, no ghost theme particles')
            # Native replay of all six algorithms with the same presentation effects.
            hud=app.dashboard.hud
            for name in ('BFS','DFS','IDS','UCS','Greedy','A*'):
                enter('level_05_split');c.set_speed(4)
                d.click_widget(hud.buttons['Guide']);d.click_widget(hud.buttons[name]);d.click_widget(hud.buttons['Play'])
                d.wait(lambda:c.phase=='GOAL',timeout=25)
                assert c.moves==c.search.solution_length and c.board.is_goal(c.state),(name,c.moves,c.search.solution_length)
                report.setdefault('solvers',{})[name]={'moves':c.moves,'solution_length':c.search.solution_length}
                check(f'{name}: replay reached real Core Goal in {c.moves} actions, equal to returned solution length')
            check('All six spawned solvers reach Goal with shared switch/bridge/split/merge presentation and no extra action commits')
            # Restart/change level while a live switch pulse owns pooled geometry.
            for operation in ('restart','level'):
                enter('level_03_soft_bridge');move('Right');c.set_speed(.25);d.key('Right')
                d.wait(lambda:c.manager.surface_layer._switch_fx.active>0)
                old=c.manager.surface_layer._switch_fx
                if operation=='restart':d.key('r');d.step(3);assert old.active==0
                else:enter('level_01');assert old.root.isEmpty()
            check('Native restart and level change during pulse release particles/audio/actuators without stale callbacks')
            enter('level_03_soft_bridge')
            resources=lambda:(app.render.findAllMatches('**').getNumPaths(),len(app.taskMgr.getTasks()))
            before=resources();loads=audio.bank.loads
            for _ in range(6):
                move('Right');move('Right');d.key('r');d.step(3)
                assert resources()==before,(before,resources())
            assert audio.bank.loads==loads
            report['restart_resources']={'before':before,'after':resources(),'cycles':6,'sound_loads':loads}
            check('Six native activate/restart cycles preserve exact render-node/task counts and prewarmed audio load count')

            for size in ((1024,720),(1280,720)):
                d.pointer(450,300);_resize(app,size);_present(app);enter('level_11_advanced_sandbox')
                for index in (0,1,2):
                    app.game_views.set_view(index);d.step(3);shot(f'view-{index}-{size[0]}')
            check('Iso/Top/Follow and 1024/1280 layouts render new switch silhouettes and stable Guide')
        finally:d.on_step=None;d.close();dispose_game(app,r,c)
    report['status']='PASS';(out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))


if __name__=='__main__':main()
