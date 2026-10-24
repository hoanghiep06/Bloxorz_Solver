"""Deterministic elapsed-time timeline; no engine tasks or frame counters."""
from src.gui.animation_contracts import AnimationStatus
from src.gui.animation_math import finite


class AnimationTimeline:
    def __init__(self, duration, rate=1.0):
        finite(duration, 'duration', minimum=.001)
        self.duration = duration
        self.elapsed = 0.0
        self.status = AnimationStatus.PLAYING
        self.set_playback_rate(rate)

    @property
    def progress(self):
        return min(1.0, self.elapsed / self.duration)

    def set_playback_rate(self, rate):
        finite(rate, 'playback rate', minimum=.05)
        if rate > 8:
            raise ValueError('Playback rate must be in [.05, 8].')
        self.rate = rate

    def advance(self, dt):
        finite(dt, 'dt')
        if self.status is AnimationStatus.PLAYING:
            self.elapsed = min(self.duration, self.elapsed + dt*self.rate)
            if self.elapsed >= self.duration-1e-12*self.duration:
                self.elapsed = self.duration
                self.status = AnimationStatus.COMPLETED
        return self.progress

    def pause(self):
        if self.status is not AnimationStatus.PLAYING:
            return False
        self.status = AnimationStatus.PAUSED
        return True

    def resume(self):
        if self.status is not AnimationStatus.PAUSED:
            return False
        self.status = AnimationStatus.PLAYING
        return True
