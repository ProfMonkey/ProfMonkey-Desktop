from adapters.screen_info import clamp_window_position


def test_bottom_right_clamped_into_work_area():
    assert clamp_window_position(9999, 9999, 160, 160, 0, 0, 1920, 1040) == (1760, 880)


def test_negative_coordinates_for_secondary_monitor():
    assert clamp_window_position(-900, -300, 160, 160, -1920, 0, 1920, 1080) == (-900, 0)


def test_too_small_display_still_has_safe_origin():
    assert clamp_window_position(300, 300, 160, 160, 0, 0, 80, 80) == (0, 0)
