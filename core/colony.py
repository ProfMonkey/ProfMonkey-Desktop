"""Pure helpers for bounding a configurable group of independently moving pets.

Multiple pets share the screen, not a single window or animation timeline.
The spawn algorithm only chooses a *starting* position; pets retain their own
physics, input handling, and autonomous state afterwards.
"""
from __future__ import annotations

MIN_MONKEYS = 1
MAX_MONKEYS = 6


def clamp_count(value: int) -> int:
    """Validate a user-facing count (reject booleans and fractional values)."""
    if isinstance(value, bool):
        raise ValueError('boolean is not a monkey count')
    if isinstance(value, float) and not value.is_integer():
        raise ValueError('fractional monkey count')
    value = int(value)
    return max(MIN_MONKEYS, min(MAX_MONKEYS, value))


def spawn_position(bounds: tuple[float, float, float, float],
                   size: tuple[float, float], index: int, count: int) -> tuple[int, int]:
    """Spread added members along the available desktop floor.

    Index zero is the primary pet on the right. All positions are Qt logical
    pixels, bounded to the same screen as the primary pet. No global mouse API.
    """
    count = clamp_count(count)
    if index < 0 or index >= count:
        raise ValueError('index outside colony')
    left, top, right, bottom = bounds
    width, height = size
    room = max(0., right-left-width)
    # Keep the default monkey at the right; place companions from left to right.
    if index == 0:
        x = left + room
    else:
        x = left + room * index / count
    y = max(top, bottom-height)
    return round(x), round(y)
