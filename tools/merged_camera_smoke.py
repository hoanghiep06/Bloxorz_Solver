"""Native merge regression: free camera, Guide ownership, Snow floor and ice actors."""
import argparse
import json
import tempfile
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/bloxorz-merged-ui/camera'))
    args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    from panda3d.core import WindowProperties,loadPrcFileData,TextureAttrib
    loadPrcFileData('merge-qa','audio-library-name null')
    from src.gui.game_app import create_game,dispose_game
    from src.gui import visual_materials as materials
    from tools.native_input import NativeInput
    from tools.gui_stage3_6_smoke import _present
    report={'checks':[],'images':[],'input':'Actual Panda3D GLX window and X11 XTest'}
    with tempfile.TemporaryDirectory() as tmp:
        app,renderer,c=create_game('tests/fixtures/mechanics',save_path=Path(tmp)/'save.json')
        flow=app.game_flow;d=NativeInput(app);views=app.game_views
        camera=app.presentation.camera;g=flow.mechanics;focus=flow.mechanics_focus
        def button(number,pressed):
            d.xt.XTestFakeButtonEvent(d.display,number,pressed,0)
            d.x.XFlush(d.display);d.step(3)
        def drag():
            d.pointer(500,300);button(1,True)
            for x in range(510,601,10):d.pointer(x,310)
            button(1,False);d.step(3)
        def wheel():
            d.pointer(500,300);button(4,True);button(4,False)
        def click_goal():
            d.click_widget(g.buttons['goal']);d.wait(lambda:focus._animation is None)
            assert focus.has_focus
        def shot(name):
            app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame()
            path=out/(name+'.png');assert app.win.saveScreenshot(str(path))
            report['images'].append(path.name)
        def check(text):report['checks'].append(text);print('PASS',text,flush=True)
        try:
            wp=WindowProperties();wp.setOrigin(0,0);app.win.requestProperties(wp);_present(app)
            for theme in ('light','dark'):
                flow.show('settings');flow.screens['settings']._set_theme(theme);d.step(3)
                i=next(i for i,e in enumerate(c._catalog.entries) if e.level_id=='level_11_advanced_sandbox')
                flow.start_level(i)
                # Let the latest team's intro actually finish at least once per theme.
                d.wait(lambda:not flow.intro.active,timeout=20)
                assert c.input_enabled
                assert materials.STATUS=='GLSL_DETAIL_EMISSION'
                assert materials.SNOW_STATUS=='GLSL_NORMAL_ROUGHNESS_FROST'
                state,moves=c.state,c.moves
                for index in (0,1,2):
                    views.set_view(index);d.step(4)
                    drag();assert views.drag_happened and views.user_modified
                    assert (c.state,c.moves)==(state,moves) and not c.manager.is_busy
                    wheel();d.wait(lambda:views._zoom_target==views._zoom)
                    start=camera.capture_presentation()
                    shot(f'{theme}-view-{index}-orbit-zoom')
                    click_goal();shot(f'{theme}-view-{index}-guide')
                    d.step(8)
                    d.click_widget(g.back_button);d.wait(lambda:not focus.has_focus)
                    assert camera.capture_presentation()==start,(theme,index,start,camera.capture_presentation())
                    # New wheel and new drag must each release a Guide lease.
                    click_goal();wheel();assert not focus.has_focus
                    assert views._presentation_owner is None
                    d.wait(lambda:views._zoom_target==views._zoom)
                    click_goal();drag();assert not focus.has_focus
                    assert views._presentation_owner is None
                    assert (c.state,c.moves)==(state,moves) and not c.manager.is_busy
                    d.key('c');d.step(4)
                    assert not views.user_modified and views.index==index
                check(theme+': native orbit/scroll, Guide Back restores exact view, wheel/drag takeover, C reset; no unintended moves')
                # Real actor geometry uses the agreed texture in the active theme.
                g.close_card();views.set_view(0)
                names=[]
                for path in app.block_root.findAllMatches('**/+GeomNode'):
                    if path.isHidden() or theme not in path.getName():continue
                    node=path.node()
                    for j in range(node.getNumGeoms()):
                        attr=node.getGeomState(j).getAttrib(TextureAttrib)
                        if attr:names.extend(attr.getOnTexture(attr.getOnStage(k)).getName() for k in range(attr.getNumOnStages()))
                expected='ice' if theme=='dark' else 'magma'
                assert expected in names,(expected,names)
                shot(theme+'-material-and-floor')
                hud=app.dashboard.hud
                assert hud.metrics.isHidden()
                d.click_widget(hud.buttons['Guide']);assert not hud.metrics.isHidden()
                d.click_widget(hud.buttons['Guide']);assert hud.metrics.isHidden()
                check(theme+': real '+expected+' actor, GLSL Snow coexistence and latest team Solver/metrics panel preserved')
        finally:d.close();dispose_game(app,renderer,c)
    report['status']='PASS';(out/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
