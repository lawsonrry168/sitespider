"""SF 分頁 CSV 匯出測試。"""

from pathlib import Path

from sitespider.crawler import CrawlReport, PageResult
from sitespider.sf_reports import export_all_sf_reports


def _page(url: str, **extra) -> PageResult:
    base = dict(
        url=url,
        status=200,
        content_type="text/html",
        response_ms=1,
        title="Sample Page Title Here",
        meta_description="x" * 60,
        meta_robots=None,
        canonical=url,
        h1=["Heading"],
        h2=["Subheading"],
        html_lang="zh-HK",
        og_title="og",
        has_viewport=True,
        is_https=True,
    )
    base.update(extra)
    return PageResult(**base)


def test_export_all_sf_reports(tmp_path: Path):
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/"] = _page("https://x/")
    report.sitemap_urls = ["https://x/"]
    names = export_all_sf_reports(report, tmp_path)
    assert "security.csv" in names
    assert "external.csv" in names
    assert "sitemap_diff.csv" in names
    assert "Title 1 Pixel Width" in (tmp_path / "internal.csv").read_text(encoding="utf-8")
