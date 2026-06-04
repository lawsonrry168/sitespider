from pathlib import Path

from sitespider.crawler import CrawlReport, LinkInfo, PageResult
from sitespider.rich_results import evaluate_rich_results, export_rich_results_csv
from sitespider.sf_reports import (
    export_all_sf_reports,
    export_csv_duplicate_content,
    export_csv_h3,
    export_csv_outlinks,
    export_csv_robots,
)


def _page(url: str, **kw) -> PageResult:
    d = dict(
        status=200,
        content_type="text/html",
        response_ms=1,
        title="T",
        meta_description="m",
        meta_robots=None,
        canonical=url,
        indexability="Indexable",
    )
    d.update(kw)
    return PageResult(url=url, **d)


def test_h3_and_outlinks_export(tmp_path: Path):
    report = CrawlReport(start_url="https://x/", mode="http")
    b = "https://x/b"
    report.pages["https://x/a"] = _page("https://x/a", h3=["Section A", "Section B"])
    report.pages[b] = _page(b)
    report.pages["https://x/a"].links = [
        LinkInfo(href="/b", resolved=b, text="go", link_type="internal", nofollow=False)
    ]
    export_csv_h3(report, tmp_path / "h3.csv")
    export_csv_outlinks(report, tmp_path / "out.csv")
    h3 = (tmp_path / "h3.csv").read_text(encoding="utf-8-sig")
    assert "H3-1" in h3 and "Section A" in h3
    out = (tmp_path / "out.csv").read_text(encoding="utf-8-sig")
    assert "Internal" in out and b in out


def test_robots_and_duplicate_clusters(tmp_path: Path):
    report = CrawlReport(start_url="https://x/", mode="http")
    report.robots_info = {
        "source": "https://x/robots.txt",
        "disallowed": ["/private/"],
        "sitemaps": ["https://x/sitemap.xml"],
        "crawl_delay": 1.0,
    }
    h = "samehash"
    report.pages["https://x/a"] = _page("https://x/a", content_hash=h)
    report.pages["https://x/b"] = _page("https://x/b", content_hash=h)
    report.pages["https://x/private"] = _page(
        "https://x/private", blocked_by_robots=True, status=0
    )
    export_csv_robots(report, tmp_path / "robots.csv")
    export_csv_duplicate_content(report, tmp_path / "dup.csv")
    robots = (tmp_path / "robots.csv").read_text(encoding="utf-8-sig")
    assert "Disallow" in robots and "/private/" in robots
    dup = (tmp_path / "dup.csv").read_text(encoding="utf-8-sig")
    assert "URL Count" in dup and "2" in dup


def test_rich_results_heuristic():
    p = _page(
        "https://x/product/item",
        has_json_ld=True,
        json_ld_types=["Product"],
    )
    row = evaluate_rich_results(p)
    assert row["Eligible Types"] == "Product"
    assert "Product" in row["Notes"]


def test_export_all_includes_new_csvs(tmp_path: Path):
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/a"] = _page("https://x/a")
    names = export_all_sf_reports(report, tmp_path)
    for fn in ("h3.csv", "outlinks.csv", "robots.csv", "javascript.csv", "duplicate_content.csv"):
        assert fn in names
        assert (tmp_path / fn).exists()


def test_rich_results_csv(tmp_path: Path):
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/a"] = _page("https://x/a", has_json_ld=False)
    export_rich_results_csv(report, tmp_path / "rich.csv")
    text = (tmp_path / "rich.csv").read_text(encoding="utf-8-sig")
    assert "Rich Result Status" in text
