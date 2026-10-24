"""Volume control plus procedurally synthesised sound (stdlib only, no licensed files).

Sounds are generated once into assets/audio/*.wav and reused afterwards.
Background music: tracks in music/ (1.mp3, 2.mp3, ...) play one after another in a loop.
"""
import math
import random
import struct
import tempfile
import wave
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


class AudioManager:
    """Hai kênh riêng: nhạc nền và hiệu ứng (lăn, click, thắng, thua).

    Mỗi kênh có công tắc bật/tắt và âm lượng độc lập, nên tắt nhạc thì tiếng game vẫn còn.
    Nhạc nền: phát ngẫu nhiên các bài trong music/, không lặp lại cùng một bài liên tiếp.
    Nếu không đọc được bài nào thì dùng music.wav tự tạo như cũ.
    Silent (not crashing) without an audio device.
    """

    MUSIC_SHARE = .6
    TICK = .5          # giây giữa 2 lần kiểm tra bài hết

    def __init__(self, base, directory=DEFAULT_DIR, music_volume=.7, sfx_volume=.7,
                 music_enabled=True, sfx_enabled=True, music_dir=MUSIC_DIR):
        from panda3d.core import Filename
        self._base = base
        paths = ensure_assets(directory)

        def path(name):
            return Filename.fromOsSpecific(str(paths[name]))

        self._sfx = {name: base.loader.loadSfx(path(name)) for name in SFX_NAMES}

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
        return min(1.0, max(0.0, float(value)))

    def set_music_volume(self, value):
        self.music_volume = self._clamp(value)
        self._base.musicManager.setVolume(self.music_volume * self.MUSIC_SHARE)

    def set_sfx_volume(self, value):
        self.sfx_volume = self._clamp(value)
        for manager in self._base.sfxManagerList:
            manager.setVolume(self.sfx_volume)

    # ------------------------------------------------------------ sfx
    def play(self, name):
        if not self.sfx_enabled:
            return
        sound = self._sfx.get(name)
        if sound is not None:
            sound.play()

    def set_sfx_enabled(self, enabled):
        self.sfx_enabled = bool(enabled)
        if not self.sfx_enabled:
            for sound in self._sfx.values():
                sound.stop()

    def toggle_sfx(self):
        self.set_sfx_enabled(not self.sfx_enabled)
        return self.sfx_enabled

    # ------------------------------------------------------------ music
    def _is_playing(self):
        from panda3d.core import AudioSound
        return self._tracks[self._current].status() == AudioSound.PLAYING

    def start_music(self):
        """An toàn khi gọi nhiều lần: không phát lại nếu đang chạy."""
        self._wanted = True
        if self.music_enabled and not self._is_playing():
            self._tracks[self._current].play()

    def set_music_enabled(self, enabled):
        self.music_enabled = bool(enabled)
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
        if self._wanted and self.music_enabled and not self._is_playing():
            self._current = self._pick_next()
            self._tracks[self._current].play()
        return task.again

    def dispose(self):
        self._base.taskMgr.remove(self._task)
        for track in self._tracks:
            track.stop()
        for sound in self._sfx.values():
            sound.stop()