"""Real worker/UI solver pipeline on the current catalog, sampled native replay.

Animation timelines are advanced deterministically to finish long DFS paths in
QA. The normal wall-clock playback is covered separately by game_integration_smoke.
"""
import argparse
import json
from pathlib import Path
import tempfile
import time


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/jungle-current-catalog'))
    args=parser.parse_args(argv);args.output.mkdir(parents=True,exist_ok=True)
    from panda3d.core import loadPrcFileData,GraphicsEngine
    loadPrcFileData('silent','audio-library-name null')
    from src.gui.game_app import create_game,dispose_game
    from src.gui.controller import SOLVER_SPECS
    from tools.gui_stage3_6_smoke import _present
    from direct.gui.DirectGuiBase import DirectGuiWidget
    report={'runs':[],'replay_sampling':'deterministic phase advancement with native framebuffers'}
    with tempfile.TemporaryDirectory() as tmp:
        a,r,c=create_game(save_path=Path(tmp)/'save.json')
        try:
            _present(a)
            for index,entry in enumerate(c._catalog.entries):
                for name in SOLVER_SPECS:
                    a.game_flow.start_level(index);a.game_flow.intro.finish();c.set_speed(4)
                    hud=a.dashboard.hud;hud.set_guide_visible(True)
                    hud.buttons[name]['command']();hud.buttons['Play']['command']()
                    deadline=time.monotonic()+60
                    while c.search is None:
                        a.taskMgr.step();time.sleep(.001)
                        if time.monotonic()>deadline:raise AssertionError('Solver timeout '+entry.level_id+'/'+name+' phase='+c.phase+' status='+c._status)
                    result=c.search
                    if not result.success:
                        row=dict(level=entry.level_id,solver=name,status='NO_SOLUTION',message=str(c._status))
                    else:
                        for phase in range(max(100,10*result.solution_length)):
                            if c.manager.is_busy:c.manager.advance(2)
                            if phase%20==0:a.taskMgr.step()
                            if c.phase=='GOAL':break
                        assert c.phase=='GOAL',(entry.level_id,name,c._status)
                        assert c.moves==result.solution_length
                        assert hud.metric_values[3]['text']==str(result.solution_length)
                        for _ in range(2):a.graphicsEngine.renderFrame()
                        a.graphicsEngine.syncFrame()
                        if name=='BFS':a.win.saveScreenshot(str(args.output/(entry.level_id+'-bfs.png')))
                        row=dict(level=entry.level_id,solver=name,status='PASS',moves=c.moves)
                    # Allow UIFlow's deferred completion to return control before
                    # loading the next run; preserve its real lifecycle boundary.
                    while c.guide_active:
                        a.taskMgr.step();time.sleep(.001)
                    report['runs'].append(row);print(json.dumps(row),flush=True)
                    (args.output/'report.json').write_text(json.dumps(report,indent=2))
        finally:dispose_game(a,r,c)
        report['after_dispose']=dict(outputs=GraphicsEngine.getGlobalPtr().getNumWindows(),
                                    tasks=len(a.taskMgr.getTasks()),widgets=len(DirectGuiWidget.guiDict))
        assert all(v==0 for v in report['after_dispose'].values())
    report['status']='PASS' if all(row['status']=='PASS' for row in report['runs']) else 'CATALOG_ISSUES'
    (args.output/'report.json').write_text(json.dumps(report,indent=2))
    print(report['status'],len(report['runs']),flush=True)


if __name__=='__main__':main()
