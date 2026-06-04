"""Normalize user-supplied crawl start URLs (fix common paste / urljoin glitches)."""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse


def sanitize_start_url(raw: str) -> str:
    """Fix URLs like https://site/zh/index://example.com/ from bad merges."""
    s = (raw or "").strip()
    if not s:
        return s
    try:
        p = urlparse(s)
    except ValueError:
        return s
    if p.scheme not in ("http", "https") or not p.netloc:
        return s

    path = p.path or "/"
    if "://" not in path:
        return urlunparse((p.scheme, p.netloc, path, p.params, p.query, ""))

    idx = path.find("://")
    prefix = path[:idx]
    if prefix.endswith("/index"):
        path = prefix[:-6] + "/"
    elif prefix.endswith("index"):
        path = prefix[:-5] + "/"
    elif prefix.endswith("/"):
        path = prefix
    else:
        path = prefix + "/"

    if not path.startswith("/"):
        path = "/" + path
    return urlunparse((p.scheme, p.netloc, path, p.params, p.query, ""))


def start_url_looks_invalid(raw: str) -> str | None:
    """Return a short user-facing reason if URL should be blocked before crawl."""
    s = (raw or "").strip()
    if not s:
        return "請輸入起始 URL"
    try:
        p = urlparse(s)
    except ValueError:
        return "URL 格式無效"
    if p.scheme not in ("http", "https") or not p.netloc:
        return "請使用完整的 https:// 網址"
    if "://" in (p.path or ""):
        return "URL 含有無效片段（請刪除多餘的 :// 或 example.com）"
    if re.search(r"example\.com", s, re.I) and re.search(r"vitagreen|123deal|allure", s, re.I):
        return "起始 URL 似乎混入了範例網址，請只保留客戶網域"
    return None
