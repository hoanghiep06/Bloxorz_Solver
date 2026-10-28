"""Native About navigation, four sizes/two themes, demo stub and resource QA."""
from pathlib import Path
import argparse,json,tempfile,threading
from unittest.mock import patch


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/about-page-ui'))
    args=parser.parse_args(argv);out=args.output;out.mkdir(parents=True,exist_ok=True)
    from panda3d.core import loadPrcFileData,GraphicsEngine,WindowProperties
    loadPrcFileData('about-qa','audio-library-name null')
    from direct.gui import DirectGuiGlobals as DGG
    from direct.gui.DirectGuiBase import DirectGuiWidget
    from direct.showbase.MessengerGlobal import messenger
    from src.gui.game_app import create_game,dispose_game
    from src.gui import about_page as about
    from tools.native_input import NativeInput
    from tools.gui_stage3_6_smoke import _present,_resize
    report={'checks':[],'images':[],'input':'X11 XTest real mouse/keys; browser mocked'}
    with tempfile.TemporaryDirectory() as tmp:
        a,r,c=create_game(save_path=Path(tmp)/'save.json');flow=a.game_flow;d=NativeInput(a)
        def button(page,text):
            return next(b for b in flow.screens[page]._owned if hasattr(b,'dims') and b['text']==text)
        def shot(name):
            a.graphicsEngine.renderFrame();a.graphicsEngine.syncFrame()
            path=out/(name+'.png');assert a.win.saveScreenshot(str(path));report['images'].append(str(path))
        def counts():
            return dict(widgets=len(DirectGuiWidget.guiDict),
                listeners=sum(len(messenger.whoAccepts(e) or {}) for e in messenger.getEvents()),
                tasks=len(a.taskMgr.getTasks())+len(a.taskMgr.getDoLaters()),
                outputs=GraphicsEngine.getGlobalPtr().getNumWindows())
        def check(name):report['checks'].append(name);print('PASS',name,flush=True)
        try:
            wp=WindowProperties();wp.setOrigin(0,0);a.win.requestProperties(wp)
            _present(a);d.pointer(500,300)
            for theme in ('light','dark'):
                if flow.name!='main':flow.show('main')
                d.click_widget(button('main','Settings'))
                flow.screens['settings']._set_theme(theme);d.step(3)
                d.click_widget(button('settings','Back'));assert flow.name=='main'
                for size in ((1280,720),(1366,768),(1920,1080),(1024,720)):
                    d.pointer(500,300);_resize(a,size);_present(a)
                    expected=(id(c.board),id(c.manager),id(c._scene))
                    region=tuple(a.dashboard.viewport.region.getDimensions())
                    with patch.object(c,'load_level',wraps=c.load_level) as load,patch.object(c,'restart_level',wraps=c.restart_level) as restart:
                        d.click_widget(button('main','About'));assert flow.name=='about'
                        load.assert_not_called();restart.assert_not_called()
                    assert (id(c.board),id(c.manager),id(c._scene))==expected
                    assert tuple(a.dashboard.viewport.region.getDimensions())==region
                    assert a.game_attract.active
                    page=flow.screens['about'];content=page.content
                    assert [tuple(w['text'] for w in pair) for pair in content['team']]==list(about.TEAM)
                    assert content['watch']['state']==DGG.DISABLED and content['status']['text']=='Coming soon'
                    with patch.object(about.webbrowser,'open') as browser:
                        d.click_widget(content['watch']);browser.assert_not_called()
                    # Check actual text metrics without rasterizing a substitute UI.
                    for label in content['labels']:
                        node=label.component('text0').textNode;scale=label['text_scale'][0]
                        assert label.getX()+node.getRight()*scale<=content['left']-12
                        assert -label.getZ()-node.getBottom()*scale<=size[1]-16
                    assert content['bottom']<=size[1]-16
                    shot(theme+f'-about-{size[0]}')
                    d.click_widget(content['back']);assert flow.name=='main'
                check(theme+': native About/Back, correct names, disabled demo, four sizes; same 3D scene/window')
                d.click_widget(button('main','About'));d.key('Escape');assert flow.name=='main'
            # Exercise configured URL without opening a fictitious real website.
            url='https://www.youtube.com/watch?v=AbCdEf123_-';opened=threading.Event()
            with patch.object(about,'DEMO_YOUTUBE_URL',url),patch.object(about.webbrowser,'open',side_effect=lambda *args,**kw:opened.set()) as browser:
                d.click_widget(button('main','About'));page=flow.screens['about']
                assert page.content['watch']['state']==DGG.NORMAL
                d.click_widget(page.content['watch']);d.wait(opened.is_set)
                browser.assert_called_once_with(url,new=2)
                d.step(3);assert flow.name=='about' and a.win.isActive()
            page.rebuild();d.step(3);assert page.content['watch']['state']==DGG.DISABLED
            check('Configured demo native click dispatches correct browser URL without blocking UI; default restored disabled')
            d.click_widget(page.content['back']);d.click_widget(button('main','Start'))
            assert flow.name=='levels';d.key('Escape');assert flow.name=='main'
            with patch.object(a,'userExit') as quit_app:
                flow.screens['main'].rebuild();d.step(3)
                d.click_widget(button('main','Quit'));quit_app.assert_called_once()
            check('Start/Settings/Quit and Escape retain their callbacks')
            # Same two screens rebuilt repeatedly; no event registration or window growth.
            flow.show('about');flow.show('main');d.step(3);baseline=counts()
            for _ in range(20):
                d.click_widget(button('main','About'))
                d.click_widget(flow.screens['about'].content['back'])
            after=counts();assert after==baseline,(baseline,after)
            report['20_cycles']={'before':baseline,'after':after}
            check('20 native About/Back cycles retain widget/listener/task/output counts')
        finally:d.close();dispose_game(a,r,c)
        report['after_dispose']=counts();assert all(v==0 for v in report['after_dispose'].values())
    report['status']='PASS';(out/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
