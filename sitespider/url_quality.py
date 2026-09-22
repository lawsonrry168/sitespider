"""
URL 品質稽核：大小寫、底線、非 ASCII、重複路徑段。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlparse

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport, PageResult

from sitespider.robots import meta_robots_noindex

_ASCII_RE = re.compile(r"^[\x00-\x7F]+$")


def _issue(page: PageResult, code: str) -> None:
    if code not in page.issues:
        page.issues.append(code)


def _path_segments(path: str) -> list[str]:
    return [s for s in path.split("/") if s]


def has_repetitive_path(path: str) -> bool:
    """連續或交錯重複的路徑段，如 /blog/blog/ 或 /a/b/a/b。"""
    segs = _path_segments(path)
    if len(segs) < 2:
        return False
    for i in range(len(segs) - 1):
        if segs[i] == segs[i + 1]:
            return True
    if len(segs) >= 4:
        half = len(segs) // 2
        if segs[:half] == segs[half : half * 2]:
            return True
    return False


def audit_url_quality(report: CrawlReport) -> None:
    for page in report.pages.values():
        if page.status >= 400 or page.blocked_by_robots:
            continue
        if meta_robots_noindex(page.meta_robots):
            continue
        parsed = urlparse(page.url)
        path = unquote(parsed.path or "/")
        if any(c.isupper() for c in path):
            _issue(page, "url_uppercase")
        if "_" in path:
            _issue(page, "url_underscore")
        if not _ASCII_RE.match(path):
            _issue(page, "url_non_ascii")
        if has_repetitive_path(path):
            _issue(page, "url_repetitive_path")
