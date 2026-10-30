"""Native production-Level-19 replay from a changed current state after weighted merge."""
import argparse
import json
import tempfile
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/phong-merge-production-ui'))
    out=parser.parse_args().output;out.mkdir(parents=True,exist_ok=True)
    from panda3d.core import loadPrcFileData,WindowProperties
    loadPrcFileData('merge-qa','audio-library-name null')
    from src.gui.game_app import create_game,dispose_game
    from src.solvers.UCS_Algorithm.cost_functions import TunedWeightCost,INVERSE_ACTIONS
    from tools.native_input import NativeInput
    from tools.gui_stage3_6_smoke import _present
    report={'input':'Native X11 XTest in real Panda3D GLX window','runs':[],'screenshots':[]}
    with tempfile.TemporaryDirectory() as tmp:
        save=Path(tmp)/'save.json';save.write_text(json.dumps({'settings':{'music':False}}))
        app,r,c=create_game(save_path=save);d=NativeInput(app);flow=app.game_flow;hud=app.dashboard.hud
        try:
            props=WindowProperties();props.setOrigin(0,0);app.win.requestProperties(props);_present(app)
            for theme in ('light','dark'):
                flow.show('settings');flow.screens['settings']._set_theme(theme)
                costs={}
                for name in ('UCS','A*','Greedy'):
                    flow.start_level(18);flow.intro.finish();c.set_speed(4);d.step(3)
                    for _ in range(2):d.key('Right');d.wait(lambda:not c.manager.is_busy)
                    root=c.state;session=c.session_id;before=c.moves
                    assert before==2 and root.bridges_state==(True,False,False)
                    if not hud.guide_open:d.click_widget(hud.buttons['Guide'])
                    d.click_widget(hud.buttons[name]);assert c.state==root and c.moves==before
                    d.click_widget(hud.buttons['Play']);d.wait(lambda:c.phase=='GOAL',timeout=90)
                    assert c.search.start_state==root and c.session_id==session
                    assert c.search.success and c.moves==before+c.search.solution_length and c.board.is_goal(c.state)
                    d.wait(lambda:not c.guide_active and flow.screens['game'].result_visible)
                    state=root;last=None;cost=0.;model=TunedWeightCost()
                    for action in c.search.actions:
                        nxt=c.board.transition(state,action);assert nxt is not None
                        cost+=model.calculate_cost(state,action,nxt,c.board,last_action=last)
                        last=action if action in INVERSE_ACTIONS else None;state=nxt
                    assert c.board.is_goal(state)
                    costs[name]=cost
                    row={'theme':theme,'solver':name,'manual_moves':before,'remaining_actions':c.search.solution_length,
                         'total_moves':c.moves,'weighted_cost':cost,'expanded_nodes':c.search.expanded_nodes}
                    report['runs'].append(row);print('PASS',json.dumps(row),flush=True)
                    if name=='A*':
                        path=out/(theme+'-weighted-current-state-goal.png')
                        app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame()
                        assert app.win.saveScreenshot(str(path));report['screenshots'].append(path.name)
                assert costs['A*']==costs['UCS'],costs
            report['status']='PASS'
        finally:d.close();dispose_game(app,r,c)
    (out/'report.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
