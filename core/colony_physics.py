"""Deterministic, screen-space contact helpers for independent desktop pets."""
from __future__ import annotations

from core.physics import Body


def resolve_horizontal_collision(
    a: Body,
    b: Body,
    *,
    center_offset_a: float,
    center_offset_b: float,
    half_width_a: float,
    half_width_b: float,
    center_y_a: float,
    center_y_b: float,
    half_height_a: float,
    half_height_b: float,
    restitution: float = 0.55,
    min_bounce_speed: float = 58.0,
) -> bool:
    """Separate overlapping grounded sprites and bounce them apart.

    Body coordinates are window top-lefts; offsets identify the visible sprite
    centers inside each transparent window. Returns whether the sprite bounds
    touched. This intentionally models soft cartoon contact, not rigid-body
    simulation, and never reads or controls the real mouse or other windows.
    """
    vertical_overlap = half_height_a + half_height_b - abs(center_y_b - center_y_a)
    if vertical_overlap <= 0:
        return False

    center_a = a.x + center_offset_a
    center_b = b.x + center_offset_b
    dx = center_b - center_a
    required = half_width_a + half_width_b
    overlap = required - abs(dx)
    if overlap <= 0:
        return False

    direction = 1.0 if dx >= 0 else -1.0
    correction = overlap / 2.0 + 0.75
    a.x -= direction * correction
    b.x += direction * correction

    # Only change momentum if they are closing in on each other. If they are
    # almost stationary, give both a small cartoon bounce so contact is visible.
    closing = (b.vx - a.vx) * direction < -1.0
    nearly_still = abs(a.vx) < 10.0 and abs(b.vx) < 10.0
    if closing or nearly_still:
        speed_a = max(min_bounce_speed, abs(a.vx) * restitution)
        speed_b = max(min_bounce_speed, abs(b.vx) * restitution)
        a.vx = -direction * speed_a
        b.vx = direction * speed_b
    return True


def clamp_x(x: float, bounds: tuple[float, float, float, float], width: float) -> float:
    """Clamp a window's horizontal coordinate to a screen work area."""
    left, _top, right, _bottom = bounds
    return max(left, min(max(left, right - width), x))
