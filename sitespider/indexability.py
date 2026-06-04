"""
Indexability 判定（對齊 Screaming Frog Internal 檢視欄位）。
"""

from __future__ import annotations

from sitespider.crawler import PageResult, _canonical_for_compare
from sitespider.robots import meta_robots_noindex


def compute_indexability(page: PageResult) -> tuple[str, str]:
    """
    回傳 (Indexability, Indexability Status)。
    Indexability: Indexable | Non-Indexable
  """
    if page.blocked_by_robots:
        return "Non-Indexable", "Blocked by robots.txt"

    if page.status == 0:
        return "Non-Indexable", "Request failed"

    if page.status >= 500:
        return "Non-Indexable", f"Server Error ({page.status})"

    if page.status >= 400:
        return "Non-Indexable", f"Client Error ({page.status})"

    if page.status in (301, 302, 303, 307, 308) or len(page.redirect_chain) > 1:
        return "Non-Indexable", "Redirected"

    if meta_robots_noindex(page.meta_robots):
        return "Non-Indexable", "Noindex"

    if page.canonical:
        page_norm = _canonical_for_compare(page.url)
        canon_norm = _canonical_for_compare(page.canonical)
        if page_norm and canon_norm and page_norm != canon_norm:
            return "Non-Indexable", "Canonicalised"

    return "Indexable", ""


def apply_indexability(page: PageResult) -> None:
    idx, status = compute_indexability(page)
    page.indexability = idx
    page.indexability_status = status
