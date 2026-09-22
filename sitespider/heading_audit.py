"""
標題層級（H1–H6）跳級稽核。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport, PageResult

from sitespider.robots import meta_robots_noindex


def _issue(page: PageResult, code: str) -> None:
    if code not in page.issues:
        page.issues.append(code)


def _heading_sequence(page: PageResult) -> list[int]:
    seq = getattr(page, "heading_sequence", None)
    if seq:
        return [int(x) for x in seq if int(x) >= 1]
    # 後備：由 h1/h2/h3 列表推估（僅能反映各層級是否存在，非 DOM 順序）
    out: list[int] = []
    if page.h1:
        out.append(1)
    if page.h2:
        out.append(2)
    if page.h3:
        out.append(3)
    return out


def has_heading_skip(sequence: list[int]) -> bool:
    """層級跳過（如 1→3）回傳 True。"""
    prev: int | None = None
    for level in sequence:
        if level < 1 or level > 6:
            continue
        if prev is not None and level > prev + 1:
            return True
        prev = level
    return False


def audit_heading_hierarchy(report: CrawlReport) -> None:
    for page in report.pages.values():
        if page.status >= 400 or page.blocked_by_robots:
            continue
        if meta_robots_noindex(page.meta_robots):
            continue
        seq = _heading_sequence(page)
        if has_heading_skip(seq):
            _issue(page, "heading_skip")
