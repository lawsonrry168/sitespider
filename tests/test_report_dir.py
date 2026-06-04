import json
from pathlib import Path

from sitespider.server import _report_dir, _write_crawl_snapshot


def test_report_dir_created_before_snapshot(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = _report_dir("default", "abc123")
    assert out.is_dir()
    payload = {"url": "https://example.com/", "tenant_id": "default"}
    _write_crawl_snapshot(out, payload)
    snap = out / "crawl-config.snapshot.json"
    assert snap.is_file()
    assert json.loads(snap.read_text(encoding="utf-8"))["url"] == "https://example.com/"
