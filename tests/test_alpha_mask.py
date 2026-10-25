import pytest

from core.alpha_mask import opaque_spans


def test_transparent_pixels_have_no_hitbox():
    rows = [[0, 0, 0, 0], [0, 255, 250, 0], [0, 0, 0, 0]]
    assert list(opaque_spans(rows)) == [(1, 1, 3)]


def test_one_row_can_contain_multiple_disconnected_regions():
    assert list(opaque_spans([[255, 0, 255, 255, 0, 255]])) == [
        (0, 0, 1), (0, 2, 4), (0, 5, 6)
    ]


def test_alpha_threshold_is_inclusive():
    assert list(opaque_spans([[23, 24, 25, 0]], threshold=24)) == [(0, 1, 3)]


def test_all_transparent_is_empty():
    assert list(opaque_spans([[0, 0], [0, 0]])) == []


def test_invalid_threshold_and_irregular_rows_rejected():
    with pytest.raises(ValueError):
        list(opaque_spans([[0]], threshold=0))
    with pytest.raises(ValueError):
        list(opaque_spans([[0, 0], [0]]))
    with pytest.raises(ValueError):
        list(opaque_spans([[500]]))
