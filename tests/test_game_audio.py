"""Device-independent audio pool/mixer/config and authoritative animation cue regressions."""
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import wave
from src.gui.audio_events import AudioEvent as A,SOUND_BANK,THEME_SOUND_FILES,animation_cues,AnimationAudioTrack
from src.gui.audio import AudioManager
from src.gui.sound_bank import SoundBank,ROOT


class Sound:
    def __init__(self):self.playing=False;self.volume=0;self.position=.13;self.plays=0;self.stops=0
    def play(self):self.playing=True;self.plays+=1
    def stop(self):self.playing=False;self.stops+=1
    def status(self):return 2 if self.playing else 1
    def length(self):return 3.
    def setLoop(self,value):self.loop=value
    def setVolume(self,value):self.volume=value
    def setPlayRate(self,value):self.rate=value
    def getTime(self):return self.position
    def setTime(self,value):self.position=value


def backend():
    loader=SimpleNamespace(loadSfx=Mock(side_effect=lambda *a,**k:Sound()),loadMusic=Mock(side_effect=lambda *a,**k:Sound()))
    return SimpleNamespace(loader=loader,musicManager=Mock(),sfxManagerList=[Mock()],
        taskMgr=SimpleNamespace(doMethodLater=Mock(return_value='audio-task'),remove=Mock()))


class MixerTests(unittest.TestCase):
    def setUp(self):
        self.base=backend();self.now=10.
        self.a=AudioManager(self.base,music_dir='/absent-audio-playlist',clock=lambda:self.now)
        self.addCleanup(self.a.dispose);self.a.set_gameplay_active(True)

    def test_bank_prewarms_three_independent_voices_and_never_reloads_on_play(self):
        loads=self.base.loader.loadSfx.call_count
        for _ in range(30):
            handle=self.a.play_sfx(A.ROLL_IMPACT,scope='move');self.a.stop_loop(handle)
        self.assertEqual(self.base.loader.loadSfx.call_count,loads)
        self.assertEqual(len({id(s) for s in self.a.bank.sounds['impact_0']}),3)

    def test_missing_bank_is_silent_without_touching_backend(self):
        with TemporaryDirectory() as tmp:
            with self.assertLogs('src.gui.sound_bank',level='WARNING'):bank=SoundBank(self.base.loader,tmp)
            self.assertIsNone(bank.acquire('landing',set()));self.assertTrue(bank.missing)
            bank.dispose();bank.dispose()

    def test_master_group_gain_and_mute_do_not_multiply_repeatedly(self):
        handle=self.a.play_sfx(A.ROLL_IMPACT,scope='roll');v=self.a.voices[handle]
        self.a.set_master_volume(.6);self.a.set_sfx_volume(.4)
        expected=.6*.4*SOUND_BANK[A.ROLL_IMPACT].gain*v.gain
        for _ in range(10):self.a.set_master_volume(.6);self.a.set_sfx_volume(.4)
        self.assertAlmostEqual(v.sound.volume,expected)
        self.a.set_muted(True);self.assertEqual(v.sound.volume,0)
        self.assertEqual((self.a.master_volume,self.a.sfx_volume),(.6,.4))
        self.a.set_muted(False);self.assertAlmostEqual(v.sound.volume,expected)
        self.a.set_sfx_volume(float('nan'));self.assertEqual(self.a.sfx_volume,0)
        self.a.set_master_volume(9);self.assertEqual(self.a.master_volume,1)

    def test_concurrent_sfx_have_a_bounded_sum_of_output_gains(self):
        self.a.set_master_volume(1);self.a.set_sfx_volume(1)
        for e in A:
            self.now+=.1;self.a.play_sfx(e,scope=str(e))
        self.assertLessEqual(sum(v.sound.volume for v in self.a.voices.values()),.700001)

    def test_music_ambience_volumes_theme_and_muted_start(self):
        self.a.set_theme('light');first=self.a._ambience
        self.a.set_theme('light');self.assertEqual(self.a._ambience,first)
        self.a.set_theme('dark');self.assertNotIn(first,self.a.voices)
        amb=[v for v in self.a.voices.values() if SOUND_BANK[v.event].group=='ambience']
        self.assertEqual(len(amb),1);self.assertEqual(amb[0].event,A.SNOW)
        self.a.set_music_volume(.2)
        self.assertAlmostEqual(amb[0].sound.volume,self.a.master_volume*.2*.18*amb[0].gain)
        self.a.set_music_enabled(False);self.assertEqual(amb[0].sound.volume,0)
        self.a.set_music_enabled(True);self.assertGreater(amb[0].sound.volume,0)
        self.a.stop_loop(self.a._ambience);self.a.set_muted(True);self.a.set_theme('light')
        self.a.set_muted(False);self.assertIn(self.a._ambience,self.a.voices)

    def test_pause_resume_preserves_offset_ui_keeps_working_and_no_cue_redispatch(self):
        h=self.a.start_loop(A.FALL_WIND,scope=('animation','session','fall'))
        self.a.pause_gameplay_audio();voice=self.a.voices[h]
        self.assertFalse(voice.sound.playing);self.assertTrue(voice.paused)
        history=list(self.a.history)
        self.a.play_sfx(A.UI_CLICK);self.assertEqual(self.a.history[-1][0],A.UI_CLICK)
        self.a.resume_gameplay_audio();self.assertEqual(voice.sound.position,.13)
        self.assertTrue(voice.sound.playing);self.assertEqual(list(self.a.history)[:-1],history)

    def test_rate_limit_priority_pool_and_session_cleanup(self):
        self.a.play_sfx(A.UI_CLICK)
        self.assertIsNone(self.a.play_sfx(A.UI_CLICK))
        for event in A:
            self.now+=.05;self.a.play_sfx(event,scope=('animation','old',str(event)))
        self.assertLessEqual(len(self.a.voices),16)
        self.assertLessEqual(self.a.stats['max_voices'],16)
        self.a.stop_session_audio('old')
        self.assertFalse(any(SOUND_BANK[v.event].group=='gameplay' for v in self.a.voices.values()))
        self.a.set_gameplay_active(False);self.assertIsNone(self.a.play_sfx(A.GOAL_COMPLETE))
        self.assertIsNotNone(self.a.play_sfx(A.UI_BACK))
        self.a.dispose();self.a.dispose();self.assertFalse(self.a.voices)
        self.assertFalse(self.a._tracks);self.assertIsNone(self.a._base)
        self.assertEqual(self.a._tick(SimpleNamespace(done='done')),'done')
        self.a.start_music()
        self.assertIsNone(self.a.play_sfx(A.UI_CLICK));self.base.taskMgr.remove.assert_called_once()

    def test_original_assets_are_stereo_48khz_non_silent_without_clipped_samples(self):
        import array
        names={f for spec in SOUND_BANK.values() for f in spec.files}
        names.update(f for skin in THEME_SOUND_FILES.values() for choices in skin.values() for f in choices)
        for name in names:
            path=ROOT/('ambience' if name in ('jungle','snow') else 'sfx')/(name+'.wav')
            with wave.open(str(path)) as f:
                self.assertEqual((f.getframerate(),f.getnchannels(),f.getsampwidth()),(48000,2,2))
                pcm=array.array('h',f.readframes(f.getnframes()))
            self.assertGreater(max(pcm),1000);self.assertLess(max(abs(x) for x in pcm),30000)

    def test_switch_theme_skins_keep_cue_identity_and_fallback_without_loading_on_play(self):
        loads=self.base.loader.loadSfx.call_count
        for theme in ('light','dark'):
            self.a.set_theme(theme)
            for event in (A.SOFT_SWITCH,A.HEAVY_SWITCH,A.SPLIT_SWITCH):
                h=self.a.play_sfx(event,scope='switch')
                name=event.value+('_ice' if theme=='dark' else '')
                self.assertIn(self.a.voices[h].sound,self.a.bank.sounds[name])
                self.assertEqual(self.a.history[-1],(event,'switch'))
                self.a.stop_loop(h)
        self.a.bank.sounds['heavy_switch_ice']=()
        h=self.a.play_sfx(A.HEAVY_SWITCH,scope='switch')
        self.assertIn(self.a.voices[h].sound,self.a.bank.sounds['heavy_switch'])
        self.assertEqual(self.base.loader.loadSfx.call_count,loads)

    def test_audio_settings_migrate_and_validate_without_losing_progress(self):
        from src.gui.profile import SaveData
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'save.json'
            for invalid in (-2,2,float('nan'),'bad',True):
                path.write_text(json.dumps({'settings':{'master_volume':invalid,'muted':'yes'},'stars':{'test':3}}))
                save=SaveData(path);self.assertEqual(save.settings.master_volume,.8)
                self.assertFalse(save.settings.muted);self.assertEqual(save.stars_for('test'),3)
            save.settings.master_volume=.35;save.settings.muted=True;save.save()
            restored=SaveData(path);self.assertEqual(restored.settings.master_volume,.35);self.assertTrue(restored.settings.muted)


class CueContractTests(unittest.TestCase):
    def test_12_roll_poses_use_contact_threshold_not_keypress(self):
        from src.gui.animation_fixtures import get_roll_fixture
        from src.gui.animation_math import RollDirection
        from src.gui.contracts import BasicOrientation
        from src.gui.animation_contracts import as_visual_board
        for pose in BasicOrientation:
            for direction in RollDirection:
                fixture=get_roll_fixture(pose,direction)
                cues=animation_cues(fixture.requests[0],as_visual_board(fixture.board))
                self.assertEqual([(c.progress,c.event) for c in cues],[(0,A.ROLL_START),(1,A.ROLL_IMPACT)])

    def test_all_mechanics_map_distinct_types_and_teleport_phase_windows(self):
        from src.gui.animation_fixtures import get_animation_fixture
        from src.gui.animation_contracts import as_visual_board
        found=set()
        for name in ('cube-roll','bridge','switches','fragile','goal','split','merge'):
            f=get_animation_fixture(name)
            for req in f.requests:
                cues=animation_cues(req,as_visual_board(f.board));found.update(c.event for c in cues)
                if name in ('split','merge'):
                    expected=[A.TELEPORT_CHARGE,A.TELEPORT_DISASSEMBLE,A.TELEPORT_TRAVEL,A.TELEPORT_ARRIVAL,A.TELEPORT_MATERIALIZE]
                    if name=='split':expected.insert(0,A.SPLIT_SWITCH)
                    self.assertEqual([c.event for c in cues],expected)
                    self.assertEqual([c.progress for c in cues], [0,0,.24,.44,.70,.90] if name=='split' else [0,.22,.42,.66,.85])
        self.assertTrue({A.SOFT_SWITCH,A.HEAVY_SWITCH,A.SPLIT_SWITCH,A.SPLIT_CUBE_IMPACT,A.FRAGILE_CRACK,
            A.FRAGILE_BREAK,A.BRIDGE_OPEN,A.BRIDGE_CLOSE,A.GOAL_ENERGY,A.GOAL_COMPLETE}<=found)

    def test_bridge_sound_stops_at_its_own_event_end_before_request_finishes(self):
        from dataclasses import replace
        from src.gui.animation_fixtures import get_animation_fixture
        from src.gui.animation_contracts import as_visual_board
        f=get_animation_fixture('bridge');req=f.requests[0]
        req=replace(req,events=(replace(req.events[0],start=.2,end=.6),))
        audio=Mock();track=AnimationAudioTrack(audio,req,as_visual_board(f.board))
        track.sample(.19);audio.play_sfx.assert_not_called()
        track.sample(.2);audio.play_sfx.assert_called_once()
        track.sample(.59);audio.stop_scope.assert_not_called()
        track.sample(.6);audio.stop_scope.assert_called_once_with(track.scope,events={A.BRIDGE_OPEN})
        self.assertFalse(track.closed)

    def test_cancel_before_goal_completion_never_plays_victory(self):
        from src.gui.animation_fixtures import get_animation_fixture
        from src.gui.animation_contracts import as_visual_board
        f=get_animation_fixture('goal');audio=Mock()
        track=AnimationAudioTrack(audio,f.requests[0],as_visual_board(f.board))
        track.sample(.8);track.finish(False);track.sample(1)
        self.assertEqual([call.args[0] for call in audio.play_sfx.call_args_list],[A.GOAL_ENERGY])

    def test_large_dt_crosses_every_cue_once_and_repeated_samples_are_idempotent(self):
        from src.gui.animation_fixtures import get_animation_fixture
        from src.gui.animation_contracts import as_visual_board
        f=get_animation_fixture('split');audio=Mock()
        track=AnimationAudioTrack(audio,f.requests[0],as_visual_board(f.board))
        track.sample(0);track.sample(0);track.sample(1);track.sample(1);track.sample(.2)
        self.assertEqual(audio.play_sfx.call_count,6)
        track.finish(False);track.sample(1)
        self.assertEqual(audio.play_sfx.call_count,6)


from game_integration_support import GameIntegrationCase


class AudioGameplayTests(GameIntegrationCase):
    def setUp(self):
        super().setUp();self.cues=[]
        self.audio=Mock()
        self.audio.play_sfx.side_effect=lambda event,**kwargs:self.cues.append((event,kwargs['scope'])) or len(self.cues)
        self.app.game_audio=self.audio
        self.load('level_01')

    def count(self,event):return sum(e==event for e,s in self.cues)

    def test_roll_contact_one_cue_no_state_or_moves_until_real_commit(self):
        c=self.controller;state=c.state
        c.manual_move('R');self.assertEqual(self.count(A.ROLL_START),1)
        self.assertEqual(self.count(A.ROLL_IMPACT),0)
        c.manager.advance(.349);c.manager.advance(0)
        self.assertEqual(c.state,state);self.assertEqual(c.moves,0);self.assertEqual(self.count(A.ROLL_IMPACT),0)
        c.manager.advance(.001)
        self.assertEqual(self.count(A.ROLL_IMPACT),1);self.assertEqual(c.moves,1)

    def test_30_60_120_fps_and_three_playback_rates_have_identical_cue_sequence(self):
        for rate in (.25,1.,4.):
            for fps in (30,60,120):
                self.load('level_01');self.cues.clear();c=self.controller;c.set_speed(rate)
                c.manual_move('R')
                for _ in range(1000):
                    if not c.manager.is_busy:break
                    c.manager.advance(1/fps)
                self.assertEqual([e for e,s in self.cues],[A.ROLL_START,A.ROLL_IMPACT])
                self.assertEqual(c.moves,1)

    def test_void_fall_has_phase_wind_and_no_fake_contact_or_ground_impact(self):
        c=self.controller;c.manual_move('L');fall=c.manager._fall
        self.assertIsNotNone(fall)
        if fall.tip_end>0:
            c.manager.advance(fall.tip_end*.99);self.assertEqual(self.count(A.FALL_WIND),0)
        self.drain();self.assertEqual(c.phase,'FELL')
        self.assertEqual(self.count(A.FALL_WIND),1);self.assertEqual(self.count(A.ROLL_IMPACT),0)
        self.audio.set_voice_gain.assert_called()
        self.audio.stop_scope.assert_any_call(self.cues[-1][1],loops_only=True)

    def test_fragile_switch_bridge_and_split_merge_follow_real_core_events(self):
        for level,cue in (('level_03_soft_bridge',A.SOFT_SWITCH),('level_04_heavy_bridge',A.HEAVY_SWITCH)):
            self.load(level);self.cues.clear();self.move('R');self.move('R')
            self.assertEqual(self.count(cue),1);self.assertEqual(self.count(A.BRIDGE_OPEN),1)
        self.load('level_07_fragile_detour');self.cues.clear();self.move('R');self.move('R')
        self.assertEqual(self.controller.phase,'FELL')
        for event in (A.FRAGILE_CRACK,A.FRAGILE_BREAK,A.FALL_WIND):self.assertEqual(self.count(event),1)
        self.load('level_05_split');self.cues.clear()
        self.move('R');self.move('R');self.move('SPACE');self.move('R')
        self.assertEqual(self.count(A.SPLIT_SWITCH),1)
        self.assertEqual(self.count(A.TELEPORT_ARRIVAL),2) # one split and one merge, not per cube
        self.assertEqual(self.count(A.SPLIT_CUBE_IMPACT),1)
        self.assertFalse(self.controller.state.is_split())

    def test_six_solver_replays_use_same_cues_and_goal_only_once(self):
        from src.gui.controller import SOLVER_SPECS
        for name in SOLVER_SPECS:
            self.load('level_05_split');self.cues.clear()
            self.controller.select_solver(name);self.controller.start_guide('play');self.drain()
            self.assertEqual(self.controller.phase,'GOAL')
            self.assertEqual(self.count(A.GOAL_COMPLETE),1)
            self.assertEqual(self.count(A.GOAL_ENERGY),1)
            self.assertGreaterEqual(self.count(A.TELEPORT_CHARGE),2)

    def test_pause_resume_cancel_restart_level_change_dispose_and_no_stale_cue(self):
        c=self.controller;c.manual_move('R');track=c.manager._audio_track
        c.manager.pause();c.manager.advance(5);self.assertEqual(self.count(A.ROLL_IMPACT),0)
        self.audio.pause_gameplay_audio.assert_called_once()
        c.manager.resume();self.audio.resume_gameplay_audio.assert_called_once()
        c.restart_level();track.sample(1);self.assertEqual(self.count(A.ROLL_IMPACT),0)
        self.audio.stop_session_audio.assert_called()
        c.manual_move('R');track=c.manager._audio_track
        self.load('level_03_soft_bridge');track.sample(1)
        self.assertEqual(self.count(A.ROLL_IMPACT),0)
        c=self.controller;c.manual_move('R');track=c.manager._audio_track;c.dispose();track.sample(1)
        self.assertEqual(self.count(A.ROLL_IMPACT),0)

    def test_audio_backend_fault_cannot_fail_a_gameplay_move(self):
        self.audio.play_sfx.side_effect=RuntimeError('device removed')
        with self.assertLogs('src.gui.animation_manager',level='ERROR'):self.move('R')
        self.assertEqual(self.controller.moves,1);self.assertEqual(self.controller.phase,'READY')


class OpeningAudioTests(unittest.TestCase):
    def setUp(self):
        from panda3d.core import NodePath
        from src.gui.level_intro import LevelIntro
        from src.gui.mesh_factory import make_block_mesh,make_floor_mesh
        self.root=NodePath('intro-audio-test');self.addCleanup(self.root.removeNode)
        app=SimpleNamespace(render=self.root,taskMgr=Mock(),
            static_board_root=self.root.attachNewNode('static'),
            dynamic_tile_root=self.root.attachNewNode('dynamic'),
            block_root=self.root.attachNewNode('block'))
        floor=app.static_board_root.attachNewNode(make_floor_mesh());floor.setTag('cell','0,0')
        app.block_root.attachNewNode(make_block_mesh())
        self.audio=Mock();self.intro=LevelIntro(app,audio=self.audio)
        self.addCleanup(self.intro.finish)

    def test_impact_waits_for_actual_intro_contact_and_is_not_replayed_by_sampling(self):
        from unittest.mock import patch
        task=SimpleNamespace(cont='cont',done='done')
        clock=SimpleNamespace(getDt=lambda:.05)
        self.intro.play(1,1)
        with patch('src.gui.level_intro.ClockObject',SimpleNamespace(getGlobalClock=lambda:clock)):
            while not self.intro._dropping:self.intro._update(task)
            self.assertNotIn('opening_landing',[c.args[0] for c in self.audio.play_sfx.call_args_list])
            while not self.intro._landed:self.intro._update(task)
            self.intro._land();self.intro._update(task)
        self.assertEqual([c.args[0] for c in self.audio.play_sfx.call_args_list],['opening_wind','opening_landing'])
        self.audio.stop_loop.assert_called_once()

    def test_skipped_intro_and_stale_cancelled_callback_cannot_emit_landing(self):
        self.intro.play(1,1);scope=self.intro._audio_scope
        self.intro.finish()
        self.assertEqual(self.intro._update(SimpleNamespace(done='done')),'done')
        self.audio.play_sfx.assert_not_called()
        self.audio.stop_scope.assert_called_with(scope)
