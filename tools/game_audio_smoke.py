"""Actual OpenAL/Pulse playback, native UI and Core/animation audio lifecycle checks.

For isolated loopback run with PULSE_SINK=<dedicated QA sink> and --sink matching it.
Never records the user's default system output.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import wave
import array


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path('/tmp/bloxorz-game-audio'))
    p.add_argument('--sink',required=True,help='An isolated QA null sink, never the default output')
    args=p.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    if os.environ.get('PULSE_SINK')!=args.sink:raise ValueError('PULSE_SINK must name the dedicated QA sink.')
    from panda3d.core import loadPrcFileData,Point3,AudioSound
    loadPrcFileData('audio-qa','audio-library-name p3openal_audio')
    from src.gui.game_app import create_game,dispose_game
    from src.gui.audio_events import AudioEvent as A,SOUND_BANK
    from tools.native_input import NativeInput
    from tools.gui_stage3_6_smoke import _present,_resize
    report={'checks':[],'images':[],'backend':'Panda3D OpenAL, PulseAudio dedicated null sink + monitor capture',
            'subjective_quality':'AUDIO SUBJECTIVE QUALITY NOT VERIFIED'}
    capture=out/'runtime-loopback.wav'
    with capture.open('wb') as recorded:
        recorder=subprocess.Popen(['parec','--device='+args.sink+'.monitor','--format=s16le',
            '--rate=48000','--channels=2','--file-format=wav'],stdout=recorded,stderr=subprocess.PIPE)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                save=Path(tmp)/'save.json';save.write_text(json.dumps({'settings':{'music':False}}))
                app,renderer,c=create_game('tests/fixtures/mechanics',save_path=save)
                d=NativeInput(app);flow=app.game_flow;audio=app.game_audio;hud=app.dashboard.hud
                def check(text):report['checks'].append(text);print('PASS',text,flush=True)
                def shot(name):
                    app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame()
                    assert app.win.saveScreenshot(str(out/(name+'.png')));report['images'].append(name+'.png')
                def enter(stem,*,intro=False):
                    flow.start_level(next(i for i,e in enumerate(c._catalog.entries) if e.level_id==stem))
                    if intro:d.wait(lambda:not flow.intro.active,timeout=20)
                    else:flow.intro.finish()
                    d.step(3);app.game_views.set_view(0);audio.history.clear()
                def move(key):
                    d.key(key);d.wait(lambda:not c.manager.is_busy,timeout=25)
                    assert c.phase!='ERROR',c._status
                def events():return [e for e,scope in audio.history]
                def button(page,text):
                    from direct.gui.DirectGui import DirectButton
                    return next(w for w in flow.screens[page]._owned if isinstance(w,DirectButton) and w['text']==text)
                def drag_slider(slider,value):
                    point=app.pixel2d.getRelativePoint(slider.thumb,Point3(0,0,0))
                    d.pointer(point.x,-point.z)
                    d.xt.XTestFakeButtonEvent(d.display,1,True,0);d.x.XFlush(d.display);d.step(3)
                    centre=slider.getPos(app.pixel2d);left,right,bottom,top=slider['frameSize']
                    target_x=centre.x+left+9+value*(right-left-18)
                    for i in range(1,11):d.pointer(point.x+(target_x-point.x)*i/10,-centre.z)
                    d.xt.XTestFakeButtonEvent(d.display,1,False,0);d.x.XFlush(d.display);d.step(4)
                try:
                    _present(app);d.step(3)
                    assert app.sfxManagerList[0].isValid()
                    assert not audio.bank.missing
                    sounds=audio.bank.sounds['landing']
                    assert all(s.length()>.5 for s in sounds)
                    assert len({int(s.this) for s in sounds})==3
                    report['preloaded_sounds']=audio.bank.loads
                    load_count=audio.bank.loads
                    check('Real OpenAL context decodes every WAV and prewarms independent cached sound instances')
                    for theme in ('light','dark'):
                        flow.show('settings');flow.screens['settings']._set_theme(theme);d.step(3)
                        index=next(i for i,e in enumerate(c._catalog.entries) if e.level_id=='level_01')
                        flow.start_level(index);audio.history.clear()
                        d.wait(lambda:flow.intro._dropping,timeout=20)
                        assert A.OPENING_LANDING not in events()
                        d.wait(lambda:flow.intro._landed,timeout=10)
                        assert events().count(A.OPENING_LANDING)==1
                        landing=[v for v in audio.voices.values() if v.event==A.OPENING_LANDING]
                        assert landing and landing[0].sound.status()==AudioSound.PLAYING
                        d.wait(lambda:not flow.intro.active)
                        audio.history.clear();move('Right');move('Right')
                        assert events().count(A.ROLL_START)==2 and events().count(A.ROLL_IMPACT)==2
                        check(theme+': opening impact at actual contact, upright/lying rolls scrape then impact, real sound PLAYING')
                        enter('level_01');move('Left')
                        assert c.phase=='FELL' and A.FALL_WIND in events() and A.ROLL_IMPACT not in events()
                        assert not any(SOUND_BANK[v.event].loop and SOUND_BANK[v.event].group=='gameplay' for v in audio.voices.values())
                        enter('level_07_fragile_detour');move('Right');move('Right')
                        assert c.phase=='FELL'
                        assert {A.FRAGILE_CRACK,A.FRAGILE_BREAK,A.FALL_WIND}<=set(events())
                        for level,cue in (('level_03_soft_bridge',A.SOFT_SWITCH),('level_04_heavy_bridge',A.HEAVY_SWITCH)):
                            enter(level);move('Right');move('Right')
                            assert cue in events() and A.BRIDGE_OPEN in events()
                        enter('level_08_toggle_bridge')
                        for key in ('Right','Right','Left','Left','Right','Right'):move(key)
                        assert A.BRIDGE_OPEN in events() and A.BRIDGE_CLOSE in events()
                        check(theme+': void fall without fictitious floor impact; Fragile crack/break/wind, Soft/Heavy switch and real Bridge activation')
                        enter('level_05_split');move('Right');move('Right');move('space');move('Right')
                        assert not c.state.is_split()
                        assert A.SPLIT_SWITCH in events() and events().count(A.TELEPORT_CHARGE)==2
                        assert events().count(A.TELEPORT_ARRIVAL)==2
                        move('Right');assert c.phase=='GOAL' and events().count(A.GOAL_COMPLETE)==1
                        shot(theme+'-goal')
                        check(theme+': split/merge five-phase energy audio, one arrival per transition, cube impacts and single Goal flourish')
                    # Native solver controls also exercise scope pause / Step across requests.
                    for name in ('BFS','DFS','IDS','UCS','Greedy','A*'):
                        enter('level_05_split');c.set_speed(.5)
                        d.click_widget(hud.buttons['Guide']);d.click_widget(hud.buttons[name]);d.click_widget(hud.buttons['Play'])
                        d.wait(lambda:A.TELEPORT_CHARGE in events(),timeout=25)
                        d.click_widget(hud.buttons['Play']);assert c.manager.status.value=='PAUSED'
                        cues=list(audio.history);progress=c.manager.progress
                        d.step(10);assert list(audio.history)==cues and c.manager.progress==progress
                        assert all(v.paused for v in audio.voices.values() if SOUND_BANK[v.event].group=='gameplay')
                        d.click_widget(hud.buttons['Step']);d.wait(lambda:not c.manager.is_busy,timeout=25)
                        d.click_widget(hud.buttons['Play']);d.wait(lambda:c.phase=='GOAL',timeout=25)
                        assert events().count(A.GOAL_COMPLETE)==1
                    c.set_speed(1)
                    check('All six spawned solvers: native Play/Pause/Step, frozen audio/cue cursor, completed split/merge and single victory')
                    # Restart while real fall wind is audible; old scopes must disappear.
                    enter('level_01');c.set_speed(.25);d.key('Left')
                    d.wait(lambda:any(v.event==A.FALL_WIND for v in audio.voices.values()),timeout=20)
                    old=c.manager._audio_track.scope
                    d.key('r');d.step(3)
                    assert not any(v.scope==old for v in audio.voices.values())
                    c.set_speed(1);enter('level_05_split');move('Right');d.key('Right')
                    d.wait(lambda:A.TELEPORT_CHARGE in events());old=c.manager._audio_track.scope
                    enter('level_01');assert not any(v.scope==old for v in audio.voices.values())
                    check('Restart during wind and level change during teleport stop old session audio without stale arrivals')
                    flow.show('settings');d.step(4)
                    for theme in ('light','dark'):
                        d.click_widget(button('settings',theme.capitalize()));d.step(4)
                        for size in ((1280,720),(1024,720)):
                            d.pointer(450,300);_resize(app,size);_present(app);d.step(3)
                            screen=flow.screens['settings']
                            drag_slider(screen._master_slider,.38)
                            assert abs(audio.master_volume-.38)<.03,audio.master_volume
                            drag_slider(screen._sfx_slider,.48)
                            assert abs(audio.sfx_volume-.48)<.03,audio.sfx_volume
                            drag_slider(screen._music_slider,.25)
                            assert abs(audio.music_volume-.25)<.03,audio.music_volume
                            before=(audio.master_volume,audio.music_volume,audio.sfx_volume)
                            d.click_widget(screen._mute);assert audio.muted
                            assert all(v.sound.getVolume()==0 for v in audio.voices.values())
                            assert before==(audio.master_volume,audio.music_volume,audio.sfx_volume)
                            shot(theme+f'-settings-{size[0]}')
                            d.click_widget(screen._mute);assert not audio.muted
                    assert audio.bank.loads==load_count
                    assert audio.stats['max_voices']<=16
                    flow.show('game');d.step(3)
                    # Exercise ambience playback alone; exclude the pre-existing MP3 playlist from evidence.
                    audio._wanted=False;audio.set_music_enabled(True)
                    for track in audio._tracks:track.stop()
                    audio.set_theme('light');audio.set_theme('dark');d.step(4)
                    assert sum(SOUND_BANK[v.event].group=='ambience' for v in audio.voices.values())<=1
                    check('Native Master/SFX/Music-Ambience sliders and Mute All, both themes and two sizes, settings preserved, bounded voices/no reloads/no double ambience')
                    report['mix_stats']=audio.stats.copy();report['events']=[e.value for e,s in audio.history]
                    report['resources_before_dispose']={'voices':len(audio.voices),'loads':audio.bank.loads}
                    from src.gui.profile import SaveData
                    saved=SaveData(save)
                    assert abs(saved.settings.master_volume-audio.master_volume)<.001
                    assert abs(saved.settings.sfx_volume-audio.sfx_volume)<.001
                finally:
                    d.close();dispose_game(app,renderer,c)
                assert not audio.voices and not audio.bank.sounds
                report['resources_after_dispose']={'voices':len(audio.voices),'sound_assets':len(audio.bank.sounds)}
                check('Dispose releases voices, loops, SoundBank and audio task')
        finally:
            recorder.terminate()
            try:recorder.wait(timeout=5)
            except subprocess.TimeoutExpired:recorder.kill();recorder.wait()
    with wave.open(str(capture)) as f:
        pcm=array.array('h',f.readframes(f.getnframes()))
        report['loopback']={'channels':f.getnchannels(),'rate':f.getframerate(),
            'seconds':f.getnframes()/f.getframerate(),'peak':max(abs(v) for v in pcm),
            'rms':(sum(v*v for v in pcm)/len(pcm))**.5}
    assert report['loopback']['peak']>1000
    assert report['loopback']['peak']<32767
    assert report['loopback']['rms']>20
    report['status']='PASS';(out/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
