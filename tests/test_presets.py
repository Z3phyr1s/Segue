from fh6_spotify import presets
from fh6_spotify.config import Config


def test_safe_filename_strips_illegal_chars():
    result = presets._safe_filename('bad<>:"/\\|?*name')
    for ch in '<>:"/\\|?*':
        assert ch not in result
    assert result.startswith("bad") and result.endswith("name")


def test_safe_filename_blank_falls_back_to_default():
    assert presets._safe_filename("") == "preset"
    assert presets._safe_filename("   ") == "preset"


def test_safe_filename_clamps_length():
    assert len(presets._safe_filename("x" * 200)) == 80


def test_capture_and_preset_game_roundtrip():
    cfg = Config()
    cfg.game_preset = "forza"
    data = presets.capture(cfg)
    assert presets.preset_game(data) == "forza"
    assert data["full_level"] == cfg.full_level


def test_preset_game_missing_key_is_universal():
    assert presets.preset_game({}) == ""
    assert presets.preset_game(None) == ""


def test_save_and_load_preset_roundtrip(tmp_path):
    d = str(tmp_path)
    presets.save_preset("My Preset", {"full_level": 0.5}, d)
    loaded = presets.load_presets(d)
    assert "My Preset" in loaded
    assert loaded["My Preset"]["full_level"] == 0.5


def test_delete_preset(tmp_path):
    d = str(tmp_path)
    presets.save_preset("Temp", {"x": 1}, d)
    presets.delete_preset("Temp", d)
    assert presets.load_presets(d) == {}


def test_save_presets_bulk_removes_stale_files(tmp_path):
    d = str(tmp_path)
    presets.save_preset("Keep", {"a": 1}, d)
    presets.save_preset("Drop", {"a": 2}, d)
    presets.save_presets({"Keep": {"a": 1}}, d)
    loaded = presets.load_presets(d)
    assert set(loaded.keys()) == {"Keep"}


def test_legacy_single_file_roundtrip(tmp_path):
    path = str(tmp_path / "presets.json")
    presets.save_presets({"Old": {"a": 1}}, path)
    assert presets.load_presets(path) == {"Old": {"a": 1}}
