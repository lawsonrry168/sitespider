"""Sites dashboard discovery."""

from __future__ import annotations

from pathlib import Path

from sitespider.sites_dashboard import sites_dashboard_json


def test_discovers_flat_report_dir(tmp_path: Path):
    smoke = tmp_path / "reports" / "123deal-smoke"
    smoke.mkdir(parents=True)
    (smoke / "summary.json").write_text(
        '{"site_label":"123deal.com.hk","url_count":12,"health_score":35}',
        encoding="utf-8",
    )
    data = sites_dashboard_json(tenant_filter="default", base=tmp_path)
    ids = {s["job_id"] for s in data["sites"]}
    assert "123deal-smoke" in ids


def test_discovers_tenant_job_dir(tmp_path: Path):
    job = tmp_path / "reports" / "acme" / "abc123"
    job.mkdir(parents=True)
    (job / "REPORT-zh.html").write_text("<html></html>", encoding="utf-8")
    (job / "summary.json").write_text('{"health_score":80}', encoding="utf-8")
    data = sites_dashboard_json(tenant_filter="acme", base=tmp_path)
    assert any(s["job_id"] == "abc123" for s in data["sites"])
