"""Actual catalog/UI/XTest gameplay validation for production level_19.json.

No gameplay state injection, manual animation events, temporary level catalog or
fake screenshots. Only existing UI callbacks, native input and real solver workers.
"""
import argparse
import json
from pathlib import Path
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/bloxorz-level19-ui'))
    args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    from panda3d.core import loadPrcFileData,WindowProperties
    loadPrcFileData('lab-qa','audio-library-name p3openal_audio')
    from direct.gui.DirectGui import DirectButton
    from src.gui.game_app import create_game,dispose_game
    from src.gui.mechanics_focus import mechanic_targets
    from src.gui.animation_contracts import EventKind as E
    from src.gui.controller import SOLVER_SPECS
    from tools.native_input import NativeInput
    from tools.gui_stage3_6_smoke import _present
    root=Path(__file__).resolve().parents[1]
    scenarios=json.loads((root/'tests/fixtures/level19/scenarios.json').read_text())
    report={'checks':[],'images':[],'input':'Real GLX Panda3D window, X11 XTest, production levels catalog','audio':'OpenAL Soft decoded null output; not a speaker listening test'}
    with tempfile.TemporaryDirectory() as tmp:
        save=Path(tmp)/'save.json';save.write_text(json.dumps({'settings':{'music':False}}))
        app,renderer,c=create_game(save_path=save);d=NativeInput(app);flow=app.game_flow;hud=app.dashboard.hud
        def check(message):report['checks'].append(message);print('PASS',message,flush=True)
        def shot(name):
            app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame()
            assert app.win.saveScreenshot(str(out/(name+'.png')));report['images'].append(name+'.png')
        def button(screen,text):return next(w for w in screen._owned if isinstance(w,DirectButton) and str(w['text'])==text)
        def idle():d.wait(lambda:not c.manager.is_busy and c.phase!='SOLVING',timeout=25)
        keys={'U':'Up','D':'Down','L':'Left','R':'Right','SPACE':'space'}
        def move(action):d.key(keys[action]);idle()
        def restart():
            d.click_widget(hud.buttons['Restart']);idle();assert c.state==c.board.get_initial_state() and c.moves==0
        def scenario(name,image,event=None,*,fall=False):
            restart();c.set_speed(4);actions=scenarios[name]
            for action in actions[:-1]:move(action)
            c.set_speed(.25);captured=[]
            def observe():
                request=c.manager._request
                if request is None:return
                if event is not None and not any(e.kind is event for e in request.events):return
                if fall and (request.terminal is None or request.terminal.collapse_cell is None):return
                if .32<=c.manager.progress<=.85 and not captured:shot(image);captured.append(True)
            d.on_step=observe;d.key(keys[actions[-1]]);idle();d.on_step=None
            assert captured,(name,c.phase)
            check(name+': native path from Start produced confirmed animation and framebuffer capture')
        def solve(name):
            restart();c.set_speed(4)
            if not hud.guide_open:d.click_widget(hud.buttons['Guide'])
            d.click_widget(hud.buttons[name]);d.click_widget(hud.buttons['Play'])
            d.wait(lambda:c.phase=='GOAL',timeout=120)
            assert c.search.success and c.board.is_goal(c.state) and c.moves==c.search.solution_length
            d.wait(lambda:not c.guide_active);d.step(3)
            report.setdefault('solvers' if c.level_index==18 else 'level18_progression',{})[name]={'moves':c.moves,'solution_length':c.search.solution_length,
                'search_ms':c.search.time_taken*1000,'expanded_nodes':c.search.expanded_nodes}
            assert flow.screens['game']._result.next_level is None if c.level_index==18 else flow.screens['game']._result.next_level==18
            check(f'{name}: native worker/replay Goal, Moves={c.moves}, metrics and catalog-based Next correct')
        try:
            props=WindowProperties();props.setOrigin(0,0);app.win.requestProperties(props);_present(app)
            assert len(flow.catalog)==19 and flow.catalog[18].title=='The Mechanics Laboratory'
            flow.show('levels');select=flow.screens['levels']
            for _ in range(2):d.click_widget(button(select,'>'));d.step(3)
            assert select.page==2;shot('level-select-19')
            d.click_widget(button(select,'19'));d.wait(lambda:not flow.intro.active and c.input_enabled)
            assert c.level_index==18 and '19/19' in hud.runtime['text']
            check('Production Level Select page 3 opens real Level 19; natural intro/landing completes; name and 19/19 visible')
            for theme in ('light','dark'):
                flow.show('settings');flow.screens['settings']._set_theme(theme)
                flow.start_level(18);d.wait(lambda:not flow.intro.active and c.input_enabled)
                shot(theme+'-level19')
                before=c.state,c.moves,c.revision;guide=flow.mechanics;focus=flow.mechanics_focus
                anchor=tuple(guide.rail.getPos(app.pixel2d))
                for key in ('fragile','soft_switch','heavy_switch','split_switch','bridge','goal','void'):
                    targets=mechanic_targets(c.board_data,key)
                    limit=len(targets) if key!='void' else 3
                    for i in range(limit):
                        d.click_widget(guide.buttons[key]);d.wait(lambda:focus._animation is None)
                        assert focus.target==targets[i],(key,i,focus.target)
                        assert before==(c.state,c.moves,c.revision) and tuple(guide.rail.getPos(app.pixel2d))==anchor
                    if key!='void':
                        d.click_widget(guide.buttons[key]);d.wait(lambda:focus._animation is None)
                        assert focus.target==targets[0]
                    if key=='split_switch':shot(theme+'-split-guide')
                    d.click_widget(guide.back_button);d.wait(lambda:not focus.has_focus)
                d.click_widget(guide.close_button)
                check(theme+': every Fragile/Soft/Heavy/Split/Bridge/Goal target cycles and wraps correctly; Void in bounds; no Core/Move/revision/rail mutation')
                scenario('bridge-open:0',theme+'-soft-bridge',E.BRIDGE_PRESENT)
                assert c.state.bridges_state[0]
                move('R');assert not c.state.bridges_state[1];shot(theme+'-heavy-bridge-closed')
                scenario('fragile-break:5:6',theme+'-fragile-collapse',E.FALL,fall=True)
                assert c.phase=='FELL' and (5,6) in c.manager.current_snapshot.broken_fragile_cells
                scenario('interior-fall',theme+'-interior-void',E.FALL)
                assert c.phase=='FELL'
                scenario('split:4:14',theme+'-split-teleport',E.SPLIT)
                assert c.state.is_split() and len(c.state.cubes)==2
                old=c.state;move('SPACE');assert c.state.cubes==old.cubes and c.state.active_cube!=old.active_cube
                scenario('merge',theme+'-merge',E.MERGE)
                assert not c.state.is_split()
                scenario('edge-fall',theme+'-edge-fall',E.FALL);assert c.phase=='FELL'
                check(theme+': all scenarios used native moves/events, two-cube identity, Space/merge/fall and exact restart flags')
            for name in SOLVER_SPECS:solve(name)
            shot('level19-victory-last-level')
            game=flow.screens['game'];assert button(game,'Next')['state']=='disabled'
            # Actual preceding level completion, no synthetic win or state injection.
            flow.start_level(17);d.wait(lambda:not flow.intro.active and c.input_enabled);solve('BFS')
            assert game._result.next_level==18 and button(game,'Next')['state']=='normal'
            d.click_widget(button(game,'Next'));d.wait(lambda:not flow.intro.active and c.input_enabled)
            assert c.level_index==18 and c.state==c.board.get_initial_state()
            check('Real Level 18 BFS victory → Next loads Level 19; Level 19 victory disables Next; no Level 20 access')
            d.click_widget(hud.buttons['Exit']);d.step(3);assert flow.name=='levels'
            d.click_widget(button(flow.screens['levels'],'Back'));d.step(3);assert flow.name=='main'
            check('Restart and native Exit → Levels → Back → Menu work; temporary save isolated')
        finally:d.on_step=None;d.close();dispose_game(app,renderer,c)
    report['status']='PASS';(out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))


if __name__=='__main__':main()
