"""Deterministic screen-space movement. Coordinates are Qt logical pixels.

No GUI dependency: simulation is bounded to one available work area and
never changes another application's window or actual mouse cursor.
"""
from dataclasses import dataclass
import math


@dataclass
class Body:
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    airborne: bool = False

    def step(self, dt: float, bounds: tuple[float, float, float, float],
             size: tuple[float, float], gravity: float = 1450.0) -> bool:
        """Integrate motion; return True upon a floor collision."""
        if not 0 <= dt <= 0.25 or not math.isfinite(dt):
            raise ValueError('invalid time step')
        left, top, right, bottom = bounds
        w, h = size
        if right < left or bottom < top or w <= 0 or h <= 0:
            raise ValueError('invalid geometry')
        self.x += self.vx * dt
        min_x, max_x = left, max(left, right - w)
        if self.x <= min_x and self.vx < 0:
            self.x, self.vx = min_x, -self.vx * 0.35
        elif self.x >= max_x and self.vx > 0:
            self.x, self.vx = max_x, -self.vx * 0.35
        self.x = max(min_x, min(max_x, self.x))
        ground = max(top, bottom - h)
        landed = False
        if self.airborne or abs(self.vy) > 0.01:
            self.vy += gravity * dt
            self.y += self.vy * dt
            if self.y >= ground:
                self.y = ground
                landed = True
                self.airborne = False
                self.vy = 0.0
                self.vx *= 0.55
            elif self.y < top:
                self.y = top
                self.vy = max(0.0, self.vy)
        else:
            self.y = ground
        return landed

    def throw(self, vx: float, vy: float, *, max_speed: float = 950.0) -> None:
        self.vx = max(-max_speed, min(max_speed, vx))
        self.vy = max(-max_speed, min(max_speed, vy))
        self.airborne = True

    def ground(self, bounds: tuple[float, float, float, float], size: tuple[float, float]) -> None:
        left, top, right, bottom = bounds
        w, h = size
        self.x = max(left, min(max(left, right - w), self.x))
        self.y = max(top, bottom - h)
        self.vx = self.vy = 0.0
        self.airborne = False
