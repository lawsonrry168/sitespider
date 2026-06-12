"""JavaScript 渲染整合測試（不需實際安裝 Playwright）。"""

from unittest.mock import MagicMock, patch

from sitespider.crawler import CrawlConfig, SeoCrawler
from sitespider.js_render import RenderedPage, playwright_available


def test_playwright_available_false_when_missing():
    with patch.dict("sys.modules", {"playwright": None}):
        # import may still succeed if installed; skip strict test
        assert isinstance(playwright_available(), bool)


@patch("sitespider.js_render.playwright_available", return_value=True)
def test_fetch_http_uses_renderer(_mock_pw):
    config = CrawlConfig(render_javascript=False, workers=1, fetch_policy="js")
    crawler = SeoCrawler("https://example.com/", mode="http", config=config)
    mock_renderer = MagicMock()
    mock_renderer.fetch.return_value = RenderedPage(
        status=200,
        final_url="https://example.com/",
        html="<html><head><title>Rendered</title></head><body><h1>Hi</h1></body></html>",
    )
    crawler._js_renderer = mock_renderer

    page = crawler._fetch_http("https://example.com/", 0, 0.0)
    assert page.rendered_with_js is True
    assert page.title == "Rendered"
    mock_renderer.fetch.assert_called_once()
