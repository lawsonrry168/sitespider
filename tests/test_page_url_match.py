"""頁面 URL 對應（爬蟲 key ↔ AI / 連結變體）。"""

from sitespider.page_url_match import resolve_page_url


def test_resolve_trailing_slash_and_index_html():
    keys = {
        "https://example.com/zh/index.html",
        "https://example.com/about/index.html",
    }
    assert resolve_page_url("https://example.com/zh/", keys) == "https://example.com/zh/index.html"
    assert resolve_page_url("https://example.com/about/", keys) == "https://example.com/about/index.html"


def test_resolve_ai_style_path_without_index():
    keys = {"https://x.com/foo/index.html"}
    assert resolve_page_url("https://x.com/foo", keys) == "https://x.com/foo/index.html"
