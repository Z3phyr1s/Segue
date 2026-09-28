from fh6_spotify.gamepad import touch_volume_delta, is_tap, tap_thresholds, classify_swipe


def test_touch_volume_delta_requires_both_active():
    assert touch_volume_delta(50, 100, active=True, was_active=True, sensitivity=1.0) == 50.0
    assert touch_volume_delta(50, 100, active=False, was_active=True, sensitivity=1.0) == 0.0
    assert touch_volume_delta(50, 100, active=True, was_active=False, sensitivity=1.0) == 0.0


def test_touch_volume_delta_direction():
    """Touchpad Y grows downward, so moving up (y decreases) is louder (+)."""
    assert touch_volume_delta(cur_y=40, prev_y=60, active=True, was_active=True, sensitivity=1.0) > 0
    assert touch_volume_delta(cur_y=60, prev_y=40, active=True, was_active=True, sensitivity=1.0) < 0


def test_is_tap_short_and_still():
    assert is_tap(duration_ms=100, movement=5, max_ms=250, max_move=50)
    assert not is_tap(duration_ms=400, movement=5, max_ms=250, max_move=50)
    assert not is_tap(duration_ms=100, movement=80, max_ms=250, max_move=50)


def test_is_tap_min_ms_floor():
    assert not is_tap(duration_ms=5, movement=0, max_ms=250, max_move=50, min_ms=40.0)
    assert is_tap(duration_ms=45, movement=0, max_ms=250, max_move=50, min_ms=40.0)


def test_tap_thresholds_scale_with_sensitivity():
    lo = tap_thresholds(0)
    hi = tap_thresholds(100)
    default = tap_thresholds(70)
    assert lo == (160, 15)
    assert hi == (340, 100)
    assert lo[0] < default[0] < hi[0]
    assert lo[1] < default[1] < hi[1]


def test_tap_thresholds_clamps_out_of_range():
    assert tap_thresholds(-10) == tap_thresholds(0)
    assert tap_thresholds(500) == tap_thresholds(100)


def test_classify_swipe_horizontal_dominant():
    assert classify_swipe(dx=200, dy=10, swipe_threshold=150) == "skip-next"
    assert classify_swipe(dx=-200, dy=10, swipe_threshold=150) == "skip-prev"


def test_classify_swipe_vertical_needs_1_6x_ratio():
    assert classify_swipe(dx=20, dy=30, swipe_threshold=150, vol_deadzone=25) is None
    assert classify_swipe(dx=10, dy=40, swipe_threshold=150, vol_deadzone=25) == "vol"


def test_classify_swipe_below_thresholds_is_none():
    assert classify_swipe(dx=5, dy=5, swipe_threshold=150) is None
