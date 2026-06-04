"""控制台 HTML 路徑對應（含 /guide 尾端斜線）。"""

from sitespider.server import resolve_console_html


def test_guide_routes():
    assert resolve_console_html("/guide") == "guide.html"
    assert resolve_console_html("/guide/") == "guide.html"
    assert resolve_console_html("/guide.html") == "guide.html"
    assert resolve_console_html("/help") == "guide.html"


def test_dashboard_routes():
    assert resolve_console_html("/") == "dashboard.html"
    assert resolve_console_html("/dashboard/") == "dashboard.html"
