"""
關鍵字密度與 keyword stuffing 稽核。
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport, PageResult

from sitespider.robots import meta_robots_noindex

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
_STOPWORDS = frozenset(
    """
    the a an and or but in on at to for of is are was were be been being
    with from by as it this that these those i you he she we they them
    的 了 是 在 我 有 和 就 不 人 都 一 一個 上 也 很 到 說 要 去 你 會
    """.split()
)


def _issue(page: PageResult, code: str) -> None:
    if code not in page.issues:
        page.issues.append(code)


def _page_text(page: PageResult) -> str:
    return (getattr(page, "body_text", None) or "").strip()


def tokenize_body(text: str) -> list[str]:
    return [
        t.lower()
        for t in _TOKEN_RE.findall(text)
        if len(t) >= 2 and t.lower() not in _STOPWORDS
    ]


def compute_keyword_density(page: PageResult, top_n: int = 20) -> list[tuple[str, float]]:
    tokens = tokenize_body(_page_text(page))
    if not tokens:
        return []
    counts = Counter(tokens)
    total = len(tokens)
    ranked = counts.most_common(top_n)
    return [(term, round(100.0 * count / total, 2)) for term, count in ranked]


def audit_keyword_density(report: CrawlReport) -> None:
    for page in report.pages.values():
        if page.status >= 400 or page.blocked_by_robots:
            continue
        if meta_robots_noindex(page.meta_robots):
            continue
        text = _page_text(page)
        if not text:
            continue
        tokens = tokenize_body(text)
        if not tokens:
            continue
        counts = Counter(tokens)
        total = len(tokens)
        density = [(term, round(100.0 * count / total, 2)) for term, count in counts.most_common(20)]
        page.keyword_density = density
        for term, pct in density:
            count = counts[term]
            if pct > 5.0 and count >= 5:
                _issue(page, "keyword_stuffing")
                break


def export_keyword_density_csv(report: CrawlReport, path: Path) -> None:
    path = Path(path)
    fields = ["Address", "Term", "Density %", "Count"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, page in sorted(report.pages.items()):
            text = _page_text(page)
            if not text:
                continue
            tokens = tokenize_body(text)
            counts = Counter(tokens)
            total = max(1, len(tokens))
            for term, pct in getattr(page, "keyword_density", None) or compute_keyword_density(page):
                w.writerow(
                    {
                        "Address": url,
                        "Term": term,
                        "Density %": pct,
                        "Count": counts.get(term, 0),
                    }
                )
