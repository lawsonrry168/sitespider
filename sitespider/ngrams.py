"""
站內 N-gram 統計（對齊 Screaming Frog N-grams 分頁，以 title / H1 / meta 為來源）。
"""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def _page_text(page) -> str:
    parts = [page.title or "", page.meta_description or "", " ".join(page.h1 or [])]
    return " ".join(p for p in parts if p).strip()


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text) if len(t) >= 2]


def collect_ngrams(
    report: CrawlReport,
    *,
    sizes: tuple[int, ...] = (2, 3),
    min_count: int = 2,
    top_per_size: int = 400,
) -> list[dict[str, str | int]]:
    """回傳依出現次數排序的 n-gram 列。"""
    rows: list[dict[str, str | int]] = []
    for n in sizes:
        counts: Counter[str] = Counter()
        samples: dict[str, list[str]] = defaultdict(list)
        for url, page in report.pages.items():
            if page.status != 200:
                continue
            tokens = tokenize(_page_text(page))
            if len(tokens) < n:
                continue
            for i in range(len(tokens) - n + 1):
                gram = " ".join(tokens[i : i + n])
                if len(gram) < 4:
                    continue
                counts[gram] += 1
                if len(samples[gram]) < 3 and url not in samples[gram]:
                    samples[gram].append(url)
        for gram, count in counts.most_common(top_per_size):
            if count < min_count:
                continue
            rows.append(
                {
                    "N": n,
                    "Phrase": gram,
                    "Count": count,
                    "Sample URLs": " | ".join(samples[gram]),
                }
            )
    rows.sort(key=lambda r: (-int(r["Count"]), str(r["Phrase"])))
    return rows


def export_ngrams_csv(report: CrawlReport, path: Path) -> None:
    rows = collect_ngrams(report)
    fields = ["N", "Phrase", "Count", "Sample URLs"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
