from fh6_spotify.config import Config
from fh6_spotify.skip_rule import SkipRule


def _rule():
    return SkipRule(Config())


def test_dpad_down_suppresses_and_returns_none():
    r = _rule()
    assert r.on_dpad("down", is_driving=True, now=0.0) is None


def test_dpad_right_left_only_while_driving():
    r = _rule()
    assert r.on_dpad("right", is_driving=False, now=0.0) is None
    assert r.on_dpad("right", is_driving=True, now=0.0) == "next"
    assert r.on_dpad("left", is_driving=True, now=0.0) == "prev"


def test_dpad_up_ignored():
    r = _rule()
    assert r.on_dpad("up", is_driving=True, now=0.0) is None


def test_down_suppresses_subsequent_right_left_until_resume():
    r = _rule()
    r.on_dpad("down", is_driving=True, now=0.0)
    assert r.on_dpad("right", is_driving=True, now=0.01) is None
    r.on_resume()
    assert r.on_dpad("right", is_driving=True, now=0.02) == "next"


def test_suppression_expires_after_window():
    r = _rule()
    r.on_dpad("down", is_driving=True, now=0.0)
    ms = r.c.skip_menu_suppress_ms / 1000
    assert r.on_dpad("right", is_driving=True, now=ms + 0.5) == "next"


def test_on_comms_suppresses_like_dpad_down():
    r = _rule()
    r.on_comms(now=0.0)
    assert r.on_dpad("right", is_driving=True, now=0.01) is None
