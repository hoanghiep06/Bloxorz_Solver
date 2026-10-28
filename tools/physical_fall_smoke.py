"""Real Controller/Core losing actions, deterministic sampling + native input QA.

Framebuffers are real. Manual API drives known reachable paths, never synthetic
Core states. A separate native key run checks the real keyboard/clock pipeline.
"""
import argparse,json,tempfile,subprocess
from pathlib import Path

CASES={
 'edge':('level_01.json',(),'U'),
 'partial':('level_01.json',(),'D'),
 'interior':('level_04.json',('R','D','D','R','R','D','D','D','R','R'),'U'),
 'confined':('level_04.json',('D','R','R','D','R','U','R','R','R'),'D'),
 'fragile':('level_05.json',('R',),'R'),
 'split':('level_15.json',('D','R','R','U','L','D','R'),'U'),
}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/physical-fall'))
    parser.add_argument('--before',action='store_true')
    parser.add_argument('--native-only',action='store_true')
    args=parser.parse_args(argv);out=args.output;out.mkdir(parents=True,exist_ok=True)
    from panda3d.core import loadPrcFileData,GraphicsEngine,WindowProperties
    loadPrcFileData('fall-qa','audio-library-name null')
    from src.gui.game_app import create_game,dispose_game
    from tools.gui_stage3_6_smoke import _present
    from tools.native_input import NativeInput
    from direct.gui.DirectGuiBase import DirectGuiWidget
    from direct.showbase.MessengerGlobal import messenger
    from src.gui import ui_theme as ui
    class FallNativeInput(NativeInput):
        def pointer(self,x,y):
            # A real desktop may reject GraphicsWindow.movePointer while the
            # cursor is outside the client; XTest generates a real entry event.
            import ctypes as ct
            display=self.display;window=self.app.win.getWindowHandle().getIntHandle()
            self.x.XDefaultRootWindow.argtypes=[ct.c_void_p];self.x.XDefaultRootWindow.restype=ct.c_ulong
            self.x.XTranslateCoordinates.argtypes=[ct.c_void_p,ct.c_ulong,ct.c_ulong,ct.c_int,ct.c_int,
                ct.POINTER(ct.c_int),ct.POINTER(ct.c_int),ct.POINTER(ct.c_ulong)]
            rx,ry,child=ct.c_int(),ct.c_int(),ct.c_ulong()
            assert self.x.XTranslateCoordinates(display,window,self.x.XDefaultRootWindow(display),0,0,
                ct.byref(rx),ct.byref(ry),ct.byref(child))
            self.xt.XTestFakeMotionEvent.argtypes=[ct.c_void_p,ct.c_int,ct.c_int,ct.c_int,ct.c_ulong]
            self.xt.XTestFakeMotionEvent(display,-1,rx.value+round(x),ry.value+round(y),0)
            self.x.XFlush(display);self.step(4)
            target=(2*x/self.app.win.getXSize()-1,1-2*y/self.app.win.getYSize())
            try:
                self.wait(lambda:self.app.mouseWatcherNode.hasMouse() and
                    max(abs(self.app.mouseWatcherNode.getMouse()[i]-target[i]) for i in (0,1))<.01)
            except AssertionError:
                w=self.app.mouseWatcherNode;p=self.app.win.getPointer(0)
                print('POINTER DIAGNOSTIC',str(self.app.win.getProperties()),'root_origin',rx.value,ry.value,
                    'requested',x,y,'pointer',p.getX(),p.getY(),'watcher',w.hasMouse(),
                    tuple(w.getMouse()) if w.hasMouse() else None,'region',w.getDisplayRegion(),flush=True)
                raise
    report={'source' :'real Panda3D game; existing production levels; deterministic animation clock',
            'before':args.before,'cases':{},'checks':[]}
    with tempfile.TemporaryDirectory() as tmp:
        a,r,c=create_game(save_path=Path(tmp)/'save.json');d=FallNativeInput(a);flow=a.game_flow
        try:
            wp=WindowProperties();wp.setOrigin(0,0);a.win.requestProperties(wp)
            d.step(5)
            subprocess.run(['wmctrl','-ia',hex(a.win.getWindowHandle().getIntHandle())],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            _present(a)
            lookup={entry.path.name:i for i,entry in enumerate(c._catalog.entries)}
            def finish():
                for _ in range(12):
                    if not c.manager.is_busy:return
                    c.manager.advance(c.manager._request.duration)
                raise AssertionError('Unfinished action')
            def enter(name):
                filename,path,action=CASES[name]
                flow.start_level(lookup[filename]);flow.intro.finish();d.step(2)
                for move in path:
                    assert c.manual_move(move),(name,move,c.phase)
                    finish()
                return action
            def shot(path):
                # Sample the assist owner's visibility too on the baseline; do
                # not leave a READY-frame overlay cached over a paused timeline.
                if getattr(flow.arrows,'enabled',True):
                    from types import SimpleNamespace
                    flow.arrows._update(SimpleNamespace(cont='cont'))
                a.graphicsEngine.renderFrame();a.graphicsEngine.syncFrame()
                assert a.win.saveScreenshot(str(path))
            def counts():
                return {'nodes':a.scene_root.findAllMatches('**').getNumPaths() if not a.scene_root.isEmpty() else 0,
                    'tasks':len(a.taskMgr.getTasks())+len(a.taskMgr.getDoLaters()),
                    'widgets':len(DirectGuiWidget.guiDict),'outputs':GraphicsEngine.getGlobalPtr().getNumWindows()}
            for theme in (() if args.native_only else ('light','dark')):
                ui.set_theme(theme);flow.apply_scene_theme(theme);a.dashboard.hud.restyle();flow.ambient.set_theme(theme)
                for name in CASES:
                    action=enter(name);manager=c.manager
                    action_before=c.state;board_before=repr(vars(c.board));poses_before=dict(manager.current_visual_poses)
                    key=None if not c.state.is_split() else 'cube-'+str(c.state.active_cube)
                    frames=[];poses=[]
                    filename,path,_=CASES[name]
                    shot(out/f'{theme}-{name}-before.png')
                    assert c.manual_move(action),(name,action,c.phase)
                    for i in range(150):
                        request=manager._request
                        terminal=request is not None and request.terminal is not None
                        physical=getattr(manager,'_fall',None)
                        phase=(physical.sample(manager.progress*request.duration).phase if terminal and physical is not None
                               else 'old-fall' if terminal else 'roll/effects' if manager.is_busy else 'terminal')
                        p=dict(manager.current_visual_poses)
                        row={'time':i/60,'phase':phase,'request':manager.current_request_id,
                             'poses':{str(k):{'center':v.center,'quaternion':v.quaternion,'dimensions':v.nominal_dimensions} for k,v in p.items()},
                             'whole_hidden':manager._rig._whole.isHidden(),
                             'whole_alpha':manager._rig._whole.getColorScale().w}
                        poses.append(row)
                        if i%2==0 or not manager.is_busy:
                            f=out/f'{theme}-{name}-{i:03d}.png';shot(f);frames.append(str(f))
                        if not manager.is_busy:break
                        manager.advance(1/60)
                    assert c.phase=='FELL',(name,c.phase,c._status)
                    assert c.state==action_before and repr(vars(c.board))==board_before
                    if c.state.is_split():
                        other=next(k for k in poses_before if k!=key)
                        assert dict(manager.current_visual_poses)[other]==poses_before[other]
                    report['cases'][theme+'-'+name]={'level':filename,'path':path,'action':action,
                        'frames':frames,'samples':poses,'terminal':c.phase,'fall_kind':physical.case if physical else 'legacy'}
                report['checks'].append(theme+': 6 losing moves, Core unchanged; other split cube stays fixed')
            if not args.before:
                assert flow.arrows.root is None and flow.arrows._task is None
                assert not a.render.findAllMatches('**/MoveAssistLayer')
                assert not a.render.findAllMatches('**/Safety-*')
                assert not a.render.findAllMatches('**/MoveWarning')
                report['checks'].append('Default gameplay creates no assist nodes or updater task')
                # Real native key and real clock; guide/HUD survive and terminal
                # overlay arrives after the fall has finished, not before.
                ui.set_theme('light');flow.apply_scene_theme('light');a.dashboard.hud.restyle()
                enter('edge')
                g=flow.mechanics;g.show_mechanic('void')
                subprocess.run(['wmctrl','-ia',hex(a.win.getWindowHandle().getIntHandle())],
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                _present(a);d.pointer(500,300)
                assert c.input_enabled and c.keyboard_enabled,(c.input_enabled,c.keyboard_enabled)
                native_frames=[];native_states=[]
                def record_native():
                    if len(native_frames)<90:
                        f=out/f'native-clock-edge-{len(native_frames):03d}.png'
                        shot(f);native_frames.append(str(f))
                        native_states.append({'phase':c.phase,'request':c.manager.current_request_id,'progress':c.manager.progress})
                        (out/'native-states.json').write_text(json.dumps(native_states,indent=2))
                d.on_step=record_native
                d.key('Up');d.wait(lambda:c.phase=='FELL',timeout=25)
                d.on_step=None
                report['native_clock_frames']=native_frames
                assert not c.manager.is_busy and g.selected=='void' and not g.root.isHidden()
                assert flow.screens['game'].result_visible
                d.key('r');d.wait(lambda:c.phase=='READY')
                assert c.manager.terminal_outcome is None
                report['checks'].append('Native Up -> FALL -> result; R restarts; Mechanics Guide preserved')
                # Exercise normal mouse picking without creating debug arrows.
                from src.gui.camera import project_point
                from src.gui.geometry_math import cell_to_world
                from src.gui.mouse_control import controlled_cells
                flow.save.settings.control_mode='mouse'
                for view in range(3):
                    enter('edge');a.game_views.set_view(view);d.step(12)
                    points=[cell_to_world(*cell,rows=c.board.rows,cols=c.board.cols)
                            for cell in controlled_cells(c.state)]
                    x=sum(p[0] for p in points)/len(points);y=sum(p[1] for p in points)/len(points)
                    px,py,_=project_point((x,y+.8,.5),a.presentation.camera.current_fit)
                    left,right,bottom,top=a.dashboard.viewport.region.getDimensions()
                    d.pointer((left+(px+1)/2*(right-left))*a.win.getXSize(),
                              (1-bottom-(py+1)/2*(top-bottom))*a.win.getYSize())
                    d.click();d.wait(lambda:c.phase=='FELL')
                    assert flow.screens['game'].result_visible and flow.arrows.root is None
                    shot(out/f'native-mouse-view-{view}-result.png')
                    d.click_widget(a.dashboard.hud.buttons['Restart'])
                    d.wait(lambda:c.phase=='READY')
                    d.key('h');d.wait(lambda:a.game_tutorial.visible)
                    shot(out/f'native-mouse-view-{view}-tutorial.png')
                    d.key('h');d.wait(lambda:not a.game_tutorial.visible)
                flow.save.settings.control_mode='keyboard';a.game_views.set_view(0)
                report['checks'].append('Native mouse fall + HUD Restart + H tutorial in Iso/Top/Follow without assist')
                # Pause in tip/free fall and finite cancellations in real scenes.
                for name in ('edge','partial','interior','fragile','split'):
                    for fraction in (.08,.45,.85):
                        action=enter(name);assert c.manual_move(action)
                        c.manager.advance(c.manager._request.duration*fraction)
                        old=c.manager.current_visual_poses
                        c.manager.pause();c.manager.advance(10)
                        assert c.manager.current_visual_poses==old
                        c.manager.resume();c.restart_level();d.step(1)
                        assert c.phase=='READY' and not c.manager.is_busy and c.manager.terminal_outcome is None
                report['checks'].append('15 pause/resume/restart cases; no stale terminal or callbacks')
                enter('edge');d.wait(lambda:flow._par_job is None);baseline=counts()
                for _ in range(20):
                    assert c.manual_move('U');c.manager.advance(.65)
                    c.restart_level();d.step(1)
                after=counts();assert baseline==after,(baseline,after)
                report['resources_20_restarts']={'before':baseline,'after':after}
        finally:d.close();dispose_game(a,r,c)
        report['after_dispose']={'tasks':len(a.taskMgr.getTasks())+len(a.taskMgr.getDoLaters()),
            'widgets':len(DirectGuiWidget.guiDict),'outputs':GraphicsEngine.getGlobalPtr().getNumWindows(),
            'listeners':sum(len(messenger.whoAccepts(e) or {}) for e in messenger.getEvents())}
        assert all(v==0 for v in report['after_dispose'].values())
    report['status']='PASS'
    (out/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'status':'PASS','cases':len(report['cases']),'checks':report['checks'],'after_dispose':report['after_dispose']},indent=2))


if __name__=='__main__':main()
