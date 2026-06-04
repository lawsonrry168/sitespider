"""頁面 SEO 稽核邏輯測試。"""

from sitespider.crawler import CrawlConfig, LinkInfo, PageResult, _audit_page


def _page(**kwargs) -> PageResult:
    defaults = dict(
        url="https://example.com/page.html",
        status=200,
        content_type="text/html",
        response_ms=10,
        title="A Good Title For SEO Testing",
        meta_description="A" * 60,
        meta_robots=None,
        canonical="https://example.com/page.html",
        h1=["Main Heading"],
        word_count=400,
        html_lang="zh-TW",
        og_title="OG",
        has_json_ld=True,
        has_viewport=True,
        redirect_chain=[],
    )
    defaults.update(kwargs)
    return PageResult(**defaults)


def test_clean_page_no_issues():
    p = _page()
    _audit_page(p, CrawlConfig(thin_content_min_words=300))
    assert p.issues == []


def test_missing_canonical():
    p = _page(canonical=None)
    _audit_page(p)
    assert "missing_canonical" in p.issues


def test_canonical_mismatch():
    p = _page(canonical="https://example.com/other.html")
    _audit_page(p)
    assert "canonical_mismatch" in p.issues


def test_thin_content():
    p = _page(word_count=50)
    _audit_page(p, CrawlConfig(thin_content_min_words=300))
    assert "thin_content" in p.issues


def test_thin_content_disabled():
    p = _page(word_count=10)
    _audit_page(p, CrawlConfig(thin_content_min_words=0))
    assert "thin_content" not in p.issues


def test_missing_html_lang():
    p = _page(html_lang=None)
    _audit_page(p)
    assert "missing_html_lang" in p.issues


def test_broken_internal_link():
    p = _page(
        links=[
            LinkInfo(
                href="/broken",
                text="x",
                resolved="https://example.com/broken",
                link_type="internal",
                status=404,
            )
        ]
    )
    _audit_page(p)
    assert "broken_internal_link" in p.issues


def test_require_json_ld():
    p = _page(has_json_ld=False)
    _audit_page(p, CrawlConfig(require_json_ld=False))
    assert "missing_json_ld" not in p.issues
    _audit_page(p, CrawlConfig(require_json_ld=True))
    assert "missing_json_ld" in p.issues


def test_missing_viewport():
    p = _page(has_viewport=False)
    _audit_page(p)
    assert "missing_viewport" in p.issues


def test_redirect_chain():
    p = _page(redirect_chain=["https://a.com/old", "https://a.com/new"])
    _audit_page(p)
    assert "redirect_chain" in p.issues


def test_meta_noindex_skips_other_checks():
    p = _page(meta_robots="noindex, follow", title=None, canonical=None)
    _audit_page(p)
    assert p.issues == ["meta_noindex"]
