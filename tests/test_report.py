"""報告與圖表資料測試。"""

from sitespider.crawler import CrawlConfig, CrawlReport, PageResult
from sitespider.report import compute_chart_data, export_csv_issues


def test_compute_chart_data():
    report = CrawlReport(start_url="https://x/", mode="file", config=CrawlConfig())
    report.pages["/a"] = PageResult(
        url="/a",
        status=200,
        content_type=None,
        response_ms=1,
        title="t",
        meta_description=None,
        meta_robots=None,
        canonical=None,
        crawl_depth=0,
        issues=["missing_h1"],
    )
    report.pages["/b"] = PageResult(
        url="/b",
        status=404,
        content_type=None,
        response_ms=1,
        title=None,
        meta_description=None,
        meta_robots=None,
        canonical=None,
        crawl_depth=1,
        issues=["http_error", "missing_title"],
    )
    charts = compute_chart_data(report)
    assert charts["depth"]["0"] == 1
    assert charts["depth"]["1"] == 1
    assert charts["status"]["200"] == 1
    assert charts["status"]["404"] == 1
    assert charts["issues"]["missing_h1"] == 1


def test_export_csv_issues(tmp_path):
    report = CrawlReport(start_url="https://x/", mode="file")
    report.pages["/a"] = PageResult(
        url="/a",
        status=200,
        content_type=None,
        response_ms=1,
        title="t",
        meta_description=None,
        meta_robots=None,
        canonical=None,
        issues=["missing_h1"],
    )
    path = tmp_path / "issues.csv"
    export_csv_issues(report, path)
    text = path.read_text(encoding="utf-8-sig")
    assert "missing_h1" in text
    assert "/a" in text
