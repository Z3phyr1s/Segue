import json

from fh6_spotify.config import Config


def test_load_missing_file_returns_defaults(tmp_path):
    cfg = Config.load(str(tmp_path / "nope.json"))
    assert cfg == Config()


def test_save_and_load_roundtrip(tmp_path):
    path = str(tmp_path / "sub" / "config.json")
    cfg = Config()
    cfg.full_level = 0.42
    cfg.game_preset = "rocketleague"
    cfg.save(path)
    loaded = Config.load(path)
    assert loaded.full_level == 0.42
    assert loaded.game_preset == "rocketleague"


def test_load_ignores_unknown_keys(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"full_level": 0.9, "totally_made_up_field": 123}))
    cfg = Config.load(str(path))
    assert cfg.full_level == 0.9
    assert not hasattr(cfg, "totally_made_up_field")


def test_load_corrupt_json_returns_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not valid json")
    cfg = Config.load(str(path))
    assert cfg == Config()


def test_apply_from_copies_all_fields():
    a = Config()
    b = Config()
    b.full_level = 0.11
    b.mode = "general"
    a.apply_from(b)
    assert a.full_level == 0.11
    assert a.mode == "general"
