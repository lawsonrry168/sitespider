"""
GEO（Generative Engine Optimization）就緒度：以可量化訊號輸出。

設計目標：
- 不依賴外部 API
- 以現有爬蟲資料（JSON-LD types、索引性、內容）估算「可被引用」與「結構化程度」
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from sitespider.crawler import CrawlReport


@dataclass(frozen=True)
class GeoRow:
    url: str
    score: int
    indexable: bool
    word_count: int
    has_schema: bool
    schema_types: str
    has_faq: bool
    has_howto: bool
    has_product: bool
    has_localbusiness: bool
    has_article: bool


_FAQ = {"FAQPage"}
_HOWTO = {"HowTo"}
_PRODUCT = {"Product"}
_LOCAL = {"LocalBusiness"}
_ARTICLE = {"Article", "BlogPosting", "NewsArticle"}


def _has_any(types: set[str], candidates: set[str]) -> bool:
    return any(t in types for t in candidates)


def compute_geo_rows(report: CrawlReport) -> list[GeoRow]:
    rows: list[GeoRow] = []
    for url, p in sorted(report.pages.items()):
        types = set(p.json_ld_types or [])
        has_schema = bool(types)
        has_faq = _has_any(types, _FAQ)
        has_howto = _has_any(types, _HOWTO)
        has_product = _has_any(types, _PRODUCT)
        has_local = _has_any(types, _LOCAL)
        has_article = _has_any(types, _ARTICLE)

        # 粗略 GEO score（0–100），偏「可引用性/結構化」
        score = 0
        if p.indexability == "Indexable" and p.status == 200:
            score += 30
        if (p.meta_description or "").strip():
            score += 10
        if (p.title or "").strip():
            score += 10
        if p.word_count >= 200:
            score += 10
        if has_schema:
            score += 15
        if has_faq:
            score += 10
        if has_howto:
            score += 10
        if has_product or has_local or has_article:
            score += 5
        score = min(100, score)

        rows.append(
            GeoRow(
                url=url,
                score=score,
                indexable=p.indexability == "Indexable",
                word_count=p.word_count,
                has_schema=has_schema,
                schema_types="; ".join(sorted(types))[:300],
                has_faq=has_faq,
                has_howto=has_howto,
                has_product=has_product,
                has_localbusiness=has_local,
                has_article=has_article,
            )
        )
    return rows


def compute_geo_summary(report: CrawlReport) -> dict:
    rows = compute_geo_rows(report)
    if not rows:
        return {"pages": 0}
    scores = [r.score for r in rows]
    avg = round(sum(scores) / max(1, len(scores)), 1)
    by_bucket = Counter(
        "80–100"
        if s >= 80
        else ("60–79" if s >= 60 else ("40–59" if s >= 40 else "0–39"))
        for s in scores
    )
    schema_cover = Counter()
    for r in rows:
        if r.has_faq:
            schema_cover["FAQPage"] += 1
        if r.has_howto:
            schema_cover["HowTo"] += 1
        if r.has_product:
            schema_cover["Product"] += 1
        if r.has_localbusiness:
            schema_cover["LocalBusiness"] += 1
        if r.has_article:
            schema_cover["Article"] += 1
    return {
        "pages": len(rows),
        "avg_score": avg,
        "score_buckets": dict(by_bucket),
        "schema_coverage": dict(schema_cover),
    }


def export_geo_csv(report: CrawlReport, path: Path) -> None:
    fields = [
        "Address",
        "GEO Score",
        "Indexable",
        "Word Count",
        "Has JSON-LD",
        "JSON-LD Types",
        "FAQPage",
        "HowTo",
        "Product",
        "LocalBusiness",
        "Article",
    ]
    rows = compute_geo_rows(report)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(
                {
                    "Address": r.url,
                    "GEO Score": r.score,
                    "Indexable": "Yes" if r.indexable else "",
                    "Word Count": r.word_count,
                    "Has JSON-LD": "Yes" if r.has_schema else "",
                    "JSON-LD Types": r.schema_types,
                    "FAQPage": "Yes" if r.has_faq else "",
                    "HowTo": "Yes" if r.has_howto else "",
                    "Product": "Yes" if r.has_product else "",
                    "LocalBusiness": "Yes" if r.has_localbusiness else "",
                    "Article": "Yes" if r.has_article else "",
                }
            )
