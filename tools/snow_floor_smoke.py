"""Real Panda3D framebuffer comparisons for the Snow floor material upgrade.

Run with xvfb-run -a .venv/bin/python -B -m tools.snow_floor_smoke --output ...
--stage before records the same scenes/cameras as after, before editing assets.
"""
import argparse
import json
import tempfile
import time
from pathlib import Path


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--stage',choices=('before','after'),default='after')
    parser.add_argument('--orbit',action='store_true',help='Capture Snow Temple camera orbit and distant view')
    args=parser.parse_args(argv);out=args.output;out.mkdir(parents=True,exist_ok=True)
    from panda3d.core import loadPrcFileData,WindowProperties
    loadPrcFileData('snow-floor-qa','audio-library-name null')
    from src.gui.game_app import create_game,dispose_game
    from src.gui.camera import CameraConfig,SceneBounds
    from src.gui.geometry_math import cell_to_world
    from src.gui.advanced_contracts import AdvancedTileKind as Tile
    from src.gui import visual_materials as materials
    from tools.native_input import NativeInput
    from tools.gui_stage3_6_smoke import _present,_resize
    report={'stage':args.stage,'screenshots':[],'scenes':[],'checks':[]}
    with tempfile.TemporaryDirectory() as tmp:
        app,renderer,c=create_game(save_path=Path(tmp)/'save.json')
        driver=NativeInput(app);flow=app.game_flow;camera=app.presentation.camera
        # Freeze only cosmetic weather/cloth for matching framebuffer comparisons.
        atmosphere=app.presentation.atmosphere
        if atmosphere._task is not None:app.taskMgr.remove(atmosphere._task)
        q=materials._quality[0];materials._quality[0]=type(q)(q[0],0,0,0)
        def shot(name):
            driver.pointer(10,app.win.getYSize()-5);driver.step(2)
            app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame()
            path=out/(name+'.png');assert app.win.saveScreenshot(str(path))
            report['screenshots'].append(path.name)
        def enter(theme,stem):
            flow.show('settings');driver.step(2);flow.screens['settings']._set_theme(theme);driver.step(2)
            index=next(i for i,e in enumerate(c._catalog.entries) if e.level_id==stem)
            flow.start_level(index);flow.intro.finish();flow.ambient.root.hide();driver.step(3)
            camera.configure(CameraConfig());driver.step(2)
        def size(width,height):
            driver.pointer(450,300);_resize(app,(width,height));_present(app)
            driver.pointer(width/2,height/2);driver.step(3)
        try:
            wp=WindowProperties();wp.setOrigin(0,0);app.win.requestProperties(wp);_present(app)
            for theme,stem in (('dark','level_01'),('dark','level_04'),('dark','level_11'),
                               ('dark','level_18'),('light','level_04'),('light','level_11')):
                size(1280,720);enter(theme,stem);shot(theme+'-'+stem+'-1280x720')
                samples=[]
                for _ in range(20):
                    t=time.perf_counter();app.taskMgr.step();app.graphicsEngine.syncFrame()
                    samples.append((time.perf_counter()-t)*1000)
                report['scenes'].append(dict(theme=theme,level=stem,
                    nodes=app.render.findAllMatches('**').getNumPaths(),
                    geoms=sum(p.node().getNumGeoms() for p in app.render.findAllMatches('**/+GeomNode')),
                    tasks=len(app.taskMgr.getTasks()),mean_frame_ms=sum(samples)/len(samples)))
            enter('dark','level_04')
            for width,height in ((1024,720),(1920,1080)):
                size(width,height);shot(f'dark-level_04-{width}x{height}')
            size(1280,720);enter('dark','level_04')
            cells=[(r,col) for r,row in enumerate(c.board_data.tiles) for col,kind in enumerate(row)
                   if kind is Tile.FLOOR and (r,col) not in c.board_data.goal_cells]
            cell=min(cells,key=lambda rc:abs(rc[0]-c.board_data.rows/2)+abs(rc[1]-c.board_data.cols/2))
            x,y=cell_to_world(*cell,rows=c.board_data.rows,cols=c.board_data.cols)
            close=SceneBounds((x-1.8,y-1.8,-.7),(x+1.8,y+1.8,.7))
            def inspect(config,name):
                camera.reframe(close,config)
                # This QA-only inspection changes the envelope, unlike a live
                # Follow tick; explicitly cover the new lens with the panorama.
                app.presentation.style.update_background(camera.current_fit)
                driver.step(3);shot(name)
            inspect(CameraConfig(),'dark-stone-close-up')
            inspect(CameraConfig(elevation=16),'dark-platform-sides')
            inspect(CameraConfig(elevation=-18),'dark-platform-underside')
            enter('dark','level_11');state,moves=c.state,c.moves
            g=flow.mechanics;focus=flow.mechanics_focus
            driver.click_widget(g.buttons['fragile']);driver.wait(lambda:focus._animation is None)
            assert focus.target.mechanic=='fragile';shot('dark-fragile-guide-focus')
            driver.click_widget(g.back_button);driver.wait(lambda:not focus.has_focus)
            assert (c.state,c.moves)==(state,moves)
            report['checks'].append('Guide Fragile target, Back restore and unchanged Core/Moves PASS')
            g.close_card()
            if args.stage=='after':
                # Theme changes reuse the already-built scene/materials. No
                # snapshot, floor geometry or texture allocation per switch.
                enter('dark','level_11');baseline_nodes=app.render.findAllMatches('**').getNumPaths()
                baseline_state=c.state,c.moves,c.manager.current_snapshot
                initial_misses=materials.texture.cache_info().misses
                for theme in ('light','dark')*6:
                    flow.apply_scene_theme(theme);driver.step(3)
                    assert app.render.findAllMatches('**').getNumPaths()==baseline_nodes
                    assert (c.state,c.moves,c.manager.current_snapshot)==baseline_state
                    variants=app.static_board_root.findAllMatches('**/Floor-*/TileTheme-'+theme)
                    assert variants.getNumPaths()>0 and all(not path.isHidden() for path in variants)
                assert materials.texture.cache_info().misses==initial_misses
                report['checks'].append('12 Light/Dark switches: stable nodes, no texture reload, unchanged Core/snapshot PASS')
                if args.orbit:
                    enter('dark','level_04');state=c.state,c.moves,c.manager.current_snapshot
                    for angle in range(30,391,30):
                        camera.configure(CameraConfig(azimuth=angle));driver.step(3)
                        shot(f'dark-orbit-{angle:03}')
                        assert not materials._snow_shader.getErrorFlag()
                    camera.configure(CameraConfig(padding=.27));driver.step(3);shot('dark-board-distant')
                    assert (c.state,c.moves,c.manager.current_snapshot)==state
                    report['checks'].append('Full 360-degree orbit, distant framing and close-up have no shader errors or Core changes PASS')
                # Demonstrate real shader normal-map evaluation by temporarily
                # binding a flat normal only on the Snow presentation instances.
                if getattr(materials,'_snow_shader',None) is not None:
                    from panda3d.core import PNMImage,Texture,ShaderInput
                    enter('dark','level_04')
                    camera.reframe(close,CameraConfig())
                    app.presentation.style.update_background(camera.current_fit)
                    driver.step(3);before=PNMImage()
                    app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame();assert app.win.getScreenshot(before)
                    image=PNMImage(1,1,4);image.fill(.5,.5,1);image.alphaFill(.9)
                    flat=Texture('QAFlatNormal');flat.load(image)
                    holders=app.static_board_root.findAllMatches('**/Floor-*/TileTheme-dark')
                    for holder in holders:holder.setShaderInput(ShaderInput('normal_roughness_map',flat,10))
                    app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame();after=PNMImage();assert app.win.getScreenshot(after)
                    changed=sum(max(abs(before.getXel(x,y)[i]-after.getXel(x,y)[i]) for i in range(3))>1/255
                                for y in range(90,610,2) for x in range(200,1160,2))
                    for holder in holders:holder.clearShaderInput('normal_roughness_map')
                    assert changed>30,changed
                    assert not materials._snow_shader.getErrorFlag()
                    report['normal_map_changed_samples']=changed
                    report['checks'].append('Compiled Snow shader samples real normal/roughness map; flat-map A/B changes floor framebuffer PASS')
                # Real input still rolls and falls against exactly the same
                # support. No floors are synthesized at a danger destination.
                from src.gui.move_assist import predict_moves,Severity
                enter('dark','level_01');driver.key('Right');driver.wait(lambda:not c.manager.is_busy)
                assert c.moves==1 and c.phase not in ('FELL','GOAL')
                enter('dark','level_04')
                danger=next(m for m in predict_moves(c.board,c.state).moves if m.severity is Severity.DANGER)
                before_failure=c.state,c.moves
                driver.key(dict(U='Up',D='Down',L='Left',R='Right')[danger.action])
                driver.wait(lambda:c.phase=='FELL' and flow.screens['game'].result_visible)
                # Existing controller commits only successful Core transitions;
                # failed attempts retain State/Moves. The material cannot alter it.
                assert (c.state,c.moves)==before_failure;shot('dark-manual-fall-result')
                driver.key('r');driver.step(5);assert c.moves==0 and not c.manager.is_busy
                report['checks'].append('Native Right rolls; Core-danger move falls with result; Restart restores intact board PASS')
            report['material_status']=materials.STATUS
            report['snow_material_status']=getattr(materials,'SNOW_STATUS','LEGACY')
            report['gpu']=app.win.getGsg().getDriverRenderer()
        finally:
            driver.close();dispose_game(app,renderer,c)
    report['status']='PASS';(out/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
