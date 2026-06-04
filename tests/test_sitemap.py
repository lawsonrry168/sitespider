"""Sitemap 解析單元測試。"""

from pathlib import Path

from sitespider.sitemap import parse_sitemap_xml, file_urls_from_sitemap, _http_url_to_local_path

SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/cal/index.html</loc></url>
  <url><loc>/about.html</loc></url>
</urlset>
"""


def test_parse_sitemap_xml():
    urls = parse_sitemap_xml(SAMPLE, "https://example.com/")
    assert "https://example.com/cal/index.html" in urls
    assert "/about.html" in urls


def test_http_url_to_local_path(tmp_path: Path):
    (tmp_path / "index.html").write_text("<html></html>")
    fp = _http_url_to_local_path(
        "https://x.github.io/cal/index.html",
        tmp_path,
        path_prefixes=("cal/",),
    )
    assert fp is not None and fp.name == "index.html"
