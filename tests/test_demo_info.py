"""示範報告 API。"""

import json
from pathlib import Path

from sitespider.demo_info import demo_info_json, demo_report_dir
from sitespider.report_share import create_report_share, find_share_for_report


def test_demo_unavailable(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = demo_info_json()
    assert not out["available"]
    assert "123deal" in out["hint"]


def test_demo_available(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    report = demo_report_dir()
    report.mkdir(parents=True)
    (report / "crawl-report.json").write_text(
        json.dumps({"site_url": "https://example.com/", "pages": {"a": {}, "b": {}}}),
        encoding="utf-8",
    )
    (report / "summary.json").write_text(
        json.dumps({"url_count": 2, "health_score": 80, "health_grade_label": "良好"}),
        encoding="utf-8",
    )
    (report / "REPORT-zh.md").write_text("# demo", encoding="utf-8")
    out = demo_info_json()
    assert out["available"]
    assert out["pages"] == 2
    assert out["health_score"] == 80
    assert any(f["file"] == "REPORT-zh.md" for f in out["files"])


def test_demo_includes_portal(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    report = demo_report_dir()
    report.mkdir(parents=True)
    (report / "crawl-report.json").write_text("{}", encoding="utf-8")
    share = create_report_share(
        tenant_id="demo",
        job_id="123deal-smoke",
        report_dir=report,
        label="Demo",
    )
    out = demo_info_json()
    assert out["portal_path"] == share["share_path"]
    assert find_share_for_report(report) is not None
