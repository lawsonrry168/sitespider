"""v1.17：熱力圖、白標、自訂預設、任務歷史。"""

from __future__ import annotations

import json
from pathlib import Path

from sitespider.branding import Branding
from sitespider.custom_presets import rules_from_preset_ids
from sitespider.crawler import CrawlConfig, CrawlReport, PageResult
from sitespider.issue_heatmap import build_prefix_issue_matrix, export_issue_heatmap_html
from sitespider.job_store import append_job_record, list_job_history


def _mini_report() -> CrawlReport:
    r = CrawlReport(start_url="https://example.com/", mode="http", config=CrawlConfig())
    base = dict(
        content_type="text/html",
        response_ms=100.0,
        title=None,
        meta_description=None,
        meta_robots=None,
        canonical=None,
    )
    r.pages["https://example.com/"] = PageResult(
        url="https://example.com/", status=200, issues=["missing_h1"], **base
    )
    r.pages["https://example.com/blog/x"] = PageResult(
        url="https://example.com/blog/x", status=200, **base
    )
    return r


def test_custom_presets_rules():
    rules = rules_from_preset_ids(["email", "phone_hk"])
    assert len(rules) == 2


def test_heatmap_matrix():
    m = build_prefix_issue_matrix(_mini_report())
    assert any(k.startswith("/") for k in m.keys())


def test_heatmap_html(tmp_path: Path):
    export_issue_heatmap_html(_mini_report(), tmp_path / "h.html", branding=Branding(consultant_name="Agency"))
    assert "Agency" in (tmp_path / "h.html").read_text(encoding="utf-8")


def test_job_history(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    append_job_record(job_id="abc", status="done", site_url="https://x.com", pages=3)
    rows = list_job_history()
    assert rows[0]["job_id"] == "abc"
