"""Capture deterministic native framebuffer sequences for visual review.

This tool uses explicit demo DTOs, not solver/game rules. Run from a checkout
with ``python -B -m tools.animation_capture --output /tmp/animation-capture``.
PNG frames are sufficient to inspect geometry; external GIF packaging is optional.
"""
import argparse
from dataclasses import fields, replace
import json
from pathlib import Path


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--scenarios',nargs='+',default=[
        'basic-roll','fragile','fall','goal','switches','bridge','split','merge','active-cube'])
    args=parser.parse_args(argv)
    from panda3d.core import loadPrcFileData
    loadPrcFileData('capture','audio-library-name null')
    from src.gui.animation_preview import create_animation_preview,dispose_animation_preview
    from src.gui.animation_contracts import AnimationRequest,AnimationKind,AnimationEvent,EventKind,TerminalVisualOutcome
    from src.gui.advanced_contracts import WholeBlockVisualPose,SplitCubeVisualState
    from src.gui.contracts import BasicOrientation
    from src.gui.camera import SceneBounds,CameraConfig
    from src.gui.geometry_math import cell_to_world
    from tools.gui_stage3_6_smoke import _present
    args.output.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for name in args.scenarios:
        app,renderer,manager=create_animation_preview(name,autoplay=False)
        try:
            _present(app)
            for _ in range(8):app.taskMgr.step()
            fixture=app.animation_fixture
            requests=list(fixture.requests)
            # A standalone fragile demo places the actor on the collapsing tile,
            # then uses the optional metadata only in checkouts supporting it.
            if name=='fragile':
                pose=WholeBlockVisualPose(BasicOrientation.STANDING,(5,2))
                before=replace(requests[0].before_snapshot,whole_pose=pose,
                               session_id=requests[0].session_id+'-capture')
                after=replace(requests[0].after_snapshot,whole_pose=pose,session_id=before.session_id)
                requests=[replace(requests[0],before_snapshot=before,after_snapshot=after,duration=.12)]
                extra={'collapse_cell':(5,2)} if any(f.name=='collapse_cell' for f in fields(TerminalVisualOutcome)) else {}
                requests.append(AnimationRequest(1,'capture-collapse',after,None,AnimationKind.TERMINAL,.9,
                    events=(AnimationEvent(EventKind.FALL),),terminal=TerminalVisualOutcome(EventKind.FALL,**extra)))
                manager.resync(before)
            elif name=='merge':
                # Adjacent unit cubes join as the whole horizontal footprint.
                before=replace(requests[0].before_snapshot,session_id=requests[0].session_id+'-capture',cubes=(
                    SplitCubeVisualState('cube-a',(3,5)),SplitCubeVisualState('cube-b',(3,6))))
                after=replace(requests[0].after_snapshot,session_id=before.session_id,
                    whole_pose=WholeBlockVisualPose(BasicOrientation.HORIZONTAL,(3,5)))
                requests=[replace(requests[0],before_snapshot=before,after_snapshot=after)]
                manager.resync(before)
            cells={'basic-roll':((3,4),(3,6)), 'fragile':((5,2),(5,2)),
                   'fall':((1,1),(1,1)), 'goal':((3,10),(3,10)),
                   'switches':((5,7),(5,9)), 'bridge':((5,4),(5,5)),
                   'split':((3,4),(3,8)), 'merge':((3,5),(3,6)),
                   'active-cube':((3,4),(3,8))}[name]
            points=[cell_to_world(*cell,rows=manager.board.rows,cols=manager.board.cols) for cell in cells]
            xs,ys=zip(*points)
            bounds=SceneBounds((min(xs)-1.6,min(ys)-1.6,-1.8),
                               (max(xs)+1.6,max(ys)+1.6,2.3))
            app.presentation.camera.set_view(CameraConfig(),bounds=bounds)
            output=args.output/name;output.mkdir(parents=True,exist_ok=True)
            index=0
            for request in requests:
                manager.submit(request)
                count=4 if name=='fragile' and request.kind is AnimationKind.EFFECTS else 24
                for frame in range(count+1):
                    if frame:manager.advance(request.duration/count)
                    for _ in range(2):app.graphicsEngine.renderFrame()
                    app.graphicsEngine.syncFrame()
                    path=output/f'{index:03d}.png'
                    assert app.win.saveScreenshot(str(path))
                    index+=1
            manifest.append(dict(scenario=name,frames=index,source='native Panda3D framebuffer',mode='explicit demo DTOs'))
            print(name,index,flush=True)
        finally:dispose_animation_preview(app,renderer,manager)
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
