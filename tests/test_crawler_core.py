"""爬蟲核心行為測試。"""

from sitespider.crawler import (
    CrawlReport,
    CrawlConfig,
    LinkInfo,
    PageResult,
    SeoCrawler,
    _normalize_url,
    _path_excluded,
)


def test_normalize_url_host_without_scheme():
    base = "https://www.allurebeauty.com.hk/en-services/foo"
    got = _normalize_url("www.allurebeauty.com.hk/contact", base)
    assert got == "https://www.allurebeauty.com.hk/contact"


def test_path_excluded():
    assert _path_excluded("https://x.com/api/foo", ("/api/",))
    assert not _path_excluded("https://x.com/blog/", ("/api/",))


def test_finalize_resource_checks():
    crawler = SeoCrawler("https://example.com/", mode="http", config=CrawlConfig())
    report = CrawlReport(start_url="https://example.com/", mode="http")
    report.pages["https://example.com/"] = PageResult(
        url="https://example.com/",
        status=200,
        content_type="text/html",
        response_ms=1,
        title="Home",
        meta_description="x" * 60,
        meta_robots=None,
        canonical="https://example.com/",
        h1=["H"],
        html_lang="en",
        og_title="og",
        has_viewport=True,
        links=[
            LinkInfo(
                href="/gone",
                text="bad",
                resolved="https://example.com/gone",
                link_type="internal",
                status=200,
            )
        ],
    )
    report.pages["https://example.com/gone"] = PageResult(
        url="https://example.com/gone",
        status=404,
        content_type="text/html",
        response_ms=1,
        title=None,
        meta_description=None,
        meta_robots=None,
        canonical=None,
    )
    crawler._finalize_resource_checks(report)
    home = report.pages["https://example.com/"]
    assert "broken_internal_link" in home.issues
    assert home.links[0].status == 404


def test_duplicate_meta_description():
    report = CrawlReport(start_url="https://x/", mode="http")
    meta = "Same description here for two pages"
    for path in ("/a", "/b"):
        url = f"https://x{path}"
        report.pages[url] = PageResult(
            url=url,
            status=200,
            content_type="text/html",
            response_ms=1,
            title=f"Title {path}",
            meta_description=meta,
            meta_robots=None,
            canonical=url,
            h1=["H"],
        )
    issues = report.summary_issues()
    assert "duplicate_meta_description" in issues
    assert len(issues["duplicate_meta_description"]) == 2
