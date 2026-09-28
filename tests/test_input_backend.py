from fh6_spotify.input_backend import (
    code_active,
    named_active,
    suppress_subsets,
    resolve_actions,
    evaluate_binds,
    parse_key_code,
    effective_bindings,
    vol_delta,
)


def test_code_active_button():
    assert code_active("btn:2", [False, False, True], [])
    assert not code_active("btn:2", [False, False, False], [])
    assert not code_active("btn:9", [True], [])


def test_code_active_hat_direction():
    assert code_active("hat:0:up", [], [(0, 1)])
    assert not code_active("hat:0:up", [], [(0, -1)])
    assert code_active("hat:0:right", [], [(1, 0)])


def test_code_active_combo_requires_all():
    buttons = [True, True, False]
    assert code_active("btn:0+btn:1", buttons, [])
    assert not code_active("btn:0+btn:2", buttons, [])


def test_code_active_empty_code():
    assert not code_active("", [True], [])


def test_named_active_single_and_combo():
    class S:
        share = True
        square = False

    assert named_active("share", S())
    assert not named_active("square", S())
    assert not named_active("share+square", S())


def test_named_active_empty():
    assert not named_active("", object())


def test_parse_key_code_bare_and_modifiers():
    assert parse_key_code("key:65") == (frozenset(), 65)
    assert parse_key_code("key:17+65") == (frozenset({17}), 65)
    assert parse_key_code("key:17+16+80") == (frozenset({17, 16}), 80)


def test_parse_key_code_invalid():
    assert parse_key_code("") == (frozenset(), None)
    assert parse_key_code("btn:5") == (frozenset(), None)
    assert parse_key_code("key:abc") == (frozenset(), None)


def test_effective_bindings_layers_overrides():
    out = effective_bindings("xbox", {"prev": "hat:0:up"})
    assert out["prev"] == "hat:0:up"
    assert out["next"] == "hat:0:right"


def test_effective_bindings_keyboard_mode_switch():
    forza = effective_bindings("keyboard", {}, mode="forza")
    general = effective_bindings("keyboard", {}, mode="general")
    assert forza["prev"] != general["prev"]


def test_suppress_subsets_combo_wins_over_component():
    binds = {"vol_up": "btn:4+hat:0:right", "next": "hat:0:right"}
    active = {"vol_up", "next"}
    assert suppress_subsets(active, binds) == {"vol_up"}


def test_suppress_subsets_no_relation_keeps_both():
    binds = {"a": "btn:1", "b": "btn:2"}
    assert suppress_subsets({"a", "b"}, binds) == {"a", "b"}


def test_resolve_actions_hold_action_needs_pass():
    binds = {"open": "btn:5"}
    out = resolve_actions(
        binds, holds={"open"}, held_codes={"btn:5"}, passed_codes=set(), hold_codes={"btn:5"}
    )
    assert out == set()
    out2 = resolve_actions(
        binds, holds={"open"}, held_codes={"btn:5"}, passed_codes={"btn:5"}, hold_codes={"btn:5"}
    )
    assert out2 == {"open"}


def test_resolve_actions_tap_twin_hidden_while_held():
    binds = {"open": "btn:5", "pause": "btn:5"}
    out = resolve_actions(
        binds, holds={"open"}, held_codes={"btn:5"}, passed_codes=set(), hold_codes={"btn:5"}
    )
    assert "pause" not in out


def test_evaluate_binds_tap_fires_on_release_under_hold_threshold():
    """A code shared by a hold-action and a plain tap-twin never goes active
    while held (see test_resolve_actions_tap_twin_hidden_while_held); instead
    the twin fires once on release, as long as the hold threshold wasn't hit."""
    binds = {"open": "btn:0", "pause": "btn:0"}
    holds = {"open"}
    down_since = {}
    consumed = set()
    active, _ = evaluate_binds(
        binds, holds, [True], [], now=0.0, down_since=down_since,
        prev_active=set(), hold_ms=0.3, consumed=consumed,
    )
    assert active == set()
    active2, pressed2 = evaluate_binds(
        binds, holds, [False], [], now=0.1, down_since=down_since,
        prev_active=active, hold_ms=0.3, consumed=consumed,
    )
    assert pressed2 == {"pause"}


def test_evaluate_binds_hold_passes_threshold_no_tap_twin():
    """Once the hold action actually fires, releasing must NOT also fire the
    tap-twin sharing its code (that would double-act on one physical press)."""
    binds = {"open": "btn:0", "pause": "btn:0"}
    holds = {"open"}
    down_since = {}
    consumed = set()
    active, _ = evaluate_binds(
        binds, holds, [True], [], now=0.0, down_since=down_since,
        prev_active=set(), hold_ms=0.3, consumed=consumed,
    )
    active2, _ = evaluate_binds(
        binds, holds, [True], [], now=0.35, down_since=down_since,
        prev_active=active, hold_ms=0.3, consumed=consumed,
    )
    assert "open" in active2
    _, pressed3 = evaluate_binds(
        binds, holds, [False], [], now=0.4, down_since=down_since,
        prev_active=active2, hold_ms=0.3, consumed=consumed,
    )
    assert "pause" not in pressed3


def test_vol_delta_initial_press_then_repeat():
    state = {}
    d = vol_delta(active={"vol_up"}, pressed={"vol_up"}, now=0.0, state=state, step=0.05)
    assert d == 0.05
    d2 = vol_delta(active={"vol_up"}, pressed=set(), now=0.1, state=state, step=0.05)
    assert d2 == 0.0
    d3 = vol_delta(active={"vol_up"}, pressed=set(), now=0.30, state=state, step=0.05)
    assert d3 == 0.05


def test_vol_delta_release_clears_state():
    state = {"vol_up": 5.0}
    vol_delta(active=set(), pressed=set(), now=1.0, state=state, step=0.05)
    assert "vol_up" not in state
