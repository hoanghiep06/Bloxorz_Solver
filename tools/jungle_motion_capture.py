"""Real framebuffer sequences for cosmetic cloth and labelled animation DTOs.

PNG frames are raw screenshots. Encode GIFs with Pillow as a separate authoring
step; Pillow is not needed to run the game or this capture tool.
"""
import argparse
import json
from pathlib import Path


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/jungle-motion'))
    parser.add_argument('--flag-only',action='store_true')
    args=parser.parse_args(argv)
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    from panda3d.core import loadPrcFileData
    loadPrcFileData('motion-qa','audio-library-name null')
    from src.gui.animation_preview import create_animation_preview,dispose_animation_preview
    from src.gui.camera import SceneBounds,CameraConfig
    from tools.gui_stage3_6_smoke import _present
    from tools.native_input import NativeInput
    report={'source':'native Panda3D framebuffers','sequences':[]}
    for scenario in (() if args.flag_only else ('basic-roll','fragile','goal','split','merge')):
        a,r,m=create_animation_preview(scenario,autoplay=False)
        try:
            _present(a)
            center=next(iter(dict(m.current_visual_poses).values())).center
            x,y,z=center
            a.presentation.camera.set_view(CameraConfig(),bounds=SceneBounds((x-2,y-2,-.8),(x+2,y+2,2.3)))
            request=a.animation_fixture.requests[0]
            m.submit(request)
            paths=[]
            for index in range(21):
                if index:m.advance(request.duration/20)
                a.graphicsEngine.renderFrame();a.graphicsEngine.syncFrame()
                path=out/f'{scenario}-{index:03d}.png'
                assert a.win.saveScreenshot(str(path));paths.append(str(path))
            m.advance(.001)
            assert not m.is_busy
            report['sequences'].append({'name':scenario,'kind':'EXPLICIT ANIMATION DTO / NOT GAMEPLAY','frames':paths})
        finally:dispose_animation_preview(a,r,m)
    # Here the app task clock drives only the cosmetic cloth. No gameplay request.
    a,r,m=create_animation_preview('bridge',autoplay=False)
    d=NativeInput(a)
    try:
        _present(a)
        flags=[f for f in r._flags.values() if not f.isHidden()];assert flags
        flag=flags[0];pos=flag.getPos(a.scene_root)
        x,y,z=pos
        a.presentation.camera.set_view(CameraConfig(),bounds=SceneBounds((x-.8,y-.8,-.3),(x+.8,y+.8,1.9)))
        snapshot=m.current_snapshot
        paths=[]
        for index in range(25):
            d.step(1)
            a.graphicsEngine.renderFrame();a.graphicsEngine.syncFrame()
            path=out/f'flag-{index:03d}.png'
            assert a.win.saveScreenshot(str(path));paths.append(str(path))
            assert m.current_snapshot==snapshot and not m.is_busy
        report['sequences'].append({'name':'flag','kind':'COSMETIC CLOCK / UNCHANGED SNAPSHOT','frames':paths})
    finally:d.close();dispose_animation_preview(a,r,m)
    (out/'report.json').write_text(json.dumps(report,indent=2))
    print('PASS',len(report['sequences']),'native sequences')


if __name__=='__main__':main()
