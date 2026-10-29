"""Bounded prewarmed Panda3D AudioSound pool; missing assets degrade silently."""
from pathlib import Path
import logging
from src.gui.audio_events import SOUND_BANK, THEME_SOUND_FILES

log=logging.getLogger(__name__)
ROOT=Path(__file__).resolve().parents[2]/'assets/audio'


class SoundBank:
    def __init__(self,loader,directory=ROOT,copies=3):
        from panda3d.core import Filename
        self.sounds={};self.missing=[];self.loads=0
        files={f for spec in SOUND_BANK.values() for f in spec.files}
        files.update(f for skin in THEME_SOUND_FILES.values() for choices in skin.values() for f in choices)
        for name in sorted(files):
            path=Path(directory)/('ambience' if name in ('jungle','snow') else 'sfx')/(name+'.wav')
            if not path.is_file():self.missing.append(str(path));continue
            pool=[]
            for _ in range(copies):
                try:sound=loader.loadSfx(Filename.fromOsSpecific(str(path)),positional=False)
                except Exception:
                    log.exception('Could not decode audio asset %s',path);break
                if sound is not None:pool.append(sound);self.loads+=1
            self.sounds[name]=tuple(pool)
        if self.missing:log.warning('Missing audio assets; affected cues are silent: %s',self.missing)

    def acquire(self,name,busy):
        return next((sound for sound in self.sounds.get(name,()) if id(sound) not in busy),None)

    def dispose(self):
        for pool in self.sounds.values():
            for sound in pool:sound.stop()
        self.sounds.clear()
