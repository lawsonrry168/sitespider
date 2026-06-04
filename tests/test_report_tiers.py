"""分層報告匯出測試。"""

import json

from sitespider.crawler import CrawlReport, PageResult
from sitespider.report_tiers import ExportOptions, export_all_tiers, export_fast_tier


def _minimal_report() -> CrawlReport:
    report = CrawlReport(start_url="https://example.com/", mode="http")
    report.pages["https://example.com/"] = PageResult(
        url="https://example.com/",
        status=200,
        content_type="text/html",
        response_ms=12,
        title="Home",
        meta_description="desc",
        meta_robots=None,
        canonical="https://example.com/",
        crawl_depth=0,
        issues=["missing_h1"],
    )
    return report


def test_export_fast_tier_writes_core_files(tmp_path):
    report = _minimal_report()
    opts = ExportOptions(client_report_label="Example")
    names = export_fast_tier(report, tmp_path, opts)

    assert "REPORT-zh.md" in names
    assert "REPORT-zh.html" in names
    assert "summary.json" in names
    assert (tmp_path / "REPORT-zh.md").is_file()
    assert (tmp_path / "REPORT-zh.html").is_file()
    assert (tmp_path / "summary.json").is_file()

    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert "health_score" in summary
    assert summary["url_count"] == 1


def test_export_all_tiers_includes_standard_and_pro(tmp_path):
    report = _minimal_report()
    opts = ExportOptions(client_report_label="Example", plan_id="starter")
    names = export_all_tiers(report, tmp_path, opts)

    assert "dashboard.html" in names
    assert "issue_heatmap.html" in names
    assert "ngrams.csv" in names
    assert (tmp_path / "dashboard.html").is_file()
