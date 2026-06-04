"""路徑解析（開發模式）。"""

from pathlib import Path

from sitespider.paths import default_reports_dir, package_dir, ui_dir, user_data_dir


def test_package_dir_has_ui():
    pkg = package_dir()
    assert pkg.is_dir()
    assert (pkg / "ui" / "dashboard.html").is_file()
    assert ui_dir() == pkg / "ui"


def test_user_data_dir_creates(tmp_path, monkeypatch):
    monkeypatch.setenv("SITESPIDER_DATA_DIR", str(tmp_path / "data"))
    d = user_data_dir()
    assert d == tmp_path / "data"
    assert d.is_dir()
    r = default_reports_dir()
    assert r == d / "reports"
    assert r.is_dir()
