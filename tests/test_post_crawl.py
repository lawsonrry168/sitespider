"""爬取後稽核測試。"""

from sitespider.crawler import CrawlReport, LinkInfo, PageResult
from sitespider.pixel_width import serp_pixel_width
from sitespider.post_crawl import (
    audit_content_duplicates,
    audit_page_extras,
    audit_sitemap_diff,
    normalize_content_hash,
)


def test_serp_pixel_width_cjk():
    assert serp_pixel_width("中文標題") > serp_pixel_width("abc")


def test_content_hash_stable():
    assert normalize_content_hash("Hello   World") == normalize_content_hash("hello world")


def test_mixed_content_issue():
    p = PageResult(
        url="https://x.com/",
        status=200,
        content_type="text/html",
        response_ms=1,
        title="Title Here Long Enough",
        meta_description="x" * 60,
        meta_robots=None,
        canonical="https://x.com/",
        h1=["H"],
        html_lang="en",
        og_title="og",
        has_viewport=True,
        links=[
            LinkInfo(
                href="http://other.com/",
                text="x",
                resolved="http://other.com/",
                link_type="external",
            )
        ],
    )
    audit_page_extras(p, mode="http")
    assert "mixed_content" in p.issues


def test_sitemap_diff():
    report = CrawlReport(start_url="https://x/", mode="http")
    report.sitemap_urls = ["https://x/a", "https://x/b"]
    report.pages["https://x/a/index.html"] = PageResult(
        url="https://x/a/index.html",
        status=200,
        content_type="text/html",
        response_ms=1,
        title="A" * 15,
        meta_description="m" * 60,
        meta_robots=None,
        canonical="https://x/a/",
        h1=["H"],
        html_lang="en",
        og_title="og",
        has_viewport=True,
    )
    audit_sitemap_diff(report, canonical_fn=lambda u: u.replace("/index.html", "/"))
    assert any("b" in u for u in report.sitemap_not_crawled) or report.sitemap_not_crawled


def test_duplicate_content():
    report = CrawlReport(start_url="https://x/", mode="http")
    h = "abc123"
    for path in ("/a", "/b"):
        report.pages[f"https://x{path}"] = PageResult(
            url=f"https://x{path}",
            status=200,
            content_type="text/html",
            response_ms=1,
            title="T" * 12,
            meta_description="m" * 60,
            meta_robots=None,
            canonical=f"https://x{path}",
            h1=["H"],
            html_lang="en",
            og_title="og",
            has_viewport=True,
            content_hash=h,
        )
    audit_content_duplicates(report)
    assert "duplicate_content" in report.pages["https://x/a"].issues
