"""Shopline robots.txt 不應因其他 bot 的 Disallow: / 封鎖全站。"""

import requests
from urllib.robotparser import RobotFileParser

from sitespider.robots import RobotsManager


def test_shopline_robots_allows_product_pages():
    ua = "SiteSpider/1.0 (+https://github.com/sitespider/seo-crawl)"
    mgr = RobotsManager(
        "https://www.saanfolouhk.com/",
        ua,
        mode="http",
        session=requests.Session(),
    )
    assert mgr.allowed("https://www.saanfolouhk.com/products/test-item")
    assert mgr.allowed("https://www.saanfolouhk.com/")


def test_robotparser_default_allows_when_no_matching_block():
    text = requests.get("https://www.saanfolouhk.com/robots.txt", timeout=15).text
    p = RobotFileParser()
    p.parse(text.splitlines())
    assert p.can_fetch("SiteSpider/1.0", "https://www.saanfolouhk.com/products/foo")
