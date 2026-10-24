"""Persistent settings and per-level progress. Pure Python, no engine imports."""
import json
import math
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SAVE = Path.home() / '.bloxorz_solver' / 'save.json'
CONTROL_MODES = ('keyboard', 'mouse')
THEMES = ('light', 'dark')


@dataclass
class Settings:
    control_mode: str = 'keyboard'
    theme: str = 'light'
    music: bool = True
    music_volume: float = 0.7
    sfx: bool = True
    sfx_volume: float = 0.7


def star_rating(moves, par):
    """3 stars at or under par (optimal), 2 within 1.5x par, otherwise 1.

    Unknown par (no solver can solve the level) counts as 3 stars.
    """
    if par is None or moves <= par:
        return 3
    return 2 if moves <= math.ceil(par * 1.5) else 1


def _int_map(value):
    if not isinstance(value, dict):
        return {}
    return {k: v for k, v in value.items() if isinstance(k, str) and type(v) is int and v >= 0}


class SaveData:
    def __init__(self, path=DEFAULT_SAVE):
        self.path = Path(path)
        self.settings = Settings()
        self.stars, self.best_moves, self.par = {}, {}, {}
        self.load()

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        settings = data.get('settings')
        if isinstance(settings, dict):
            if settings.get('control_mode') in CONTROL_MODES:
                self.settings.control_mode = settings['control_mode']
            if settings.get('theme') in THEMES:
                self.settings.theme = settings['theme']
            legacy = settings.get('volume')            # save cũ: một âm lượng chung
            for key in ('music_volume', 'sfx_volume'):
                value = settings.get(key, legacy)
                if type(value) in (int, float) and 0 <= value <= 1:
                    setattr(self.settings, key, float(value))
            for key in ('music', 'sfx'):
                if type(settings.get(key)) is bool:
                    setattr(self.settings, key, settings[key])
        self.stars = _int_map(data.get('stars'))
        self.best_moves = _int_map(data.get('best_moves'))
        self.par = _int_map(data.get('par'))

    def save(self):
        payload = {'settings': {'control_mode': self.settings.control_mode,
                                'theme': self.settings.theme,
                                'music': self.settings.music,
                                'music_volume': self.settings.music_volume,
                                'sfx': self.settings.sfx,
                                'sfx_volume': self.settings.sfx_volume},
                   'stars': self.stars, 'best_moves': self.best_moves, 'par': self.par}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix('.tmp')
            temporary.write_text(json.dumps(payload, indent=2), encoding='utf-8')
            temporary.replace(self.path)
        except OSError:
            return False
        return True

    def stars_for(self, level_id):
        return self.stars.get(level_id, 0)

    def total_stars(self, level_ids):
        return sum(self.stars_for(level_id) for level_id in level_ids)

    def record(self, level_id, moves, stars):
        """Keep the best result; True when stars or move count improved."""
        old_stars = self.stars.get(level_id, 0)
        old_moves = self.best_moves.get(level_id)
        improved = stars > old_stars or (stars == old_stars and (old_moves is None or moves < old_moves))
        self.stars[level_id] = max(stars, old_stars)
        self.best_moves[level_id] = moves if old_moves is None else min(moves, old_moves)
        return improved