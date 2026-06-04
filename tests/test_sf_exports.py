"""SF 風格 CSV 匯出測試。"""

from pathlib import Path

from sitespider.crawler import CrawlReport, PageResult
from sitespider.report import export_csv_page_titles, export_csv_response_codes


def test_sf_export_csvs(tmp_path: Path):
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/a"] = PageResult(
        url="https://x/a",
        status=200,
        content_type="text/html",
        response_ms=1,
        title="Hello",
        meta_description=None,
        meta_robots=None,
        canonical=None,
        indexability="Indexable",
    )
    export_csv_response_codes(report, tmp_path / "rc.csv")
    export_csv_page_titles(report, tmp_path / "pt.csv")
    rc = (tmp_path / "rc.csv").read_text(encoding="utf-8-sig")
    assert "Status Code" in rc
    assert "https://x/a" in rc
    pt = (tmp_path / "pt.csv").read_text(encoding="utf-8-sig")
    assert "Title 1" in pt
    assert "Hello" in pt
