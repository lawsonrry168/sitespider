"""
單頁 URL 檢視器 — 靜態 HTML，載入 crawl 摘要 JSON。
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from sitespider.crawler import CrawlReport
from sitespider.issues import ISSUE_LABELS
from sitespider.link_metrics import compute_page_link_stats, inlinks_for_destination
from sitespider.report_theme import report_styles_bundle, report_topbar


def export_page_inspector(report: CrawlReport, path: Path) -> None:
    stats = compute_page_link_stats(report)
    pages_data = []
    for url, p in sorted(report.pages.items()):
        st = stats.get(url)
        pages_data.append(
            {
                "url": url,
                "status": p.status,
                "title": p.title or "",
                "indexability": p.indexability,
                "indexability_status": p.indexability_status or "",
                "canonical": p.canonical or "",
                "depth": p.crawl_depth,
                "inlinks": st.unique_inlinks if st else len(p.inlinks),
                "outlinks": st.unique_outlinks if st else 0,
                "link_score": st.link_score if st else 0,
                "word_count": p.word_count,
                "issues": [
                    {"code": i, "label": ISSUE_LABELS.get(i, i)} for i in p.issues
                ],
                "inlink_urls": list(p.inlinks)[:50],
                "inlink_details": [
                    {
                        "source": r.source,
                        "anchor": r.anchor,
                        "follow": "Follow" if not r.nofollow else "Nofollow",
                        "position": r.link_position,
                    }
                    for r in inlinks_for_destination(report, url)[:80]
                ],
                "h1": p.h1,
                "meta_description": (p.meta_description or "")[:300],
            }
        )

    payload = json.dumps(
        {
            "start_url": report.start_url,
            "page_count": len(report.pages),
            "pages": pages_data,
        },
        ensure_ascii=False,
    )
    template = _UI.read_text(encoding="utf-8")
    css = report_styles_bundle()
    topbar = report_topbar(
        path.parent, "URL 檢視", active="inspector.html", site_url=report.start_url
    )
    html = (
        template.replace("{{START_URL}}", escape(report.start_url))
        .replace("{{PAGES_JSON}}", payload)
        .replace("{{REPORT_PAGES_CSS}}", css)
        .replace("{{REPORT_NAV}}", topbar)
    )
    path.write_text(html, encoding="utf-8")


_UI = Path(__file__).resolve().parent / "ui" / "page_inspector.html"
