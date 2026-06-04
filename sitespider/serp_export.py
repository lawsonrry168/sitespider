"""
SERP 預覽匯出（標題／描述像素寬度與截斷風險）— 非即時 Google 排名抓取。
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

from sitespider.pixel_width import META_MAX_PX, TITLE_MAX_PX, serp_pixel_width

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport


def collect_serp_rows(report: CrawlReport) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for url, page in report.pages.items():
        if page.status != 200:
            continue
        title = page.title or ""
        meta = page.meta_description or ""
        t_px = page.serp_title_pixels or serp_pixel_width(title)
        m_px = page.serp_meta_pixels or serp_pixel_width(meta) if meta else 0
        rows.append(
            {
                "Address": url,
                "Title 1": title[:200],
                "Title 1 Pixel Width": t_px,
                "Title Over Limit": "Yes" if t_px > TITLE_MAX_PX else "",
                "Meta Description 1": meta[:300],
                "Meta Description 1 Pixel Width": m_px if meta else "",
                "Meta Over Limit": "Yes" if meta and m_px > META_MAX_PX else "",
                "Title Length": len(title),
                "Meta Length": len(meta),
            }
        )
    rows.sort(key=lambda r: (-int(r["Title 1 Pixel Width"] or 0), str(r["Address"])))
    return rows


def export_serp_snippets_csv(report: CrawlReport, path: Path) -> None:
    rows = collect_serp_rows(report)
    fields = [
        "Address",
        "Title 1",
        "Title 1 Pixel Width",
        "Title Over Limit",
        "Meta Description 1",
        "Meta Description 1 Pixel Width",
        "Meta Over Limit",
        "Title Length",
        "Meta Length",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
