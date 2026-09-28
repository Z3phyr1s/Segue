from fh6_spotify.config import Config
from fh6_spotify.state import StateMachine


def _cfg(**overrides):
    c = Config()
    for k, v in overrides.items():
        setattr(c, k, v)
    return c


def test_general_mode_unfocused_uses_unfocused_level():
    c = _cfg(mode="general", unfocused_level=0.3)
    sm = StateMachine(c)
    assert sm._base_desired(None, False, None, 0.0, is_focused=False) == 0.3


def test_general_mode_focused_full_volume():
    c = _cfg(mode="general", full_level=0.7)
    sm = StateMachine(c)
    assert sm._base_desired(None, False, None, 0.0, is_focused=True) == 0.7


def test_general_mode_speech_ducks_when_enabled():
    c = _cfg(mode="general", ducking_enabled=True, duck_level=0.15)
    sm = StateMachine(c)
    assert sm._base_desired(None, True, None, 0.0, is_focused=True) == 0.15


def test_forza_menu_uses_menu_level():
    c = _cfg(mode="forza", menu_level=0.1)
    sm = StateMachine(c)
    assert sm._base_desired(False, False, None, 0.0) == 0.1


def test_forza_no_telemetry_yet_uses_running_flag():
    """is_race_on is None (no packet parsed yet): still menu_level while the
    game process is up, but full volume if it isn't running at all."""
    c = _cfg(mode="forza", menu_level=0.1, full_level=0.7)
    sm = StateMachine(c)
    assert sm._base_desired(None, False, None, 0.0, is_running=True) == 0.1
    assert sm._base_desired(None, False, None, 0.0, is_running=False) == 0.7


def test_forza_racing_full_volume_by_default():
    c = _cfg(mode="forza", full_level=0.7)
    sm = StateMachine(c)
    assert sm._base_desired(True, False, 50.0, 0.0) == 0.7


def test_forza_idle_after_stationary_window():
    c = _cfg(
        mode="forza", idle_when_stopped=True, idle_speed_threshold=2.0,
        idle_after_stationary_s=3.0, idle_level=0.3, full_level=0.7,
    )
    sm = StateMachine(c)
    assert sm._base_desired(True, False, 0.0, 0.0) == 0.7
    assert sm._base_desired(True, False, 0.0, 3.0) == 0.3


def test_forza_moving_again_resets_stationary_timer():
    c = _cfg(
        mode="forza", idle_when_stopped=True, idle_speed_threshold=2.0,
        idle_after_stationary_s=1.0, idle_level=0.3, full_level=0.7,
    )
    sm = StateMachine(c)
    sm._base_desired(True, False, 0.0, 0.0)
    sm._base_desired(True, False, 10.0, 0.5)
    assert sm._stationary_since is None


def test_system_scope_caps_menu_volume_when_speech_detected():
    """duck_scope="system" must cap volume on speech even in the menu, where
    _base_desired's own (game-only) duck check never runs."""
    c = _cfg(mode="forza", duck_scope="system", ducking_enabled=True,
             duck_level=0.15, menu_level=0.5)
    sm = StateMachine(c)
    assert sm._desired(False, True, None, 0.0) == 0.15


def test_game_scope_does_not_cap_menu_volume_when_speech_detected():
    c = _cfg(mode="forza", duck_scope="game", ducking_enabled=True,
             duck_level=0.15, menu_level=0.5)
    sm = StateMachine(c)
    assert sm._desired(False, True, None, 0.0) == 0.5


def test_update_debounces_before_committing():
    c = _cfg(mode="general", full_level=0.7, unfocused_level=0.3, debounce_ms=150)
    sm = StateMachine(c)
    assert sm.committed == 0.7
    v = sm.update(is_race_on=None, speech=False, now=0.0, is_focused=False)
    assert v == 0.7
    v2 = sm.update(is_race_on=None, speech=False, now=0.2, is_focused=False)
    assert v2 == 0.3


def test_update_returns_committed_immediately_when_matching():
    c = _cfg(mode="general", full_level=0.7)
    sm = StateMachine(c)
    v = sm.update(is_race_on=None, speech=False, now=0.0, is_focused=True)
    assert v == 0.7
    assert sm._pending is None
