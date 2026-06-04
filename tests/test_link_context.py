"""連結語意與版位偵測測試。"""

from bs4 import BeautifulSoup

from sitespider.link_context import (
    POSITION_FOOTER,
    POSITION_NAV,
    detect_link_position,
    is_nofollow,
)


def test_is_nofollow():
    assert is_nofollow("nofollow")
    assert is_nofollow(["noopener", "nofollow"])
    assert not is_nofollow(None)
    assert not is_nofollow("follow")


def test_detect_link_position_nav_footer():
    html = """
    <body>
      <nav class="main-menu"><a href="/a">A</a></nav>
      <main><a href="/b">B</a></main>
      <footer id="site-footer"><a href="/c">C</a></footer>
    </body>
    """
    soup = BeautifulSoup(html, "lxml")
    links = soup.find_all("a")
    assert detect_link_position(links[0]) == POSITION_NAV
    assert detect_link_position(links[1]) == "Content"
    assert detect_link_position(links[2]) == POSITION_FOOTER
