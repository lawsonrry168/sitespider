"""JSON-LD 路徑規則稽核測試。"""

from sitespider.crawler import CrawlReport, PageResult
from sitespider.json_ld_audit import JsonLdRule, audit_json_ld_rules


def _page(url: str, types: list[str]) -> PageResult:
    return PageResult(
        url=url,
        status=200,
        content_type="text/html",
        response_ms=1,
        title="T",
        meta_description="x" * 60,
        meta_robots=None,
        canonical=url,
        h1=["H"],
        html_lang="zh-HK",
        og_title="og",
        has_viewport=True,
        has_json_ld=bool(types),
        json_ld_types=types,
    )


def test_json_ld_missing_type_on_product_path():
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/product/foo/"] = _page("https://x/product/foo/", ["WebPage"])
    rules = (JsonLdRule(types=("Product",), path_contains="/product/"),)
    audit_json_ld_rules(report, rules)
    assert "json_ld_missing_type" in report.pages["https://x/product/foo/"].issues


def test_json_ld_ok_when_type_present():
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/product/foo/"] = _page("https://x/product/foo/", ["Product", "WebPage"])
    rules = (JsonLdRule(types=("Product",), path_contains="/product/"),)
    audit_json_ld_rules(report, rules)
    assert "json_ld_missing_type" not in report.pages["https://x/product/foo/"].issues
