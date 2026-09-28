from fh6_spotify import game_presets as gp
from fh6_spotify.config import Config


def test_get_falls_back_to_other_for_unknown_key():
    assert gp.get("nonexistent") is gp.GAME_PRESETS["other"]


def test_label_for():
    assert gp.label_for("forza") == "Forza Horizon"
    assert gp.label_for("nonexistent") == "Other game"


def test_show_control_defaults_true_for_unknown_control():
    assert gp.show_control("forza", "some_future_control") is True


def test_exes_for_includes_aliases():
    exes = gp.exes_for("forza")
    assert "forzahorizon6.exe" in exes
    assert "forzahorizon5.exe" in exes
    assert "forzahorizon4.exe" in exes


def test_exes_for_unknown_preset_no_exe():
    assert gp.exes_for("other") == set()


def test_apply_preset_sets_defaults_and_resolves_key():
    cfg = Config()
    key = gp.apply_preset(cfg, "rocketleague")
    assert key == "rocketleague"
    assert cfg.mode == "general"
    assert cfg.general_target_process == "rocketleague.exe"
    assert cfg.duck_scope == "system"


def test_apply_preset_unknown_key_resolves_to_other():
    cfg = Config()
    key = gp.apply_preset(cfg, "made_up_game")
    assert key == "other"
    assert cfg.game_preset == "other"


def test_detect_preset_from_running_matches_alias():
    assert gp.detect_preset_from_running(["forzahorizon5.exe"]) == "forza"
    assert gp.detect_preset_from_running(["rocketleague.exe"]) == "rocketleague"
    assert gp.detect_preset_from_running(["notepad.exe"]) is None


def test_detect_preset_from_running_empty():
    assert gp.detect_preset_from_running([]) is None
