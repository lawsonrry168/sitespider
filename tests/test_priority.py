from pathlib import Path

from sitespider.crawler import CrawlReport, PageResult
from sitespider.priority import (
    compute_priority_rows,
    export_priority_pages_csv,
    export_priority_summary_md,
)


def _page(url: str, *, issues=None, indexability="Indexable", status=200, depth=1):
    return PageResult(
        url=url,
        status=status,
        content_type="text/html",
        response_ms=1,
        title="Title long enough",
        meta_description="m" * 80,
        meta_robots=None,
        canonical=url,
        issues=issues or [],
        indexability=indexability,
        crawl_depth=depth,
    )


def test_priority_money_page_boost():
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/blog/a"] = _page("https://x/blog/a", issues=["missing_title"])
    report.pages["https://x/product/a"] = _page("https://x/product/a", issues=["missing_title"])
    rows = compute_priority_rows(report)
    by_url = {r.url: r for r in rows}
    assert by_url["https://x/product/a"].money_page
    assert by_url["https://x/product/a"].score >= by_url["https://x/blog/a"].score


def test_priority_non_indexable_penalty():
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/service/a"] = _page(
        "https://x/service/a",
        issues=["missing_title"],
        indexability="Indexable",
    )
    report.pages["https://x/service/b"] = _page(
        "https://x/service/b",
        issues=["missing_title"],
        indexability="Non-Indexable",
    )
    rows = compute_priority_rows(report)
    by_url = {r.url: r for r in rows}
    assert by_url["https://x/service/a"].score > by_url["https://x/service/b"].score


def test_export_priority_csv_columns(tmp_path: Path):
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/contact"] = _page("https://x/contact")
    out = tmp_path / "priority.csv"
    export_priority_pages_csv(report, out, limit=10)
    text = out.read_text(encoding="utf-8-sig")
    assert "Money Page" in text
    assert "Segment" in text


def test_export_priority_summary_md(tmp_path: Path):
    report = CrawlReport(start_url="https://x/", mode="http")
    report.llms_info = {
        "llms.txt": {"status": 200, "bytes": 128},
        "llms-full.txt": {"status": 404, "bytes": 0},
    }
    report.pages["https://x/contact"] = _page("https://x/contact", issues=["missing_title"])
    out = tmp_path / "priority_summary.md"
    export_priority_summary_md(report, out, top_n=5)
    text = out.read_text(encoding="utf-8")
    assert "Priority Summary" in text
    assert "https://x/contact" in text
    assert "llms.txt: OK 200" in text
    assert "7 日執行排程" in text
    assert "Day 1" in text
    assert "Day 7" in text
