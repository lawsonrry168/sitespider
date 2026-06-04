"""SEO / GEO brief 與可選 AI 潤飾。"""

from __future__ import annotations

from sitespider.crawler import CrawlConfig, CrawlReport, PageResult
from sitespider.ai_client import ai_configured
from sitespider.seo_briefs import (
    build_page_briefs,
    export_seo_briefs_bundle,
    export_seo_briefs_md,
)


def _report() -> CrawlReport:
    r = CrawlReport(start_url="https://shop.example/", mode="http", config=CrawlConfig())
    base = dict(
        status=200,
        content_type="text/html",
        response_ms=100.0,
        meta_robots=None,
        canonical="https://shop.example/p",
    )
    r.pages["https://shop.example/"] = PageResult(
        url="https://shop.example/",
        title="Shop",
        meta_description="Short",
        h1=["Welcome"],
        word_count=80,
        issues=["thin_content", "meta_description_too_short", "missing_alt"],
        **{**base, "canonical": "https://shop.example/"},
    )
    r.pages["https://shop.example/product/a"] = PageResult(
        url="https://shop.example/product/a",
        title="Product A | Shop",
        meta_description="",
        h1=[],
        word_count=120,
        issues=["missing_meta_description", "missing_h1"],
        **base,
    )
    r.pages["https://shop.example/product/a"].inlinks = ["https://shop.example/"]
    return r


def test_build_page_briefs():
    briefs = build_page_briefs(_report(), limit=5)
    assert briefs
    assert any("meta" in b.meta_advice.lower() for b in briefs)
    assert briefs[0].priority_score >= 0


def test_export_seo_briefs_md(tmp_path):
    report = _report()
    briefs = build_page_briefs(report)
    export_seo_briefs_md(report, briefs, tmp_path / "seo-briefs.md")
    text = (tmp_path / "seo-briefs.md").read_text(encoding="utf-8")
    assert "SEO / GEO 文案 Brief" in text
    assert "shop.example" in text


def test_export_bundle(tmp_path):
    written = export_seo_briefs_bundle(_report(), tmp_path, site_label="Test Shop")
    assert "seo-briefs.html" in written
    assert "seo-briefs.md" in written
    assert isinstance(ai_configured(), bool)
