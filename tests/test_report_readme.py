from pathlib import Path

from sitespider.crawler import CrawlReport, PageResult
from sitespider.report_readme import export_report_readme_html, export_report_readme_md


def _page(url: str) -> PageResult:
    return PageResult(
        url=url,
        status=200,
        content_type="text/html",
        response_ms=1,
        title="Title long enough here",
        meta_description="m" * 80,
        meta_robots=None,
        canonical=url,
        indexability="Indexable",
    )


def test_export_report_readme_no_gsc(tmp_path: Path):
    report = CrawlReport(start_url="https://x/", mode="http")
    report.config.gsc_inspect_max = 0
    report.pages["https://x/a"] = _page("https://x/a")
    export_report_readme_md(report, tmp_path / "REPORT-zh.md", site_label="Test")
    text = (tmp_path / "REPORT-zh.md").read_text(encoding="utf-8")
    assert "報告導覽" in text
    assert "未使用 Google Search Console" in text
    assert "priority_summary.md" in text


def test_export_report_readme_html_gui(tmp_path: Path):
    report = CrawlReport(start_url="https://x/", mode="http")
    report.config.gsc_inspect_max = 0
    report.pages["https://x/a"] = _page("https://x/a")
    (tmp_path / "dashboard.html").write_text("<html></html>", encoding="utf-8")
    export_report_readme_html(
        report, tmp_path / "REPORT-zh.html", site_label="Test", out_dir=tmp_path
    )
    html = (tmp_path / "REPORT-zh.html").read_text(encoding="utf-8")
    assert "交付導覽" in html
    assert "delivery-grid" in html
    assert "dashboard.html" in html
    assert "health-ring-lg" in html
