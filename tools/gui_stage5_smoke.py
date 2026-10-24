"""Real GraphicsWindow animation QA. All inputs are non-authoritative visual fixtures.

Screenshots, JSON and logs remain outside Git (/tmp/bloxorz-stage5 by default).
Run modes in separate processes for reliable framebuffer/shadow/AA observations.
"""
import argparse
from dataclasses import replace
import gc
import json
import math
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc

from src.gui.animation_preview import create_animation_preview, dispose_animation_preview
from src.gui.animation_fixtures import get_animation_fixture, get_roll_fixture, SCENARIOS
from src.gui.animation_contracts import AnimationRequest, AnimationKind, as_visual_board
from src.gui.animation_math import RollDirection, RollPlan
from src.gui.contracts import BasicOrientation
from src.gui.animation_effects import AnimatedSurfaceLayer
from src.gui.animation_manager import AnimationManager
from src.gui.advanced_renderer import AdvancedSceneRenderer
from src.gui.advanced_preview import build_framing_data
from src.gui.hud import HudViewModel
from tools.gui_stage3_6_smoke import _present, _step, _resize, resources, _validate_frame


def counts(app):
    result=resources(app)
    result.update(tasks=len(app.taskMgr.getTasks()),
        effects_children=app.effects_root.getNumChildren(),
        animated_actor_paths=app.block_root.findAllMatches('**/AnimatedActorRig/**').getNumPaths(),
        dynamic_paths=app.dynamic_tile_root.findAllMatches('**').getNumPaths())
    return result


def load(app,renderer,manager,fixture):
    manager.dispose();renderer.dispose();app.animation_surface_layer.dispose()
    board=as_visual_board(fixture.board)
    layer=AnimatedSurfaceLayer(app.dynamic_tile_root,board)
    app.animation_surface_layer=layer
    renderer=AdvancedSceneRenderer(app.static_board_root,layer.renderer_root,app.block_root)
    renderer.load_board(board)
    manager=AnimationManager(renderer,fixture.board,fixture.initial,app.block_root,surface_layer=layer)
    rect=app.dashboard.viewport.layout.viewport
    app.presentation.camera.fit_board(build_framing_data(board),rect.width,rect.height)
    return renderer,manager


def capture(app,manager,output,name,**metadata):
    from src.gui.camera import project_point
    from panda3d.core import GraphicsWindow
    assert isinstance(app.win,GraphicsWindow)
    app.dashboard.hud.update_view_model(HudViewModel(level_label='ANIMATION DEMO DATA',
        runtime_status=metadata.get('label','NOT GAMEPLAY')))
    _step(app,4)
    _validate_frame(app)
    if manager.current_request_id is not None and manager._roll is not None:
        fit=app.presentation.camera.current_fit
        for _,pose in manager.current_visual_poses:
            for point in pose.corners():
                x,y,depth=project_point(point,fit)
                assert max(abs(x),abs(y))<1 and fit.near<depth<fit.far
    path=output/(name+'.png')
    deadline=time.perf_counter()+5
    while time.perf_counter()<deadline:
        app.graphicsEngine.renderFrame();app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame()
        if app.win.saveScreenshot(str(path)):
            break
        _step(app,1);time.sleep(.01)
    else:
        raise RuntimeError('Native framebuffer was unavailable; no screenshot evidence.')
    return {'path':str(path),'progress':manager.progress,'size':[app.win.getXSize(),app.win.getYSize()],
        'poses':[(key,{'center':p.center,'quaternion':p.quaternion,'dimensions':p.nominal_dimensions})
                 for key,p in manager.current_visual_poses],
        'actual_samples':app.win.getFbProperties().getMultisamples(),
        'shadow_status':app.presentation.lighting.shadow_status,
        'technical_checks':'PASS','visual_review':'PENDING',**metadata}


def visual(app,renderer,manager,output):
    images=[]
    for orientation in BasicOrientation:
        for direction in RollDirection:
            f=get_roll_fixture(orientation,direction)
            renderer,manager=load(app,renderer,manager,f)
            request=f.requests[0];manager.submit(request)
            for index,progress in enumerate((0,.25,.5,.75,1)):
                if index:manager.advance(request.duration*.25)
                images.append(capture(app,manager,output,
                    f'roll-{orientation.value.lower()}-{direction.name.lower()}-{int(progress*100):03}',
                    label=f'{orientation.value} {direction.name} {int(progress*100)}%',
                    group='rolling',orientation=orientation.value,direction=direction.name,sample=progress))
    f=get_animation_fixture('roll-chain');renderer,manager=load(app,renderer,manager,f)
    for i,request in enumerate(f.requests,1):
        manager.submit(request)
        for index,progress in enumerate((0,.5,1)):
            if index:manager.advance(request.duration*.5)
            images.append(capture(app,manager,output,f'chain-{i:02}-{int(progress*100):03}',
                label=f'CHAIN {i}/16 / {int(progress*100)}%',group='chain',move=i,sample=progress))
    for name in ('fragile','bridge','switches','split','merge','active-cube','cube-roll','fall','goal','combined'):
        f=get_animation_fixture(name);renderer,manager=load(app,renderer,manager,f)
        for i,request in enumerate(f.requests,1):
            manager.submit(request)
            for index,progress in enumerate((0,.5,1)):
                if index:manager.advance(request.duration*.5)
                images.append(capture(app,manager,output,f'effect-{name}-{i:02}-{int(progress*100):03}',
                    label=f'{name.upper()} {i} / {int(progress*100)}%',group=name,move=i,sample=progress))
    _resize(app,(1024,720))
    f=get_animation_fixture('combined');renderer,manager=load(app,renderer,manager,f)
    manager.submit(f.requests[0]);manager.advance(f.requests[0].duration*.5)
    images.append(capture(app,manager,output,'minimum-rolling-middle',label='ROLL 50% / NOT GAMEPLAY',group='minimum'))
    return renderer,manager,{'images':images,'status':'PASS'}


def stress(app,renderer,manager):
    f=get_animation_fixture('basic-roll');renderer,manager=load(app,renderer,manager,f)
    _step(app,20);baseline=counts(app);samples=[]
    tracemalloc.start();gc.collect();start,_=tracemalloc.get_traced_memory()
    callbacks=[]
    for i in range(500):
        before=manager.current_snapshot
        template=f.requests[0].after_snapshot if i%2==0 else f.initial
        after=replace(template,state_revision=before.state_revision+1)
        r=AnimationRequest(1,f'stress-{i}',before,after,AnimationKind.ROLL,.05,
                            RollDirection.RIGHT if i%2==0 else RollDirection.LEFT)
        manager.submit(r,callbacks.append)
        manager.advance(.02)
        if i%5==0:
            manager.pause();pose=manager.current_visual_poses;manager.advance(9)
            assert pose==manager.current_visual_poses
            manager.set_playback_rate(2);manager.resume()
        manager.advance(.1);manager.set_playback_rate(1)
        if (i+1)%100==0:
            _step(app,2);gc.collect();current,peak=tracemalloc.get_traced_memory()
            assert counts(app)==baseline
            samples.append({'requests':i+1,'resources':counts(app),'python_current_bytes':current,'python_peak_bytes':peak})
    assert len(callbacks)==500 and len({r.request_id for r in callbacks})==500
    # Separate cancellation/resync population, each with a fresh explicit demo session.
    for i in range(100):
        before=replace(f.initial,session_id=f'cancel-demo-{i}')
        manager.resync(before)
        r=replace(f.requests[0],request_id=f'cancel-{i}',before_snapshot=before,
                  after_snapshot=replace(f.requests[0].after_snapshot,session_id=before.session_id))
        manager.submit(r,callbacks.append);manager.advance(.02);manager.cancel();manager.cancel()
    assert len(callbacks)==600
    assert counts(app)==baseline
    for name in ('fragile','bridge','switches','split','merge','active-cube','fall','goal'):
        effect=get_animation_fixture(name)
        renderer,manager=load(app,renderer,manager,effect)
        effect_baseline=counts(app)
        for i in range(10):
            before=replace(effect.initial,session_id=f'{name}-stress-{i}')
            manager.resync(before)
            template=effect.requests[0]
            after=None if template.after_snapshot is None else replace(template.after_snapshot,session_id=before.session_id)
            r=replace(template,request_id=f'{name}-{i}',before_snapshot=before,after_snapshot=after)
            manager.submit(r);manager.advance(r.duration*.5)
            if i%2:manager.cancel()
            else:manager.advance(r.duration)
        assert counts(app)==effect_baseline
    for i in range(20):
        renderer,manager=load(app,renderer,manager,get_animation_fixture('basic-roll' if i%2 else 'combined'))
        manager.submit(get_animation_fixture('basic-roll' if i%2 else 'combined').requests[0])
        manager.advance(.1)
        # load() explicitly disposes the pending manager on its next iteration.
    manager.cancel()
    gc.collect();current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    return renderer,manager,{'status':'PASS','completed_rolls':500,'pause_resume_cycles':100,
        'cancel_resync_cycles':100,'effect_requests':80,'board_manager_recreations':20,
        'snapshot_batches':samples,'python_start_bytes':start,'python_end_bytes':current,'python_peak_bytes':peak,
        'final_resources':counts(app),'callback_results':len(callbacks),
        'note':'Finite stress; Python heap only, not RSS/VRAM or proof of zero leak.'}


def profile(app,renderer,manager,output,mode):
    f=get_animation_fixture('roll-chain' if mode=='rolling' else 'combined')
    renderer,manager=load(app,renderer,manager,f)
    index=0
    def update():
        nonlocal index
        if mode!='idle':
            if not manager.is_busy and index<len(f.requests):
                manager.submit(f.requests[index]);index+=1
            if manager.is_busy:manager.advance(1/60)
    for _ in range(60):update();_step(app,1)
    durations=[];minimized=foreground=active=0;before=counts(app)
    for _ in range(240):
        start=time.perf_counter();update();active+=int(manager.is_busy)
        app.taskMgr.step();app.graphicsEngine.syncFrame()
        durations.append(time.perf_counter()-start)
        minimized+=int(app.win.getProperties().getMinimized() or app.mainWinMinimized)
        foreground+=int(app.win.getProperties().getForeground())
    result={'profile':mode,'warmup_frames':60,'frames':240,'active_frames':active,
        'mean_fps':1/statistics.mean(durations),'mean_ms':statistics.mean(durations)*1000,
        'median_ms':statistics.median(durations)*1000,'p95_ms':sorted(durations)[227]*1000,
        'minimized_frames':minimized,'foreground_frames':foreground,'resources_before':before,'resources_after':counts(app),
        'capture':capture(app,manager,output,'profile-'+mode,group='profile',label='ANIMATION DEMO ONLY'),
        'note':'Wall-clock update + taskMgr.step + syncFrame, CPU/driver/compositor inclusive; deterministic visual dt=1/60.'}
    assert not minimized and foreground==240
    return renderer,manager,result


def native_entrypoints():
    result=[]
    modules=('src.gui.app','src.gui.board_preview','src.gui.dashboard_preview','src.gui.advanced_preview','src.gui.animation_preview')
    for module in modules:
        command=[sys.executable,'-B','-m',module]
        if module.endswith('animation_preview'):command+=['--scenario','combined','--speed','.25']
        p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            window=None
            for _ in range(180):
                lines=subprocess.check_output(['wmctrl','-lp'],text=True).splitlines()
                found=[line.split()[0] for line in lines if int(line.split()[2])==p.pid]
                if found:window=found[0];break
                if p.poll() is not None:break
                time.sleep(.03)
            assert window,'No native window: '+module
            time.sleep(.9 if module.endswith('animation_preview') else .3)
            subprocess.run(['wmctrl','-ic',window],check=True)
            stdout,stderr=p.communicate(timeout=15)
            assert p.returncode==0 and 'Traceback' not in stderr,stderr
            result.append({'module':module,'exit_code':p.returncode,'native_window':window,'stderr':stderr})
        finally:
            if p.poll() is None:p.terminate();p.communicate(timeout=5)
    return {'entrypoints':result}


def lifecycle():
    """Sequential native hosts, including host-first close during an accepted request."""
    from panda3d.core import GraphicsEngine
    from direct.showbase.MessengerGlobal import messenger
    runs=[]
    for i in range(3):
        app,renderer,manager=create_animation_preview('basic-roll',autoplay=False,shadows=i==1)
        layer=app.animation_surface_layer
        results=[]
        try:
            _present(app)
            manager.submit(app.animation_fixture.requests[0],results.append)
            manager.advance(.3)
            _step(app,6)
            before=counts(app)
            # The host detaches SceneRoot before its finalExitCallbacks. This is
            # deliberately the fallback path, not the normal composition order.
            app.destroy()
            assert len(results)==1 and results[0].status.value=='CANCELLED'
            assert GraphicsEngine.getGlobalPtr().getNumWindows()==0
            assert len(app.taskMgr.getTasks())==0
            runs.append({'iteration':i+1,'resources_before_close':before,
                'outputs_after_close':0,'tasks_after_close':0,'result':results[0].status.value,
                'subscriptions_after_close':sum(len(messenger.whoAccepts(e) or {}) for e in messenger.getEvents())})
        finally:
            manager.dispose();renderer.dispose();layer.dispose()
    return {'runs':runs,'status':'PASS'}


def terminal_visual(app,renderer,manager,output):
    images=[]
    for name in ('fall','goal'):
        fixture=get_animation_fixture(name)
        renderer,manager=load(app,renderer,manager,fixture)
        request=fixture.requests[0];manager.submit(request)
        for index,progress in enumerate((0,.5,1)):
            if index:manager.advance(request.duration*.5)
            images.append(capture(app,manager,output,f'terminal-{name}-{int(progress*100):03}',
                group=name,label=f'{name.upper()} {int(progress*100)}%',sample=progress))
        assert manager._rig._whole.isHidden(), 'Invisible terminal actor must not keep casting a shadow.'
    return renderer,manager,{'images':images,'status':'PASS'}


def autoplay_validation(app,manager,output):
    captures=[]
    deadline=time.perf_counter()+25
    while time.perf_counter()<deadline:
        _step(app,1)
        if app.animation_demo_driver.index==1 and .5<=manager.progress<.8 and not captures:
            captures.append(capture(app,manager,output,'autoplay-first-roll-middle',
                group='autoplay',label='AUTOPLAY / NOT GAMEPLAY'))
        if app.animation_demo_driver.index==len(app.animation_fixture.requests) and not manager.is_busy:
            break
        time.sleep(.001)
    else:
        raise RuntimeError('Autoplay did not finish its explicit fixture storyboard.')
    assert manager.current_snapshot==app.animation_fixture.requests[-1].after_snapshot
    owned=[task.getName() for task in app.taskMgr.getTasks() if task.getName().startswith(('AnimationDemo-','BloxorzAnimation-'))]
    assert len(owned)==1
    captures.append(capture(app,manager,output,'autoplay-complete',group='autoplay',label='DEMO COMPLETE / NOT GAMEPLAY'))
    return {'status':'PASS','requests_completed':len(app.animation_fixture.requests),
            'owned_tasks':owned,'resources':counts(app),'images':captures}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('visual','stress','profile','entrypoints','terminal','lifecycle','autoplay'),default='visual')
    parser.add_argument('--profile',choices=('idle','rolling','combined'),default='rolling')
    parser.add_argument('--shadows',action='store_true')
    parser.add_argument('--output',type=Path,default=Path('/tmp/bloxorz-stage5'))
    args=parser.parse_args(argv);args.output.mkdir(parents=True,exist_ok=True)
    if args.mode=='entrypoints':result=native_entrypoints()
    elif args.mode=='lifecycle':result=lifecycle()
    else:
        from panda3d.core import GraphicsEngine,GraphicsWindow,PandaSystem
        app,renderer,manager=create_animation_preview(autoplay=args.mode=='autoplay',shadows=args.shadows)
        try:
            assert isinstance(app.win,GraphicsWindow);_present(app)
            env={'python':sys.version,'panda':PandaSystem.getVersionString(),'platform':platform.platform(),
                'window':type(app.win).__name__,'renderer':app.win.getGsg().getDriverRenderer(),
                'driver':app.win.getGsg().getDriverVersion()}
            if args.mode=='visual':renderer,manager,result=visual(app,renderer,manager,args.output)
            elif args.mode=='stress':renderer,manager,result=stress(app,renderer,manager)
            elif args.mode=='terminal':renderer,manager,result=terminal_visual(app,renderer,manager,args.output)
            elif args.mode=='autoplay':result=autoplay_validation(app,manager,args.output)
            else:renderer,manager,result=profile(app,renderer,manager,args.output,args.profile)
            result['environment']=env
        except SystemExit as error:
            raise RuntimeError('Native preview closed before QA finished; no PASS evidence was recorded.') from error
        finally:dispose_animation_preview(app,renderer,manager)
        result['graphics_outputs_after_destroy']=GraphicsEngine.getGlobalPtr().getNumWindows()
        result['tasks_after_destroy']=len(app.taskMgr.getTasks())
        from direct.showbase.MessengerGlobal import messenger
        result['subscriptions_after_destroy']=sum(len(messenger.whoAccepts(e) or {}) for e in messenger.getEvents())
        assert result['graphics_outputs_after_destroy']==0 and result['tasks_after_destroy']==0
    filename=args.mode+('-'+args.profile if args.mode=='profile' else '')+'.json'
    (args.output/filename).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
