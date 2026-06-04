"""
Rich Results 啟發式檢查（無 Google API；依 JSON-LD @type 與頁型推斷）。
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport, PageResult

# Google 常見 Rich Result 類型 → 簡要資格說明
_TYPE_HINTS: dict[str, str] = {
    "Product": "需 name、image、offers（爬蟲僅見 @type，請以 SDTT 驗證）",
    "FAQPage": "需 mainEntity Question/Answer",
    "HowTo": "需 step 或 name",
    "LocalBusiness": "需 name、address",
    "Organization": "需 name、url 或 logo",
    "BreadcrumbList": "需 itemListElement",
    "Article": "需 headline、author、datePublished",
    "WebSite": "可含 SearchAction（站內搜尋框）",
    "Review": "需 itemReviewed、reviewRating",
    "Event": "需 startDate、location",
    "Recipe": "需 name、recipeIngredient",
    "VideoObject": "需 name、thumbnailUrl、uploadDate",
}

_PATH_EXPECTED: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("/product", ("Product",)),
    ("/products", ("Product",)),
    ("/faq", ("FAQPage",)),
    ("/blog", ("Article", "BlogPosting")),
    ("/article", ("Article", "BlogPosting")),
    ("/recipe", ("Recipe",)),
    ("/event", ("Event",)),
)


def _path_suggests_types(path: str) -> tuple[str, ...]:
    low = path.lower()
    found: list[str] = []
    for frag, types in _PATH_EXPECTED:
        if frag in low:
            found.extend(types)
    return tuple(dict.fromkeys(found))


def evaluate_rich_results(page: PageResult) -> dict[str, str]:
    """回傳單頁 Rich Results 評估列。"""
    types = list(page.json_ld_types or [])
    path = urlparse(page.url).path or "/"
    suggested = _path_suggests_types(path)

    if page.status != 200:
        return {
            "Address": page.url,
            "Status": "Skipped",
            "JSON-LD Types": "; ".join(types),
            "Eligible Types": "",
            "Rich Result Status": "",
            "Notes": f"HTTP {page.status}",
        }

    if not page.has_json_ld:
        note = "無 JSON-LD"
        if suggested:
            note += f"；路徑建議：{', '.join(suggested)}"
        return {
            "Address": page.url,
            "Status": "No Schema",
            "JSON-LD Types": "",
            "Eligible Types": "",
            "Rich Result Status": "Not eligible",
            "Notes": note,
        }

    eligible = [t for t in types if t in _TYPE_HINTS]
    missing_suggested = [t for t in suggested if t not in types]
    notes: list[str] = []
    for t in eligible:
        notes.append(f"{t}: {_TYPE_HINTS[t]}")
    if missing_suggested:
        notes.append(f"路徑建議缺少：{', '.join(missing_suggested)}")

    status = "Eligible (heuristic)" if eligible else "Schema present"
    if missing_suggested and page.indexability == "Indexable":
        status = "Review recommended"

    return {
        "Address": page.url,
        "Status": "OK" if eligible else "Review",
        "JSON-LD Types": "; ".join(types),
        "Eligible Types": "; ".join(eligible),
        "Rich Result Status": status,
        "Notes": " · ".join(notes) if notes else "",
    }


def export_rich_results_csv(report: CrawlReport, path: Path) -> None:
    fields = [
        "Address",
        "Status",
        "JSON-LD Types",
        "Eligible Types",
        "Rich Result Status",
        "Notes",
    ]
    rows = [evaluate_rich_results(p) for p in sorted(report.pages.values(), key=lambda x: x.url)]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
