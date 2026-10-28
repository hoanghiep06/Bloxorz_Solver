"""Production F1/F2 + fixed Guide bounds + toolbar native UI acceptance.

xvfb-run -a -s '-screen 0 2200x1400x24 +extension GLX' \
 .venv/bin/python -B -m tools.targeted_ui_smoke --output /tmp/targeted-ui
Temporary profile only. No level/Core mutation; native XTest keys/buttons.
"""
from pathlib import Path
import argparse,json,tempfile

CASES={'F1':('D','D'), 'F2':('DUDRRDRRDL','L')}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/targeted-ui'))
    parser.add_argument('--native-falls-only',action='store_true')
    args=parser.parse_args(argv);out=args.output;out.mkdir(parents=True,exist_ok=True)
    from panda3d.core import loadPrcFileData,WindowProperties,Point3,GraphicsEngine,PNMImage,Filename
    loadPrcFileData('targeted-qa','audio-library-name null')
    from direct.gui.DirectGuiBase import DirectGuiWidget
    from direct.showbase.MessengerGlobal import messenger
    from src.gui.game_app import create_game,dispose_game
    from src.gui import ui_theme as ui
    from tools.native_input import NativeInput
    from tools.gui_stage3_6_smoke import _present,_resize
    report={'checks':[],'falls':{},'input':'Real Panda3D GraphicsWindow + X11 XTest','bounds':[]}
    with tempfile.TemporaryDirectory() as tmp:
        a,r,c=create_game(save_path=Path(tmp)/'save.json');d=NativeInput(a);flow=a.game_flow
        g=flow.mechanics;hud=a.dashboard.hud
        def shot(name):
            a.graphicsEngine.renderFrame();a.graphicsEngine.syncFrame()
            p=out/(name+'.png');assert a.win.saveScreenshot(str(p));return str(p)
        def enter(index=3):
            flow.start_level(index);flow.intro.finish();a.game_views.set_view(0);d.step(3)
        def reach(label):
            enter()
            for action in CASES[label][0]:
                assert c.manual_move(action)
                while c.manager.is_busy:c.manager.advance(c.manager._request.duration)
            assert c.moves==len(CASES[label][0]);d.step(2)
        def resources():
            return {'nodes':a.scene_root.findAllMatches('**').getNumPaths(),
                'tasks':len(a.taskMgr.getTasks())+len(a.taskMgr.getDoLaters()),
                'widgets':len(DirectGuiWidget.guiDict),'outputs':GraphicsEngine.getGlobalPtr().getNumWindows()}
        def bounds():
            values=[]
            for key,b in g.buttons.items():
                icon=g._icons[key]
                values.append(tuple(b.getPos(a.pixel2d))+tuple(b['frameSize'])+
                    tuple(icon.getPos(a.pixel2d))+
                    tuple(x for point in icon.getTightBounds(a.pixel2d) for x in point))
            return values
        def stable(expected):
            actual=bounds();error=max(abs(x-y) for aa,bb in zip(expected,actual) for x,y in zip(aa,bb))
            assert error<=1.,error
            return error
        try:
            wp=WindowProperties();wp.setOrigin(0,0);a.win.requestProperties(wp);_present(a);d.pointer(500,300)
            for theme in ('dark','light'):
                ui.set_theme(theme);flow.apply_scene_theme(theme);hud.restyle()
                for label,(route,action) in CASES.items():
                    report['falls'][theme+'-'+label]={'route':route,'action':action}
                    if not args.native_falls_only:
                        reach(label);m=c.manager;initial=c.state;moves=c.moves
                        before=shot(theme+'-'+label+'-before');frames=[];samples=[]
                        assert c.manual_move(action);assert m._fall.case=='roll-off'
                        for i in range(55):
                            if i%2==0:frames.append(shot(theme+'-'+label+f'-{i:03d}'))
                            pose=dict(m.current_visual_poses)[None]
                            samples.append({'time':i/60,'center':pose.center,'quaternion':pose.quaternion,
                                'hidden':m._rig._whole.isHidden(),'alpha':m._rig._whole.getColorScale().w})
                            if m.is_busy:m.advance(1/60)
                        assert c.phase=='FELL' and c.state==initial and c.moves==moves
                        assert not m.is_busy and m._rig._whole.isHidden()
                        report['falls'][theme+'-'+label].update(before=before,frames=frames,samples=samples,end=c.phase)
                    # Repeat through real keyboard and the unmodified task clock.
                    reach(label);native=[];native_samples=[];actions=[];images=[]
                    original_move=c.manual_move
                    def traced_move(direction):
                        actions.append(direction);return original_move(direction)
                    c.manual_move=traced_move
                    def record():
                        if len(native)<100:
                            # Buffer real framebuffers; PNG encoding happens
                            # after completion so QA cannot stall the fall clock.
                            frame=PNMImage();assert a.win.getScreenshot(frame)
                            images.append(frame)
                            native.append(str(out/(theme+'-'+label+f'-native-{len(native):03d}.png')))
                            native_samples.append({'progress':c.manager.progress,'phase':c.phase})
                    d.on_step=record
                    d.key('Down' if action=='D' else 'Left');d.wait(lambda:c.phase=='FELL',timeout=25)
                    d.on_step=None;c.manual_move=original_move
                    assert actions==[action],actions
                    assert flow.screens['game'].result_visible
                    for frame,path in zip(images,native):assert frame.write(Filename.fromOsSpecific(path))
                    report['falls'][theme+'-'+label]['native_frames']=native
                    report['falls'][theme+'-'+label]['native_samples']=native_samples
                    report['falls'][theme+'-'+label]['received_actions']=actions
                    d.click_widget(hud.buttons['Restart']);d.wait(lambda:c.phase=='READY')
                report['checks'].append(theme+': production F1/F2 + native Down/Left + result + HUD Restart')
                for size in (() if args.native_falls_only else ((1280,720),(1024,720),(1920,1080))):
                    d.pointer(500,300);_resize(a,size);_present(a);enter(10)
                    if g.selected:g.close_card()
                    expected=bounds();fit=a.presentation.camera.current_fit
                    region=tuple(a.dashboard.viewport.region.getDimensions());errors=[]
                    for key,b in g.buttons.items():
                        l,rr,bb,t=b['frameSize'];p=a.pixel2d.getRelativePoint(b,Point3((l+rr)/2,0,(bb+t)/2))
                        d.pointer(p.x,-p.z);errors.append(stable(expected))
                        d.xt.XTestFakeButtonEvent(d.display,1,True,0);d.x.XFlush(d.display);d.step(3)
                        errors.append(stable(expected))
                        d.xt.XTestFakeButtonEvent(d.display,1,False,0);d.x.XFlush(d.display);d.step(3)
                        errors.append(stable(expected));assert g.selected==key
                        assert fit==a.presentation.camera.current_fit
                        assert region==tuple(a.dashboard.viewport.region.getDimensions())
                    shot(theme+f'-{size[0]}-guide-card')
                    card=g.layout.card;before=c.state;moves=c.moves
                    flow.save.settings.control_mode='mouse';flow.show('game');d.step(2)
                    d.pointer(card.x+60,card.y+100);d.click();d.step(3)
                    assert c.state==before and c.moves==moves and not c.manager.is_busy
                    flow.save.settings.control_mode='keyboard';flow.show('game')
                    d.click_widget(g.close_button);errors.append(stable(expected))
                    # Keep selected icon centers stable across actual theme updates.
                    flow.apply_scene_theme('light' if theme=='dark' else 'dark');errors.append(stable(expected))
                    flow.apply_scene_theme(theme);errors.append(stable(expected))
                    shot(theme+f'-{size[0]}-toolbar')
                    # All five existing toolbar callbacks are exercised, including
                    # the multicolour robot on the unchanged AI Solver button.
                    d.click_widget(hud.buttons['Guide']);assert hud.guide_open
                    d.click_widget(hud.buttons['Guide']);assert not hud.guide_open
                    view=a.game_views.index
                    d.click_widget(hud.buttons['View']);assert a.game_views.index!=view
                    d.click_widget(hud.buttons['Tutorial']);assert a.game_tutorial.visible
                    d.key('h');assert not a.game_tutorial.visible
                    d.click_widget(hud.buttons['Exit']);assert flow.name=='levels'
                    report['bounds'].append({'theme':theme,'size':size,'max_error_px':max(errors)})
                if not args.native_falls_only:
                    report['checks'].append(theme+': hover/press/release/card/theme/resize bounds <=1px; all toolbar callbacks')
            enter(10);g.show_mechanic('bridge');d.wait(lambda:flow._par_job is None)
            baseline=resources()
            for _ in range(20):
                g.close_card();g.show_mechanic('void');g.close_card();g.show_mechanic('bridge')
            assert baseline==resources();report['20_card_cycles']={'before':baseline,'after':resources()}
        finally:d.close();dispose_game(a,r,c)
        report['after_dispose']={'tasks':len(a.taskMgr.getTasks())+len(a.taskMgr.getDoLaters()),
            'widgets':len(DirectGuiWidget.guiDict),'outputs':GraphicsEngine.getGlobalPtr().getNumWindows(),
            'listeners':sum(len(messenger.whoAccepts(e) or {}) for e in messenger.getEvents())}
        assert all(v==0 for v in report['after_dispose'].values())
    report['status']='PASS';(out/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='falls'},indent=2))

if __name__=='__main__':main()
