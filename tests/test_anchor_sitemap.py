"""錨文字稽核與 sitemap 匯出測試。"""

from pathlib import Path

from sitespider.crawler import CrawlReport, LinkInfo, PageResult
from sitespider.post_crawl import audit_anchor_text
from sitespider.sf_reports import export_csv_anchor_text
from sitespider.sitemap_export import export_sitemap_xml


def _page(url: str, **kwargs) -> PageResult:
    defaults = dict(
        status=200,
        content_type="text/html",
        response_ms=1,
        title="Title long enough",
        meta_description="x" * 60,
        meta_robots=None,
        canonical=url,
        h1=["H"],
        indexability="Indexable",
    )
    defaults.update(kwargs)
    return PageResult(url=url, **defaults)


def test_duplicate_anchor_text_issue():
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/"] = _page(
        "https://x/",
        links=[
            LinkInfo("/a", "Shop", "https://x/a", "internal"),
            LinkInfo("/b", "Shop", "https://x/b", "internal"),
        ],
    )
    report.pages["https://x/a"] = _page("https://x/a")
    report.pages["https://x/b"] = _page("https://x/b")
    audit_anchor_text(report)
    assert "duplicate_anchor_text" in report.pages["https://x/"].issues


def test_export_sitemap_xml(tmp_path: Path):
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/"] = _page("https://x/")
    report.pages["https://x/hidden"] = _page(
        "https://x/hidden", meta_robots="noindex", indexability="Non-Indexable"
    )
    n = export_sitemap_xml(report, tmp_path / "sitemap.xml")
    assert n == 1
    text = (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    assert "https://x/" in text
    assert "hidden" not in text


def test_anchor_text_csv(tmp_path: Path):
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/"] = _page(
        "https://x/",
        links=[
            LinkInfo("/a", "Buy", "https://x/a", "internal"),
            LinkInfo("/b", "Buy", "https://x/b", "internal"),
        ],
    )
    report.pages["https://x/a"] = _page("https://x/a")
    report.pages["https://x/b"] = _page("https://x/b")
    export_csv_anchor_text(report, tmp_path / "anchor.csv")
    body = (tmp_path / "anchor.csv").read_text(encoding="utf-8-sig")
    assert "buy" in body.lower()
    assert ",2," in body.replace(" ", "")
