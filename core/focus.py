"""In-process focus clock, independent of animations and keyboard activity.

No input hooks, no persistence of individual sessions and no background service.
Uses monotonic wall time so a minimized/hidden monkey doesn't slow the timer.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import time


@dataclass
class FocusClock:
    state: str = 'idle'  # idle / running / paused / completed
    minutes: int = 25
    _deadline: float = 0.0
    _frozen: float = 0.0

    def start(self, minutes: int, now: float | None = None) -> None:
        if isinstance(minutes, bool) or not isinstance(minutes, int) or not 1 <= minutes <= 180:
            raise ValueError('focus minutes must be 1..180')
        t = time.monotonic() if now is None else now
        self.minutes = minutes
        self.state = 'running'
        self._deadline = t + 60 * minutes
        self._frozen = 0.0

    def remaining(self, now: float | None = None) -> int:
        if self.state == 'paused':
            return math.ceil(self._frozen)
        if self.state == 'running':
            t = time.monotonic() if now is None else now
            return max(0, math.ceil(self._deadline - t))
        if self.state == 'completed':
            return 0
        return self.minutes * 60

    @property
    def active(self) -> bool:
        return self.state in ('running', 'paused')

    def pause(self, now: float | None = None) -> bool:
        if self.state != 'running':
            return False
        self._frozen = self.remaining(now)
        self.state = 'paused'
        return True

    def resume(self, now: float | None = None) -> bool:
        if self.state != 'paused':
            return False
        t = time.monotonic() if now is None else now
        self._deadline = t + self._frozen
        self.state = 'running'
        return True

    def cancel(self) -> None:
        self.state = 'idle'
        self._frozen = 0.0

    def check_complete(self, now: float | None = None) -> bool:
        """True exactly once upon crossing the deadline."""
        if self.state != 'running' or self.remaining(now) > 0:
            return False
        self.state = 'completed'
        return True


def format_seconds(seconds: int) -> str:
    seconds = max(0, int(seconds))
    return f'{seconds // 60:02}:{seconds % 60:02}'
