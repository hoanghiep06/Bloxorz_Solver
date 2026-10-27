"""Capture real Panda3D framebuffers for the visual overhaul.

Uses a temporary save and the deterministic mechanics test catalog by default.
No screenshots are composited or used as game surfaces. Demo roll shots are
explicit animation DTOs, labelled in the JSON manifest.
"""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import statistics
import tempfile
import time


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/jungle-visual'))
    parser.add_argument('--game-only',action='store_true')
    args=parser.parse_args(argv);out=args.output;out.mkdir(parents=True,exist_ok=True)
    from panda3d.core import loadPrcFileData, GraphicsEngine
    loadPrcFileData('visual-qa','audio-library-name null')
    from src.gui.game_app import create_game,dispose_game
    from tools.gui_stage3_6_smoke import _present,_resize
    from tools.native_input import NativeInput
    from direct.gui.DirectGuiBase import DirectGuiWidget
    from direct.showbase.MessengerGlobal import messenger
    catalog=Path(__file__).resolve().parents[1]/'tests/fixtures/mechanics'
    report={'images':[],'checks':[], 'source':'native Panda3D framebuffer'}
    def shot(app,name):
        for _ in range(3):app.graphicsEngine.renderFrame()
        app.graphicsEngine.syncFrame()
        path=out/(name+'.png');assert app.win.saveScreenshot(str(path))
        report['images'].append(str(path))
    with tempfile.TemporaryDirectory() as tmp:
        a,r,c=create_game(catalog,save_path=Path(tmp)/'save.json')
        driver=NativeInput(a)
        try:
            _present(a);driver.step(5)
            shot(a,'main-menu')
            flow=a.game_flow;hud=a.dashboard.hud
            def enter(index):
                flow.start_level(index);flow.intro.finish();c.set_speed(1);driver.step(3)
            enter(0);hud.set_guide_visible(True);driver.pointer(1200,150)
            shot(a,'game-comparable')
            hud.buttons['BFS']['command']()
            assert c.selected=='BFS'
            shot(a,'solver-controls')
            enter(10);hud.set_guide_visible(True)
            for theme in ('light','dark'):
                from src.gui import ui_theme as ui
                ui.set_theme(theme);hud.restyle();flow.apply_scene_theme(theme);flow.ambient.set_theme(theme)
                driver.step(4);driver.pointer(1200,150)
                shot(a,'dashboard-'+theme+'-1280')
                _resize(a,(1024,720));driver.step(4)
                shot(a,'dashboard-'+theme+'-1024')
                _resize(a,(1280,720));driver.step(3)
            flow.apply_scene_theme('light');flow.ambient.set_theme('light');ui.set_theme('light');hud.restyle()
            from src.gui.camera import SceneBounds,CameraConfig
            from src.gui.geometry_math import cell_to_world
            x,y=cell_to_world(c.state.r,c.state.c,rows=c.board.rows,cols=c.board.cols)
            for angle in (45,135,225):
                bounds=SceneBounds((x-1.6,y-1.6,-.18),(x+1.6,y+1.6,2.3))
                a.presentation.camera.set_view(CameraConfig(azimuth=angle),bounds=bounds)
                shot(a,'magma-face-'+str(angle))
            enter(10)
            # Real Core split transition, manual controls and native Space.
            for action in ('R','R'):
                assert c.manual_move(action)
                driver.wait(lambda:not c.manager.is_busy)
            assert c.state.is_split()
            shot(a,'advanced-split')
            driver.key('space');driver.wait(lambda:not c.manager.is_busy)
            assert c.state.active_cube==1
            report['checks'].append('Core split + native Space, two textured actors')
            # The goal flag must remain visible while surfaces are leased.
            enter(2)
            actions=__import__('src.solvers.bfs',fromlist=['BFSSolver']).BFSSolver(c.board).solve().actions
            for action in actions[:2]:
                assert c.manual_move(action)
                driver.wait(lambda:not c.manager.is_busy)
            shot(a,'bridge-and-soft-switch')
            enter(10);driver.step(5)
            def counts():
                return dict(nodes=a.scene_root.findAllMatches('**').getNumPaths(),
                            tasks=len(a.taskMgr.getTasks())+len(a.taskMgr.getDoLaters()),outputs=GraphicsEngine.getGlobalPtr().getNumWindows(),
                            widgets=len(DirectGuiWidget.guiDict))
            baseline=counts()
            for _ in range(10):c.restart_level();driver.step(2)
            after=counts()
            assert all(after[key]<=baseline[key] for key in baseline),(baseline,after)
            report['resources_10_restarts']={'before':baseline,'after':counts()}
            times=[]
            for _ in range(45):
                t=time.perf_counter();a.graphicsEngine.renderFrame();a.graphicsEngine.syncFrame();times.append(time.perf_counter()-t)
            report['render_frame_ms_median']=round(statistics.median(times)*1000,2)
            report['render_fps_median']=round(1/statistics.median(times),1)
            report['gpu']=a.win.getGsg().getDriverRenderer()
            report['material_status']=a.material_status
            report['bloom_status']=a.dashboard.bloom.status
        finally:
            driver.close();dispose_game(a,r,c)
        report['after_dispose']=dict(outputs=GraphicsEngine.getGlobalPtr().getNumWindows(),
                    tasks=len(a.taskMgr.getTasks())+len(a.taskMgr.getDoLaters()),widgets=len(DirectGuiWidget.guiDict),
                    subscriptions=sum(len(messenger.whoAccepts(e) or {}) for e in messenger.getEvents()))
        assert all(v==0 for v in report['after_dispose'].values()),report['after_dispose']
    if not args.game_only:
        from src.gui.animation_preview import create_animation_preview,dispose_animation_preview
        for name in ('basic-roll','switches','bridge','fragile','split','merge','goal'):
            a,r,m=create_animation_preview(name,autoplay=False)
            try:
                _present(a)
                request=a.animation_fixture.requests[0]
                poses=dict(m.current_visual_poses)
                center=next(iter(poses.values())).center
                x,y,z=center
                bounds=SceneBounds((x-2,y-2,-.5),(x+2,y+2,2.3))
                a.presentation.camera.set_view(CameraConfig(),bounds=bounds)
                m.submit(request)
                for index,amount in enumerate((0,.5,1)):
                    if index:m.advance(request.duration*.5)
                    shot(a,f'demo-{name}-{int(amount*100):03d}')
                if m.is_busy:m.cancel()
                report['checks'].append('Explicit demo DTO: '+name)
            finally:dispose_animation_preview(a,r,m)
    report['status']='PASS'
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
