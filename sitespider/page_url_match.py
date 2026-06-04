"""將任意 URL 對應到爬蟲 report.pages 的 key（含 /index.html 變體）。"""

from __future__ import annotations

from typing import Iterable
from urllib.parse import urlparse, urlunparse


def page_url_aliases(url: str) -> list[str]:
    """產生可能對應到同一頁的 URL 變體（不含 fragment）。"""
    url = (url or "").strip()
    if not url:
        return []
    p = urlparse(url)
    if p.fragment:
        p = p._replace(fragment="")
        url = urlunparse(p)
    out: list[str] = []
    seen: set[str] = set()

    def add(u: str) -> None:
        if u and u not in seen:
            seen.add(u)
            out.append(u)

    add(url)
    path = p.path or "/"
    scheme, netloc, query = p.scheme, p.netloc, p.query

    if path.endswith("/index.html"):
        base = path[: -len("index.html")] or "/"
        add(urlunparse((scheme, netloc, base, "", query, "")))
        if base not in ("/", ""):
            add(urlunparse((scheme, netloc, base.rstrip("/"), "", query, "")))
    if path.endswith("/") and path not in ("/", ""):
        add(urlunparse((scheme, netloc, path + "index.html", "", query, "")))
    if path != "/" and not path.endswith("/"):
        add(urlunparse((scheme, netloc, path + "/", "", query, "")))
        add(urlunparse((scheme, netloc, path + "/index.html", "", query, "")))
    if path == "/":
        add(urlunparse((scheme, netloc, "/index.html", "", query, "")))

    return out


def build_page_url_index(page_keys: Iterable[str]) -> dict[str, str]:
    """別名 URL → 爬蟲實際 page key。"""
    index: dict[str, str] = {}
    for key in page_keys:
        if not key:
            continue
        for alias in page_url_aliases(key):
            index.setdefault(alias, key)
        index.setdefault(key, key)
    return index


def resolve_page_url(url: str, page_keys: Iterable[str] | dict[str, object]) -> str | None:
    """將 URL 解析為 report.pages 中的 key；無法對應時回傳 None。"""
    if isinstance(page_keys, dict):
        keys = page_keys
        if url in keys:
            return url
        index = build_page_url_index(keys)
    else:
        keys_list = list(page_keys)
        if url in keys_list:
            return url
        index = build_page_url_index(keys_list)
    if not url:
        return None
    for alias in page_url_aliases(url):
        hit = index.get(alias)
        if hit:
            return hit
    return None
