"""Indexability 判定測試（對齊 Screaming Frog）。"""

from sitespider.crawler import PageResult
from sitespider.indexability import compute_indexability


def _page(**kwargs) -> PageResult:
    defaults = dict(
        url="https://example.com/page",
        status=200,
        content_type="text/html",
        response_ms=10,
        title="Title",
        meta_description="desc",
        meta_robots=None,
        canonical="https://example.com/page",
    )
    defaults.update(kwargs)
    return PageResult(**defaults)


def test_indexable():
    idx, status = compute_indexability(_page())
    assert idx == "Indexable"
    assert status == ""


def test_canonicalised():
    idx, status = compute_indexability(
        _page(
            url="https://example.com/a",
            canonical="https://example.com/b",
        )
    )
    assert idx == "Non-Indexable"
    assert status == "Canonicalised"


def test_noindex():
    idx, status = compute_indexability(_page(meta_robots="noindex, follow"))
    assert idx == "Non-Indexable"
    assert status == "Noindex"
