"""
sitemap.xml 解析 — 作為爬取種子 URL。
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _local_name(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _find_loc(parent) -> str | None:
    for el in parent:
        if _local_name(el.tag) == "loc" and el.text:
            return el.text.strip()
    loc = parent.find("sm:loc", SITEMAP_NS)
    if loc is not None and loc.text:
        return loc.text.strip()
    return None


def parse_sitemap_xml(content: str, base_url: str) -> list[str]:
    """解析 urlset 或 sitemapindex，回傳頁面 URL 列表。"""
    urls: list[str] = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return urls

    root_tag = _local_name(root.tag)
    if root_tag == "sitemapindex":
        for child in root:
            if _local_name(child.tag) != "sitemap":
                continue
            loc = _find_loc(child)
            if loc:
                urls.append(loc)
        return urls

    if root_tag == "urlset":
        for url_el in root:
            if _local_name(url_el.tag) != "url":
                continue
            loc = _find_loc(url_el)
            if loc:
                urls.append(loc)
    return urls


def fetch_sitemap_urls(
    base_url: str,
    *,
    site_root: Path | None = None,
    mode: str = "http",
    session: requests.Session | None = None,
    extra_sitemap_urls: list[str] | None = None,
    user_agent: str = "VitaPure-SEO-Crawler/1.0",
) -> tuple[list[str], list[str]]:
    """
    回傳 (page_urls, errors)。
    會遞迴解析 sitemap index（最多 3 層）。
    """
    session = session or requests.Session()
    errors: list[str] = []
    page_urls: list[str] = []
    seen_sitemaps: set[str] = set()

    seeds: list[str] = list(extra_sitemap_urls or [])
    if mode == "file" and site_root:
        local = site_root / "sitemap.xml"
        if local.exists():
            seeds.insert(0, local.as_uri())
        else:
            errors.append(f"找不到 {local}")
    else:
        p = urlparse(base_url)
        seeds.insert(0, f"{p.scheme}://{p.netloc}/sitemap.xml")

    def process_sitemap(sitemap_url: str, depth: int) -> None:
        if sitemap_url in seen_sitemaps or depth > 3:
            return
        seen_sitemaps.add(sitemap_url)

        try:
            if sitemap_url.startswith("file:"):
                path = Path(urlparse(sitemap_url).path)
                content = path.read_text(encoding="utf-8", errors="replace")
            else:
                r = session.get(
                    sitemap_url, timeout=15, headers={"User-Agent": user_agent}
                )
                if r.status_code == 404:
                    return
                r.raise_for_status()
                content = r.text
        except (OSError, requests.RequestException) as e:
            errors.append(f"sitemap {sitemap_url}: {e}")
            return

        found = parse_sitemap_xml(content, base_url)
        for u in found:
            if not u.startswith(("http://", "https://", "file:")):
                u = urljoin(base_url, u)
            if u.endswith(".xml") or "sitemap" in Path(urlparse(u).path).name.lower():
                process_sitemap(u, depth + 1)
            else:
                page_urls.append(u)

    for s in seeds:
        process_sitemap(s, 0)

    # file 模式：將相對路徑轉為 file://
    if mode == "file" and site_root:
        normalized: list[str] = []
        for u in page_urls:
            if u.startswith("file:"):
                normalized.append(u)
            elif u.startswith("http"):
                fp = _http_url_to_local_path(u, site_root)
                if fp:
                    normalized.append(fp.as_uri())
            else:
                fp = site_root / u.lstrip("/")
                if fp.exists():
                    normalized.append(fp.as_uri())
        page_urls = normalized

    return list(dict.fromkeys(page_urls)), errors


def _http_url_to_local_path(url: str, site_root: Path) -> Path | None:
    path = urlparse(url).path.lstrip("/")
    if path.startswith("cal/"):
        path = path[4:]
    fp = site_root / path
    return fp if fp.exists() else None


def file_urls_from_sitemap(site_root: Path) -> list[str]:
    path = site_root / "sitemap.xml"
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8", errors="replace")
    base = site_root.as_uri() + "/"
    raw = parse_sitemap_xml(content, base)
    out: list[str] = []
    for u in raw:
        if u.startswith("http"):
            fp = _http_url_to_local_path(u, site_root)
        elif u.startswith("file:"):
            fp = Path(urlparse(u).path)
        else:
            fp = site_root / u.lstrip("/")
        if fp and fp.suffix in (".html", ".htm") and fp.exists():
            out.append(fp.as_uri())
    return out
