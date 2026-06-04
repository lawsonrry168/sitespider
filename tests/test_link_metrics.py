"""內鏈指標與 All Inlinks 匯出測試。"""

from pathlib import Path

from sitespider.crawler import CrawlReport, LinkInfo, PageResult
from sitespider.link_metrics import collect_internal_inlinks, compute_page_link_stats
from sitespider.sf_reports import export_csv_all_inlinks, export_sf_internal_enhanced


def _page(url: str, *, links=None, inlinks=None) -> PageResult:
    return PageResult(
        url=url,
        status=200,
        content_type="text/html",
        response_ms=1,
        title=url,
        meta_description=None,
        meta_robots=None,
        canonical=None,
        links=links or [],
        inlinks=inlinks or [],
    )


def test_pagerank_ignores_nofollow_outlinks():
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/"] = _page(
        "https://x/",
        links=[
            LinkInfo("a", "NF", "https://x/a", "internal", nofollow=True),
            LinkInfo("b", "F", "https://x/b", "internal", nofollow=False),
        ],
    )
    report.pages["https://x/a"] = _page("https://x/a", inlinks=["https://x/"])
    report.pages["https://x/b"] = _page("https://x/b", inlinks=["https://x/"])
    stats = compute_page_link_stats(report)
    assert stats["https://x/b"].link_score >= stats["https://x/a"].link_score


def test_pagerank_homepage_wins():
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/"] = _page(
        "https://x/",
        links=[
            LinkInfo("a", "A", "https://x/a", "internal"),
            LinkInfo("b", "B", "https://x/b", "internal"),
        ],
        inlinks=[],
    )
    report.pages["https://x/a"] = _page(
        "https://x/a",
        links=[LinkInfo("/", "Home", "https://x/", "internal")],
        inlinks=["https://x/"],
    )
    report.pages["https://x/b"] = _page(
        "https://x/b",
        links=[],
        inlinks=["https://x/"],
    )
    stats = compute_page_link_stats(report)
    assert stats["https://x/"].link_score == 100.0
    assert stats["https://x/b"].link_score < stats["https://x/"].link_score
    assert stats["https://x/"].unique_outlinks == 2


def test_all_inlinks_csv(tmp_path: Path):
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/"] = _page(
        "https://x/",
        links=[LinkInfo("/a", "Go A", "https://x/a", "internal")],
    )
    report.pages["https://x/a"] = _page("https://x/a")
    export_csv_all_inlinks(report, tmp_path / "all_inlinks.csv")
    text = (tmp_path / "all_inlinks.csv").read_text(encoding="utf-8-sig")
    assert "Hyperlink" in text
    assert "https://x/" in text
    assert "Go A" in text


def test_internal_csv_link_score(tmp_path: Path):
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/"] = _page("https://x/")
    export_sf_internal_enhanced(report, tmp_path / "internal.csv")
    text = (tmp_path / "internal.csv").read_text(encoding="utf-8-sig")
    assert "Link Score" in text
    assert "Unique Outlinks" in text
