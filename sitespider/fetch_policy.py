"""依 URL／回應決定 HTTP 或 JS 渲染（Scrapling 多 fetcher 概念精簡版）。"""

from __future__ import annotations

import re
from typing import Literal
from urllib.parse import urlparse

FetchMode = Literal["http", "js"]

_DEFAULT_AUTO_JS = (
    r"/products?/",
    r"/product/",
    r"/collections?/",
    r"/shop/",
    r"/app/",
    r"/checkout",
)


def resolve_fetch_mode(
    url: str,
    *,
    policy: str,
    render_javascript: bool,
    auto_patterns: tuple[str, ...] = (),
) -> FetchMode:
    """決定此 URL 用 HTTP 或 Playwright。"""
    pol = (policy or "http").lower()
    if render_javascript and pol == "http":
        return "js"
    if pol == "js":
        return "js"
    if pol == "auto":
        path = urlparse(url).path or "/"
        patterns = auto_patterns or _DEFAULT_AUTO_JS
        for pat in patterns:
            if re.search(pat, path, re.I):
                return "js"
        return "http"
    return "http"


def should_retry_with_js(
    html: str,
    *,
    word_count: int,
    min_words: int = 80,
) -> bool:
    """HTTP 回應過薄或像 SPA 殼時，auto 模式改走 JS。"""
    if word_count >= min_words:
        return False
    if not html:
        return True
    lower = html.lower()
    if "id=\"__next\"" in lower or "id=\"root\"" in lower or "data-reactroot" in lower:
        return True
    if lower.count("<script") >= 4 and word_count < 40:
        return True
    return word_count < 25
