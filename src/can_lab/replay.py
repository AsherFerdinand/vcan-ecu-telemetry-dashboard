"""Dedicated recorded-data source and deterministic monotonic-clock replay.

Never creates CAN identifiers. Invalid/mixed/reversed times block timed replay,
while diagnostics and exports still retain the recording unchanged.
"""
from bisect import bisect_right
from dataclasses import dataclass
import math
from typing import Protocol


class RecordedDataSource(Protocol):
    @property
    def observations(self): ...


@dataclass
class RecordingSource:
    recording: object

    @property
    def observations(self):
        return self.recording.observations


class Replay:
    def __init__(self, source: RecordedDataSource):
        self.source = source
        times = [row.timestamp_s for row in source.observations]
        if not times or any(time is None or not math.isfinite(time) for time in times):
            raise ValueError('Timed replay requires usable timestamps for every observation; raw rows remain available for diagnostics.')
        if any(b < a for a, b in zip(times, times[1:])):
            raise ValueError('Timed replay requires nondecreasing timestamps; original recording was not sorted or altered.')
        self.times = times
        self.offsets = [time - times[0] for time in times]
        self.reset()

    def reset(self):
        self.position_s = 0.0
        self.cursor = 0
        self.playing = False
        self.speed = 1.0
        self._last_wall = None

    def play(self, now):
        self._check_now(now)
        self.playing = True
        self._last_wall = now

    def pause(self, now):
        emitted = self.advance(now)
        self.playing = False
        self._last_wall = None
        return emitted

    def set_speed(self, speed, now):
        if not math.isfinite(speed) or speed <= 0:
            raise ValueError('playback speed must be finite and positive')
        emitted = self.advance(now)
        self.speed = speed
        return emitted

    @staticmethod
    def _check_now(now):
        if not math.isfinite(now):
            raise ValueError('replay clock must be finite')

    def advance(self, now):
        self._check_now(now)
        if self.playing:
            if now < self._last_wall:
                raise ValueError('replay clock must be monotonic')
            self.position_s = min(self.offsets[-1], self.position_s + (now - self._last_wall) * self.speed)
            self._last_wall = now
        end = bisect_right(self.offsets, self.position_s)
        # Tuple of original row objects; duplicate-time rows are emitted in original order.
        emitted = tuple(self.source.observations[self.cursor:end]) if self.playing else ()
        if self.playing:
            self.cursor = end
            if self.cursor == len(self.times):
                self.playing = False
        return emitted

    @property
    def current(self):
        return self.source.observations[max(0, self.cursor - 1)]

    @property
    def finished(self):
        return self.cursor == len(self.times)
