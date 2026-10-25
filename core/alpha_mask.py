"""Convert a sprite's alpha channel to horizontal hit-test spans.

This module intentionally has no Qt import, so the click-through shape
algorithm is deterministic and independently testable. Every span is
(start_x inclusive, end_x exclusive), in a particular image row.
"""

from collections.abc import Iterable, Sequence, Iterator


def opaque_spans(
    rows: Iterable[Sequence[int]], *, threshold: int = 24
) -> Iterator[tuple[int, int, int]]:
    """Yield (y, start_x, end_x) runs of pixels with alpha >= threshold.

    Rows must have the same width. The window mask can use these to
    exclude transparent pixels entirely from operating-system hit tests.
    """
    if not 1 <= threshold <= 255:
        raise ValueError("threshold must be between 1 and 255")

    expected_width = None
    for y, row in enumerate(rows):
        width = len(row)
        if expected_width is None:
            expected_width = width
        elif width != expected_width:
            raise ValueError("all alpha rows must have equal width")

        start = None
        for x, alpha in enumerate(row):
            if not 0 <= alpha <= 255:
                raise ValueError("alpha channel values must be between 0 and 255")
            if alpha >= threshold:
                if start is None:
                    start = x
            elif start is not None:
                yield y, start, x
                start = None
        if start is not None:
            yield y, start, width
