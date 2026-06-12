"""爬蟲引擎增強：fetch policy、快取、checkpoint、adaptive extract。"""

import json
from pathlib import Path

from sitespider.adaptive_extract import apply_extractions_adaptive, extract_json_ld_value
from sitespider.crawl_checkpoint import load_checkpoint, restore_from_checkpoint, save_checkpoint
from sitespider.crawler import CrawlConfig, CrawlReport, PageResult
from sitespider.custom_extract import ExtractionRule
from sitespider.fetch_policy import resolve_fetch_mode, should_retry_with_js
from sitespider.response_cache import ResponseCache


def test_resolve_fetch_mode_auto_products():
    mode = resolve_fetch_mode(
        "https://shop.example.com/products/foo",
        policy="auto",
        render_javascript=False,
    )
    assert mode == "js"
    mode_http = resolve_fetch_mode(
        "https://shop.example.com/about",
        policy="auto",
        render_javascript=False,
    )
    assert mode_http == "http"


def test_resolve_fetch_mode_render_js_compat():
    assert (
        resolve_fetch_mode(
            "https://x.com/",
            policy="http",
            render_javascript=True,
        )
        == "js"
    )


def test_should_retry_with_js_spa_shell():
    html = '<html><body><div id="root"></div><script></script><script></script></body></html>'
    assert should_retry_with_js(html, word_count=10)


def test_response_cache_roundtrip(tmp_path):
    cache = ResponseCache(tmp_path, enabled=True)
    cache.put(
        "https://example.com/",
        final_url="https://example.com/",
        status=200,
        headers={"content-type": "text/html"},
        text="<html><body>hi</body></html>",
    )
    got = cache.get("https://example.com/")
    assert got is not None
    assert got.status == 200
    assert "hi" in got.text


def test_checkpoint_save_restore(tmp_path):
    report = CrawlReport(start_url="https://x.com/", mode="http", config=CrawlConfig(max_pages=10))
    report.pages["https://x.com/"] = PageResult(
        url="https://x.com/",
        status=200,
        content_type="text/html",
        response_ms=1.0,
        title="Home",
        meta_description=None,
        meta_robots=None,
        canonical="https://x.com/",
    )
    seen = {"https://x.com/"}
    queue = [("https://x.com/about", 1, "https://x.com/", "link")]
    save_checkpoint(tmp_path, report=report, seen=seen, queue=queue)
    data = load_checkpoint(tmp_path)
    assert data is not None
    rep2, seen2, queue2, n = restore_from_checkpoint(data)
    assert n == 1
    assert "https://x.com/" in rep2.pages
    assert "https://x.com/" in seen2
    assert len(queue2) == 1


def test_adaptive_json_ld_price():
    html = """
    <script type="application/ld+json">
    {"@type":"Product","name":"T","offers":{"@type":"Offer","price":99.0}}
    </script>
    """
    val = extract_json_ld_value(html, "Product", "offers.price")
    assert val == "99.0"


def test_adaptive_extract_rule_chain():
    html = """
    <script type="application/ld+json">{"@type":"Product","sku":"ABC123"}</script>
    <div class="old-sku">ignored</div>
    """
    rules = (
        ExtractionRule(
            name="sku",
            css=".missing",
            json_ld_type="Product",
            json_ld_field="sku",
            adaptive=True,
        ),
    )
    out = apply_extractions_adaptive(html, rules)
    assert out["sku"] == "ABC123"
