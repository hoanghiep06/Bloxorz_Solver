"""Native XTest quality switches, persistence, framebuffer and resource QA."""
import argparse
import json
import os
from pathlib import Path
import statistics
import tempfile
import time


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/jungle-quality'))
    args=parser.parse_args(argv)
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    from panda3d.core import loadPrcFileData,GraphicsEngine
    loadPrcFileData('quality-qa','audio-library-name null')
    from direct.gui.DirectGuiBase import DirectGuiWidget
    from src.gui.game_app import create_game,dispose_game
    from src.gui import visual_quality as quality
    from src.gui.profile import SaveData
    from tools.native_input import NativeInput
    from tools.gui_stage3_6_smoke import _present,_resize
    report={'input':'native XTest','profiles':[],'checks':[]}
    # This tool exercises saved preferences rather than the process override.
    os.environ.pop('BLOXORZ_QUALITY',None)
    with tempfile.TemporaryDirectory() as tmp:
        save=Path(tmp)/'save.json'
        a,r,c=create_game(save_path=save)
        d=NativeInput(a)
        def shot(name):
            a.graphicsEngine.renderFrame();a.graphicsEngine.syncFrame()
            assert a.win.saveScreenshot(str(out/(name+'.png')))
        def counts():
            return dict(outputs=GraphicsEngine.getGlobalPtr().getNumWindows(),
                        tasks=len(a.taskMgr.getTasks())+len(a.taskMgr.getDoLaters()),
                        nodes=0 if a.scene_root.isEmpty() else a.scene_root.findAllMatches('**').getNumPaths(),
                        widgets=len(DirectGuiWidget.guiDict))
        try:
            _present(a);d.step(4)
            flow=a.game_flow
            # Native menu button, then native quality buttons (no callback calls).
            settings=next(w for w in flow.screens['main']._owned if w.__class__.__name__=='DirectButton' and w['text']=='Settings')
            d.click_widget(settings);d.wait(lambda:flow.name=='settings')
            flow.attract.stop();c.restart_level()
            screen=flow.screens['settings'];d.step(3)
            shot('settings-quality')
            baseline=None
            for i in range(5):
                for choice in ('high','balanced','low','auto'):
                    state=c.state;session=c.session_id;moves=c.moves
                    d.click_widget(screen._quality_buttons[choice]);d.step(2)
                    assert quality.CURRENT==choice,(choice,quality.CURRENT)
                    assert quality.EFFECTIVE==quality.resolve(choice,quality.RENDERER)
                    assert SaveData(save).settings.quality==choice
                    assert c.state==state and c.session_id==session and c.moves==moves
                    expected='ENABLED' if quality.EFFECTIVE=='high' else 'DISABLED_QUALITY'
                    assert a.dashboard.bloom.status==expected,a.dashboard.bloom.status
                if i==0:baseline=counts()
            final=counts()
            assert baseline==final,(baseline,final)
            report['20_native_switches']={'before':baseline,'after':final}
            report['checks'].append('Live preference updates preserve state/session/Moves; saved JSON matches every native click')
            for choice in ('high','balanced','low'):
                d.click_widget(screen._quality_buttons[choice]);d.step(2)
                flow.start_level(0);flow.intro.finish();d.step(3)
                d.pointer(1200,150)
                shot('game-'+choice)
                times=[]
                for _ in range(45):
                    t=time.perf_counter();a.graphicsEngine.renderFrame();a.graphicsEngine.syncFrame()
                    times.append(time.perf_counter()-t)
                report['profiles'].append(dict(choice=choice,effective=quality.EFFECTIVE,
                    median_render_ms=round(statistics.median(times)*1000,2),
                    median_render_fps=round(1/statistics.median(times),1),
                    bloom=a.dashboard.bloom.status,resources=counts()))
                flow.show('settings');flow.attract.stop();c.restart_level()
                d.step(2);screen=flow.screens['settings']
            _resize(a,(1024,720));d.step(3);shot('settings-1024')
            _resize(a,(1280,720));d.step(3);screen=flow.screens['settings']
            d.click_widget(screen._quality_buttons['balanced']);d.step(2)
            report['gpu']=a.win.getGsg().getDriverRenderer()
            report['material_status']=a.material_status
        finally:
            d.close();dispose_game(a,r,c)
        report['after_dispose']=counts()
        assert all(v==0 for v in report['after_dispose'].values()),report['after_dispose']
        # A second real window must load the saved preference, not the default.
        a,r,c=create_game(save_path=save)
        try:
            _present(a)
            assert quality.CURRENT=='balanced'
            assert quality.EFFECTIVE=='balanced'
            assert a.dashboard.bloom.status=='DISABLED_QUALITY'
            report['checks'].append('Saved Balanced preference restored in a fresh game window')
        finally:dispose_game(a,r,c)
    (out/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
