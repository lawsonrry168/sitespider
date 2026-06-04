"""客戶 Portal 分享連結。"""

import json
from pathlib import Path

from sitespider.report_share import (
    create_report_share,
    portal_file_path,
    portal_manifest,
    resolve_share,
)


def test_share_roundtrip(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    report = tmp_path / "r1"
    report.mkdir()
    (report / "crawl-report.json").write_text('{"pages":{}}', encoding="utf-8")
    (report / "REPORT-zh.md").write_text("# hi", encoding="utf-8")
    (report / "delivery-summary.html").write_text("<html></html>", encoding="utf-8")

    out = create_report_share(
        tenant_id="acme",
        job_id="job1",
        report_dir=report,
        label="Demo",
        ttl_days=7,
    )
    rec = resolve_share(out["token"])
    assert rec is not None
    assert rec["tenant_id"] == "acme"
    m = portal_manifest(report, "Demo", expires_at=9999999999.0)
    assert m["expires_at"] == 9999999999.0
    assert any(f["file"] == "REPORT-zh.md" for f in m["files"])
    fp = portal_file_path(report, "REPORT-zh.md")
    assert fp and fp.is_file()
    assert portal_file_path(report, "crawl-report.json") is None
