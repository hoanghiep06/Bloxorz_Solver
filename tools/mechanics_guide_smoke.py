"""Native XTest guide acceptance + real framebuffer captures; temporary save only."""
import argparse
import json
from pathlib import Path
import tempfile


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/mechanics-guide-qa'))
    args=parser.parse_args(argv);out=args.output;out.mkdir(parents=True,exist_ok=True)
    from panda3d.core import GraphicsEngine,loadPrcFileData,WindowProperties
    loadPrcFileData('guide-qa','audio-library-name null')
    from direct.gui.DirectGuiBase import DirectGuiWidget
    from direct.showbase.MessengerGlobal import messenger
    from src.gui.game_app import create_game,dispose_game
    from src.gui.mechanics_guide_data import MECHANICS,BY_ID
    from src.gui import ui_theme as ui
    from src.gui.camera import project_point
    from tools.native_input import NativeInput
    from tools.gui_stage3_6_smoke import _present,_resize
    report={'input':'X11 XTest native mouse and keyboard','checks':[],'images':[]}
    def check(name):report['checks'].append(name);print('PASS',name,flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        levels=Path(__file__).resolve().parents[1]/'tests/fixtures/mechanics'
        a,r,c=create_game(levels,save_path=Path(tmp)/'save.json');d=NativeInput(a)
        g=a.game_flow.mechanics;flow=a.game_flow;hud=a.dashboard.hud
        def shot(name):
            for _ in range(2):a.graphicsEngine.renderFrame()
            a.graphicsEngine.syncFrame();path=out/(name+'.png')
            assert a.win.saveScreenshot(str(path));report['images'].append(str(path))
        def resize(size):
            # Keep the real cursor inside both old/new client rectangles; keep
            # the largest requested window fully on the Xvfb desktop.
            d.pointer(500,300)
            _resize(a,size);_present(a);d.step(3)
        def idle():d.wait(lambda:not c.manager.is_busy and c.phase!='SOLVING');d.step(3)
        def counts():
            return dict(widgets=len(DirectGuiWidget.guiDict),
                listeners=sum(len(messenger.whoAccepts(e) or {}) for e in messenger.getEvents()),
                tasks=len(a.taskMgr.getTasks())+len(a.taskMgr.getDoLaters()),
                outputs=GraphicsEngine.getGlobalPtr().getNumWindows(),
                guide_nodes=0 if g.root.isEmpty() else g.root.findAllMatches('**').getNumPaths())
        try:
            origin=WindowProperties();origin.setOrigin(0,0);a.win.requestProperties(origin)
            _present(a);flow.start_level(10);flow.intro.finish();d.step(4)
            flow.save.settings.control_mode='mouse'
            # The native pass starts from the actual icon-only default.
            assert g.selected is None and not g.root.isHidden() and g.card.isHidden()
            for theme in ('dark','light'):
                ui.set_theme(theme);hud.restyle();flow.apply_scene_theme(theme);flow.ambient.set_theme(theme)
                if g.selected:g.close_card()
                d.step(3);shot(theme+'-rail-closed')
                state=c.state;moves=c.moves
                for item in MECHANICS:
                    d.click_widget(g.buttons[item.id])
                    assert g.selected==item.id,(item.id,g.selected)
                    assert g.title['text']==item.name and g.body['text']==item.description
                    assert not g.card.isHidden()
                    assert g.large_icon.getNumChildren()==1
                    assert c.state==state and c.moves==moves
                check(theme+': 7 native icons replace one card without moving the block')
                d.click_widget(g.buttons['void']);assert g.selected is None
                d.click_widget(g.buttons['fragile']);assert g.selected=='fragile'
                shot(theme+'-card-open')
                # Passive body/padding must be blocked, not just the X/icon widgets.
                rect=g.layout.card
                d.pointer(rect.x+60,rect.y+90);d.click();d.step(4)
                assert c.state==state and c.moves==moves
                assert flow.arrows._hover() is None
                check(theme+': card body blocks board clicks and move-preview hover')
                d.click_widget(g.close_button);assert g.selected is None
                assert c.state==state and c.moves==moves
                check(theme+': same icon and real X close card')
                for width,height in ((1024,720),(1280,720),(1366,768),(1920,1080)):
                    resize((width,height))
                    if g.selected:g.close_card()
                    d.click_widget(g.buttons['split_switch'])
                    assert g.selected=='split_switch'
                    layout=g.layout
                    for rect in (layout.rail,layout.card):
                        assert 136<=rect.y and rect.bottom<height-94
                        assert rect.right<=width-20
                    # The real fitted Iso board remains to the left of the card.
                    fit=a.presentation.camera.current_fit
                    left,right,bottom,top=a.dashboard.viewport.region.getDimensions()
                    assert round(right*width)<layout.card.x
                    for point in fit.bounds.corners():
                        x,y,_=project_point(point,fit)
                        px=(left+(x+1)/2*(right-left))*width
                        assert px<layout.card.x,(width,height,px,layout.card.x)
                    if width in (1024,1920):shot(f'{theme}-card-{width}')
                check(theme+': four target resolutions, no HUD overlap or board behind card')
            resize((1280,720))
            # Theme update while the same card remains open; widget identities stable.
            buttons=tuple(g.buttons.values());selected=g.selected;baseline=counts()
            for theme in ('dark','light')*10:
                ui.set_theme(theme);hud.restyle();flow.apply_scene_theme(theme)
                d.step(1)
                assert g.selected==selected and tuple(g.buttons.values())==buttons
                assert counts()==baseline,(baseline,counts())
            report['20_theme_updates']={'before':baseline,'after':counts()}
            check('20 theme changes preserve selected card, widgets/listeners/tasks/outputs')
            flow.save.settings.control_mode='keyboard'
            flow.start_level(0);flow.intro.finish();d.step(3)
            assert g.selected==selected and not g.card.isHidden()
            before=c.state;expected=c.board.transition(before,'R');moves=c.moves
            d.key('Right');idle()
            assert c.state==expected and c.moves==moves+1
            assert g.selected==selected
            check('Keyboard roll works while card is open')
            d.key('r');idle();assert g.selected==selected and not g.card.isHidden()
            # Open another card while an existing action is already animating.
            g.close_card();before=c.state;expected=c.board.transition(before,'R');moves=c.moves
            assert c.manual_move('R');assert c.manager.is_busy
            d.click_widget(g.buttons['bridge']);idle()
            assert c.state==expected and c.moves==moves+1 and g.selected=='bridge'
            check('Native guide click during roll does not cancel or duplicate the action')
            d.key('r');idle();assert g.selected=='bridge'
            for index in (10,0):
                flow.start_level(index);flow.intro.finish();d.step(3)
                assert g.selected=='bridge' and not g.root.isHidden() and not g.card.isHidden()
            check('Restart and level changes keep the existing rail/card')
            # Menus hide guide; re-entering restores it, without duplicate widgets.
            flow.show('settings');d.step(2);assert g.root.isHidden()
            flow.start_level(0);flow.intro.finish();d.step(3)
            assert g.selected=='bridge' and not g.root.isHidden()
            # Keep card visible through all six real solver/replay paths.
            for name in ('BFS','DFS','IDS','UCS','Greedy','A*'):
                c.restart_level();hud.set_guide_visible(True);d.step(2)
                d.click_widget(hud.buttons[name]);d.click_widget(hud.buttons['Play'])
                d.wait(lambda:c.search is not None,timeout=30)
                result=c.search;assert result.success
                d.wait(lambda:c.phase=='GOAL',timeout=30)
                assert c.moves==result.solution_length
                assert g.selected=='bridge' and not g.card.isHidden()
                d.wait(lambda:not c.guide_active)
            check('Six solver buttons, true worker metrics and clock replay work with guide open')
            # Minimum-size fallback can hide the component and then restore selection.
            resize((900,600));assert g.root.isHidden()
            resize((1024,720))
            assert g.selected=='bridge' and not g.root.isHidden()
            check('Unsupported size hides cleanly; valid resize restores selected card')
        finally:d.close();dispose_game(a,r,c)
        report['after_dispose']=counts()
        assert all(v==0 for v in report['after_dispose'].values()),report['after_dispose']
    report['status']='PASS'
    (out/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
