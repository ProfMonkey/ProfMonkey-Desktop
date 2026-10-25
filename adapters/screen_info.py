"""Safe positioning in the Qt logical-pixel coordinate system."""


def clamp_coordinate(value: int, minimum: int, maximum: int) -> int:
    """Clamp a scalar, including unusually small screens."""
    if maximum < minimum:
        return minimum
    return max(minimum, min(maximum, value))


def clamp_window_position(
    x: int, y: int, width: int, height: int,
    area_left: int, area_top: int, area_width: int, area_height: int,
) -> tuple[int, int]:
    """Keep a top-level sprite inside one available desktop rectangle.

    When a window is bigger than the visible work area, anchor at top-left.
    """
    return (
        clamp_coordinate(x, area_left, area_left + area_width - width),
        clamp_coordinate(y, area_top, area_top + area_height - height),
    )
