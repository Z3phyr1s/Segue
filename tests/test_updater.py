import hashlib

from fh6_spotify.updater import (
    _parse_version,
    is_newer,
    _is_https_exe,
    installer_is_directly_updatable,
    verify_sha256,
    UpdateInfo,
)


def test_parse_version_basic():
    assert _parse_version("1.2.3") == (1, 2, 3)
    assert _parse_version("1.0") == (1, 0, 0)
    assert _parse_version("2") == (2, 0, 0)


def test_parse_version_prerelease_and_build_metadata_collapse():
    assert _parse_version("1.0.0-beta") == (1, 0, 0)
    assert _parse_version("1.0.0+build5") == (1, 0, 0)


def test_parse_version_garbage_is_zero():
    assert _parse_version("a.b.c") == (0, 0, 0)
    assert _parse_version("") == (0, 0, 0)


def test_is_newer():
    assert is_newer("1.1.0", "1.0.9")
    assert not is_newer("1.0.0", "1.0.0")
    assert not is_newer("1.0.0-beta", "1.0.0")


def test_is_https_exe():
    assert _is_https_exe("https://example.com/Segue_Setup.exe")
    assert not _is_https_exe("http://example.com/Segue_Setup.exe")
    assert not _is_https_exe("https://example.com/page.html")
    assert not _is_https_exe("")


def test_installer_is_directly_updatable_requires_both():
    info = UpdateInfo(
        version="1.0.0", ko_fi_url="", notes="",
        installer_url="https://example.com/a.exe", sha256="",
    )
    assert not installer_is_directly_updatable(info)
    info.sha256 = "abc123"
    assert installer_is_directly_updatable(info)
    info.installer_url = "https://example.com/page"
    assert not installer_is_directly_updatable(info)


def test_verify_sha256(tmp_path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"hello world")
    expected = hashlib.sha256(b"hello world").hexdigest()
    assert verify_sha256(str(p), expected)
    assert verify_sha256(str(p), expected.upper())
    assert not verify_sha256(str(p), "0" * 64)
    assert not verify_sha256(str(p), "")


def test_verify_sha256_missing_file(tmp_path):
    assert not verify_sha256(str(tmp_path / "nope.bin"), "a" * 64)
