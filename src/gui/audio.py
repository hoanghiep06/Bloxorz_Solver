"""Unified presentation mixer, bounded SoundBank and preserved background playlist.

Cinematic SFX are authored offline by tools.build_game_audio; legacy synthesis below
is retained only for compatibility and the original fallback music.
"""
import math
import random
import struct
import tempfile
import wave
import time
from collections import deque
from dataclasses import dataclass
from src.gui.audio_events import AudioEvent, SOUND_BANK, THEME_SOUND_FILES
from src.gui.sound_bank import SoundBank
from pathlib import Path

RATE, MUSIC_RATE = 22050, 11025
DEFAULT_DIR = Path(__file__).resolve().parents[2] / 'assets' / 'audio'
SFX_NAMES = ('click', 'roll', 'goal', 'fall')
MUSIC_DIR = Path(__file__).resolve().parents[2] / 'music'   # đổi thành 'assets' / 'music' nếu cần
MUSIC_EXTS = ('.mp3', '.ogg', '.wav')


def find_playlist(directory=MUSIC_DIR):
    """Các file nhạc trong thư mục, xếp 1, 2, 3... rồi đến tên chữ."""
    folder = Path(directory)
    if not folder.is_dir():
        return []

    def key(path):
        return (0, int(path.stem), '') if path.stem.isdigit() else (1, 0, path.stem.lower())

    return sorted((p for p in folder.iterdir() if p.suffix.lower() in MUSIC_EXTS), key=key)


def _note(freq, duration, volume, decay, freq_end=None, rate=RATE):
    count = int(duration * rate)
    end = freq if freq_end is None else freq_end
    phase, out = 0.0, []
    for i in range(count):
        phase += 2 * math.pi * (freq + (end - freq) * i / count) / rate
        attack = min(1.0, i / (.004 * rate))
        release = min(1.0, (count - i) / (.01 * rate))
        out.append(math.sin(phase) * volume * math.exp(-decay * i / rate) * attack * release)
    return out


def _click():
    return _note(880, .07, .35, 45)


def _roll():
    return _note(120, .16, .7, 20, 55)


def _fall():
    return _note(520, .6, .4, 2.5, 80)


def _goal():
    samples = []
    for freq, length in ((523.25, .14), (659.25, .14), (783.99, .14), (1046.5, .6)):
        samples += _note(freq, length, .4, 5)
    return samples


# Am - F - C - G pads, one octave low. Frequencies snap to 1/16 Hz so every
# partial completes whole cycles in 16 s and the loop has no seam click.
_CHORDS = ((110.0, 130.81, 164.81), (87.31, 110.0, 130.81),
           (130.81, 164.81, 196.0), (98.0, 123.47, 146.83))


def _music():
    seconds, per = 16, 4
    chords = [[round(f * 16) / 16 for f in chord] for chord in _CHORDS]
    out = []
    for i in range(seconds * MUSIC_RATE):
        t = i / MUSIC_RATE
        value = 0.0
        for k, chord in enumerate(chords):
            d = (t - (per * k + per / 2) + seconds / 2) % seconds - seconds / 2
            if abs(d) >= per:
                continue
            weight = math.cos(math.pi * d / (2 * per)) ** 2   # overlapping windows sum to 1
            value += weight * sum(math.sin(2 * math.pi * f * t) + .3 * math.sin(4 * math.pi * f * t)
                                  for f in chord)
        out.append(value * .09)
    return out


def _write(path, samples, rate):
    data = struct.pack('<%dh' % len(samples),
                       *[int(max(-1.0, min(1.0, s)) * 32767) for s in samples])
    with wave.open(str(path), 'wb') as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(data)


def ensure_assets(directory=DEFAULT_DIR):
    """Create missing WAV files and return {name: Path}; falls back to a temp dir."""
    makers = {'click': (_click, RATE), 'roll': (_roll, RATE), 'goal': (_goal, RATE),
              'fall': (_fall, RATE), 'music': (_music, MUSIC_RATE)}
    try:
        folder = Path(directory)
        folder.mkdir(parents=True, exist_ok=True)
        paths = {}
        for name, (make, rate) in makers.items():
            path = folder / f'{name}.wav'
            if not path.exists():
                _write(path, make(), rate)
            paths[name] = path
        return paths
    except OSError:
        fallback = Path(tempfile.gettempdir()) / 'bloxorz_audio'
        if Path(directory) == fallback:
            raise
        return ensure_assets(fallback)


@dataclass
class Voice:
    sound: object
    event: AudioEvent
    scope: object
    gain: float=1.
    paused: bool=False
    offset: float=0.


class AudioManager:
    """One presentation mixer for scoped gameplay, UI, ambience and existing music.

    A bounded prewarmed pool supplies SFX; the original music playlist/fallback
    remains independent. No gameplay clock, rules or state are owned here.
    """

    MUSIC_SHARE = .6
    TICK = .025        # voice maintenance; playlist checks are throttled to .5 s

    def __init__(self, base, directory=DEFAULT_DIR, music_volume=.7, sfx_volume=.7,
                 music_enabled=True, sfx_enabled=True, music_dir=MUSIC_DIR,
                 master_volume=.8, muted=False, seed=193, clock=time.monotonic):
        from panda3d.core import Filename
        self._base = base
        paths = ensure_assets(directory)

        def path(name):
            return Filename.fromOsSpecific(str(paths[name]))

        self.bank=SoundBank(base.loader,directory)
        self.voices={};self._serial=0;self._disposed=False
        self._clock=clock;self._rng=random.Random(seed);self._last_ui=-float('inf')
        self.history=deque(maxlen=512)
        self.stats={'played':0,'dropped':0,'max_voices':0}
        self.gameplay_active=False;self.master_volume=self._clamp(master_volume)
        self.muted=bool(muted);self.ambience_volume=self._clamp(music_volume)
        self._ambience=None;self._theme=None;self._playlist_check=0.
        self._paused_scopes=set()
        for manager in base.sfxManagerList:manager.setVolume(1.)

        self._tracks = []
        for file in find_playlist(music_dir):
            sound = base.loader.loadMusic(Filename.fromOsSpecific(str(file)))
            if sound.length() > 0:          # NullAudioSound (không giải mã được) có length = 0
                self._tracks.append(sound)
        if not self._tracks:                 # dự phòng: nhạc tổng hợp cũ
            fallback = base.loader.loadMusic(path('music'))
            fallback.setLoop(True)
            self._tracks = [fallback]

        self.music_enabled = bool(music_enabled)
        self.sfx_enabled = bool(sfx_enabled)
        self._current = random.randrange(len(self._tracks))   # bài mở đầu ngẫu nhiên
        self._wanted = False                 # start_music() đã được gọi chưa
        self.music_volume = self.sfx_volume = 0.0
        self.set_music_volume(music_volume)
        self.set_sfx_volume(sfx_volume)
        self._task = base.taskMgr.doMethodLater(self.TICK, self._tick, 'audio-playlist')

    # ------------------------------------------------------------ volume
    @staticmethod
    def _clamp(value):
        value=float(value)
        return min(1.0,max(0.0,value)) if math.isfinite(value) else 0.

    def set_music_volume(self, value):
        self.music_volume = self._clamp(value)
        self.ambience_volume=self.music_volume
        self._mix()

    def set_sfx_volume(self, value):
        self.sfx_volume = self._clamp(value)
        self._mix()

    def set_master_volume(self,value):
        self.master_volume=self._clamp(value);self._mix()

    def set_ambience_volume(self,value):
        self.ambience_volume=self._clamp(value);self._mix()

    def set_muted(self,value):
        self.muted=bool(value)
        if not self.muted and self._theme and self._ambience not in self.voices:
            theme=self._theme;self._theme=None;self.set_theme(theme)
        self._mix()

    def _mix(self):
        if self._disposed or not hasattr(self,'_tracks'):return
        gains={}
        for key,v in self.voices.items():
            spec=SOUND_BANK[v.event]
            group=(self.ambience_volume if self.music_enabled else 0.) if spec.group=='ambience' else (self.sfx_volume if self.sfx_enabled else 0.)
            gains[key]=group*spec.gain*v.gain
        # Sum-of-gains budget prevents correlated, overlapping transients clipping.
        budget=.5 if self.music_enabled and self._wanted else .7
        headroom=min(1.,budget/max(sum(gains.values()),1e-9))
        duck=.55 if any(SOUND_BANK[v.event].priority>=4 for v in self.voices.values()) else 1.
        master=0. if self.muted else self.master_volume
        self._base.musicManager.setVolume(master*self.music_volume*self.MUSIC_SHARE*duck)
        for key,v in self.voices.items():
            v.sound.setVolume(master*gains[key]*headroom)

    def play(self,name):
        # Compatibility for existing menu buttons; gameplay now belongs to timeline cues.
        event={'click':AudioEvent.UI_CLICK,'roll':AudioEvent.ROLL_START,
               'goal':AudioEvent.GOAL_COMPLETE,'fall':AudioEvent.FALL_WIND}.get(name,name)
        return self.play_sfx(event)

    def play_sfx(self,event,*,scope=None):
        if self._disposed:return None
        event=AudioEvent(event);spec=SOUND_BANK[event]
        if spec.group=='gameplay' and not self.gameplay_active:return None
        if self.muted or (spec.group!='ambience' and not self.sfx_enabled):return None
        now=self._clock()
        if spec.group=='ui':
            if now-self._last_ui<.035:return None
            self._last_ui=now
        self._reap()
        # Bounded 16 voices, preferentially preserve gameplay over ambience/UI.
        if len(self.voices)>=16:
            candidates=[k for k,v in self.voices.items() if SOUND_BANK[v.event].priority<spec.priority]
            if not candidates:self.stats['dropped']+=1;return None
            self.stop_loop(candidates[0])
        choices=THEME_SOUND_FILES.get(self._theme,{}).get(event,spec.files)
        if not any(self.bank.sounds.get(name) for name in choices):choices=spec.files
        name=self._rng.choice(choices)
        sound=self.bank.acquire(name,{id(v.sound) for v in self.voices.values()})
        if sound is None:self.stats['dropped']+=1;return None
        self._serial+=1;handle=self._serial
        self.voices[handle]=Voice(sound,event,scope,gain=self._rng.uniform(.95,1.))
        sound.setLoop(spec.loop)
        sound.setPlayRate(1. if spec.loop else self._rng.uniform(.97,1.03))
        self._mix();sound.play()
        if scope in self._paused_scopes:self.pause_scope(scope)
        self.history.append((event,scope));self.stats['played']+=1
        self.stats['max_voices']=max(self.stats['max_voices'],len(self.voices))
        return handle

    start_loop=play_sfx

    def stop_loop(self,handle):
        v=self.voices.pop(handle,None)
        if v:v.sound.stop()

    def set_voice_gain(self,handle,gain):
        if handle in self.voices:self.voices[handle].gain=self._clamp(gain);self._mix()

    def stop_scope(self,scope,*,loops_only=False,events=None):
        for k,v in tuple(self.voices.items()):
            if v.scope==scope and (not loops_only or SOUND_BANK[v.event].loop) and (events is None or v.event in events):self.stop_loop(k)
        self._paused_scopes.discard(scope)
        self._mix()

    def pause_scope(self,scope):
        self._paused_scopes.add(scope)
        for v in self.voices.values():
            if v.scope==scope and not v.paused:
                v.offset=v.sound.getTime();v.sound.stop();v.paused=True

    def resume_scope(self,scope):
        self._paused_scopes.discard(scope)
        for v in self.voices.values():
            if v.scope==scope and v.paused:
                v.sound.play();v.sound.setTime(v.offset);v.paused=False

    def pause_gameplay_audio(self):
        for scope in {v.scope for v in self.voices.values() if SOUND_BANK[v.event].group=='gameplay'}:self.pause_scope(scope)

    def resume_gameplay_audio(self):
        for scope in tuple(self._paused_scopes):self.resume_scope(scope)

    def stop_session_audio(self,session_id=None):
        for k,v in tuple(self.voices.items()):
            if SOUND_BANK[v.event].group=='gameplay' and (session_id is None or
                isinstance(v.scope,tuple) and len(v.scope)>1 and v.scope[1]==session_id):self.stop_loop(k)
        self._paused_scopes.intersection_update(v.scope for v in self.voices.values())
        self._mix()

    def set_gameplay_active(self,active):
        self.gameplay_active=bool(active)
        if not active:self.stop_session_audio()

    def set_theme(self,theme):
        if theme==self._theme:return
        self._theme=theme
        self.stop_loop(self._ambience)
        self._ambience=self.play_sfx(AudioEvent.SNOW if theme=='dark' else AudioEvent.JUNGLE,scope='ambience')

    def set_sfx_enabled(self,enabled):
        self.sfx_enabled=bool(enabled)
        if not self.sfx_enabled:
            for k,v in tuple(self.voices.items()):
                if SOUND_BANK[v.event].group!='ambience':self.stop_loop(k)
        self._mix()

    def toggle_sfx(self):
        self.set_sfx_enabled(not self.sfx_enabled)
        return self.sfx_enabled

    def _reap(self):
        from panda3d.core import AudioSound
        for k,v in tuple(self.voices.items()):
            if not v.paused and not SOUND_BANK[v.event].loop and v.sound.status()!=AudioSound.PLAYING:self.voices.pop(k,None)

    # ------------------------------------------------------------ music
    def _is_playing(self):
        from panda3d.core import AudioSound
        return self._tracks[self._current].status() == AudioSound.PLAYING

    def start_music(self):
        """An toàn khi gọi nhiều lần: không phát lại nếu đang chạy."""
        if self._disposed:return
        self._wanted = True
        if self.music_enabled and not self._is_playing():
            self._tracks[self._current].play()

    def set_music_enabled(self, enabled):
        self.music_enabled = bool(enabled)
        self._mix()
        if self.music_enabled:
            if self._wanted:
                self.start_music()
        else:
            for track in self._tracks:
                track.stop()

    def toggle_music(self):
        self.set_music_enabled(not self.music_enabled)
        return self.music_enabled

    def _pick_next(self):
        """Chọn ngẫu nhiên một bài khác bài vừa phát (nếu có từ 2 bài trở lên)."""
        others = [i for i in range(len(self._tracks)) if i != self._current]
        return random.choice(others) if others else self._current

    def _tick(self, task):
        """Bài hiện tại phát xong thì chuyển bài kế tiếp (vòng tròn)."""
        if self._disposed:return task.done
        self._reap();self._mix()
        now=self._clock()
        if now-self._playlist_check<.5:return task.again
        self._playlist_check=now
        if self._wanted and self.music_enabled and not self._is_playing():
            self._current = self._pick_next()
            self._tracks[self._current].play()
        return task.again

    def dispose(self):
        if self._disposed:return
        self._disposed=True
        self._base.taskMgr.remove(self._task)
        for track in self._tracks:track.stop()
        self._tracks.clear()
        for handle in tuple(self.voices):self.stop_loop(handle)
        self._paused_scopes.clear();self.bank.dispose()
        self._base=None
