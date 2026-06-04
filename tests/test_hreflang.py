"""hreflang 稽核測試。"""

from sitespider.crawler import CrawlReport, PageResult
from sitespider.hreflang import audit_hreflang


def test_hreflang_missing_self():
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/en/index.html"] = PageResult(
        url="https://x/en/index.html",
        status=200,
        content_type="text/html",
        response_ms=1,
        title="EN",
        meta_description="d" * 60,
        meta_robots=None,
        canonical="https://x/en/",
        h1=["H"],
        html_lang="en",
        og_title="og",
        has_viewport=True,
        hreflangs=[
            {"lang": "zh-HK", "url": "/zh/", "resolved": "https://x/zh/index.html"},
            {"lang": "fr", "url": "/fr/", "resolved": "https://x/fr/index.html"},
        ],
    )
    report.pages["https://x/zh/index.html"] = PageResult(
        url="https://x/zh/index.html",
        status=200,
        content_type="text/html",
        response_ms=1,
        title="ZH",
        meta_description="d" * 60,
        meta_robots=None,
        canonical="https://x/zh/",
        h1=["H"],
        html_lang="zh-HK",
        og_title="og",
        has_viewport=True,
        hreflangs=[
            {"lang": "en", "url": "/en/", "resolved": "https://x/en/index.html"},
        ],
    )

    def canon(u: str) -> str:
        return u.replace("/index.html", "/") if u.endswith("index.html") else u

    audit_hreflang(report, canonical_fn=lambda u: u)
    en = report.pages["https://x/en/index.html"]
    assert "hreflang_missing_self" in en.issues
