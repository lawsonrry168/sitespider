"""本機桌面啟動器輔助函式。"""

from sitespider.desktop_launcher import _with_desktop_query
from sitespider.desktop_webview import webview_available


def test_with_desktop_query():
    assert _with_desktop_query("/") == "/?desktop=1"
    assert _with_desktop_query("/guide") == "/guide?desktop=1"
    assert _with_desktop_query("/x?a=1") == "/x?a=1&desktop=1"
    assert _with_desktop_query("/x?desktop=0") == "/x?desktop=0"


def test_webview_available_is_bool():
    assert isinstance(webview_available(), bool)
