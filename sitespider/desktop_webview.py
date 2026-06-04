"""本機內嵌視窗（pywebview）— 選用依賴 sitespider[desktop]。"""

from __future__ import annotations


def webview_available() -> bool:
    try:
        import webview  # noqa: F401

        return True
    except ImportError:
        return False


def run_webview(
    url: str,
    *,
    title: str = "SiteSpider",
    width: int = 1440,
    height: int = 920,
) -> None:
    """阻塞直到使用者關閉視窗。"""
    import webview

    window = webview.create_window(
        title,
        url,
        width=width,
        height=height,
        min_size=(1000, 680),
        text_select=True,
    )
    webview.start(debug=False)
