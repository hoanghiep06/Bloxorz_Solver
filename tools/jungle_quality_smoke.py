"""Native Settings QA: graphics controls removed, default High, legacy-save migration."""
import argparse
import json
import os
from pathlib import Path
import tempfile


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/jungle-quality'))
    out=parser.parse_args(argv).output;out.mkdir(parents=True,exist_ok=True)
    from panda3d.core import loadPrcFileData
    loadPrcFileData('quality-qa','audio-library-name null')
    from direct.gui.DirectGui import DirectButton,DirectLabel
    from src.gui.game_app import create_game,dispose_game
    from src.gui import visual_quality as quality
    from src.gui.profile import SaveData
    from tools.native_input import NativeInput
    from tools.gui_stage3_6_smoke import _present,_resize
    report={'input':'Panda3D GLX window + native X11 XTest','checks':[],'images':[]}
    os.environ.pop('BLOXORZ_QUALITY',None)
    with tempfile.TemporaryDirectory() as tmp:
        save=Path(tmp)/'save.json'
        save.write_text(json.dumps({'settings':{'quality':'low','music_volume':.4},'stars':{'level_01':3}}))
        for launch in range(2):
            app,renderer,c=create_game(save_path=save);d=NativeInput(app);flow=app.game_flow
            def buttons(page):
                return {w['text']:w for w in flow.screens[page]._owned if isinstance(w,DirectButton)}
            try:
                _present(app);d.step(4)
                assert quality.CURRENT==quality.EFFECTIVE=='high'
                assert app.dashboard.bloom.status=='ENABLED'
                assert SaveData(save).settings.quality=='high'
                assert flow.save.stars_for('level_01')==3 and abs(flow.save.settings.music_volume-.4)<1e-6
                d.click_widget(buttons('main')['Settings']);assert flow.name=='settings'
                for theme in ('light','dark'):
                    d.click_widget(buttons('settings')[theme.capitalize()]);d.step(4)
                    for size in ((1280,720),(1024,720)):
                        d.pointer(500,300);_resize(app,size);_present(app);d.step(3)
                        screen=flow.screens['settings']
                        labels=[str(w['text']) for w in screen._owned if isinstance(w,DirectLabel)]
                        assert 'Graphics quality' not in labels
                        assert {'Auto','High','Balanced','Low'}.isdisjoint(buttons('settings'))
                        assert {'Keyboard','Mouse','Light','Dark','On','Off','Back'}<=set(buttons('settings'))
                        assert {'Master volume','Music / Ambience','Sound effects'}<=set(labels)
                        assert quality.CURRENT==quality.EFFECTIVE=='high'
                        name=f'{theme}-settings-{size[0]}-launch-{launch}.png'
                        app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame()
                        assert app.win.saveScreenshot(str(out/name));report['images'].append(name)
                d.click_widget(buttons('settings')['Mouse']);assert flow.save.settings.control_mode=='mouse'
                d.click_widget(buttons('settings')['Keyboard']);assert flow.save.settings.control_mode=='keyboard'
                d.click_widget(buttons('settings')['Back']);assert flow.name=='main'
                assert json.loads(save.read_text())['settings']['quality']=='high'
                report['checks'].append(f'Launch {launch}: default High + bloom, legacy save/progress retained, both themes/sizes, native Controls/Back work')
            finally:d.close();dispose_game(app,renderer,c)
    report['status']='PASS';(out/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
