"""
依爬取結果產生 sitemap.xml（可索引 HTML 頁）。
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from sitespider.crawler import CrawlReport
from sitespider.robots import meta_robots_noindex

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def export_sitemap_xml(report: CrawlReport, path: Path) -> int:
    """寫入 sitemap.xml，回傳 URL 數。"""
    urlset = ET.Element("urlset", xmlns=SITEMAP_NS)
    count = 0
    for url, page in sorted(report.pages.items()):
        if page.status != 200:
            continue
        if page.indexability == "Non-Indexable":
            continue
        if meta_robots_noindex(page.meta_robots):
            continue
        if page.blocked_by_robots:
            continue
        loc = (page.canonical or url).strip()
        if not loc:
            continue
        node = ET.SubElement(urlset, "url")
        ET.SubElement(node, "loc").text = loc
        count += 1

    tree = ET.ElementTree(urlset)
    ET.indent(tree, space="  ")
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return count
