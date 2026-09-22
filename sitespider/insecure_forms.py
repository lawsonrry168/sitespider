"""
HTTPS 頁面上的 HTTP 表單 action 稽核（需 page.form_actions: list[str]）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport


def audit_insecure_forms(report: CrawlReport) -> None:
    """若 page.is_https 且任一 form action 為 http://，標記 insecure_form_action。"""
    for page in report.pages.values():
        if not page.is_https or page.status != 200:
            continue
        actions = getattr(page, "form_actions", None) or []
        for action in actions:
            if not action:
                continue
            normalized = action.strip().lower()
            if normalized.startswith("http://"):
                if "insecure_form_action" not in page.issues:
                    page.issues.append("insecure_form_action")
                break


def export_insecure_forms_csv(report: CrawlReport, path) -> None:
    import csv
    from pathlib import Path

    out = Path(path)
    fields = ["url", "form_action", "indexability"]
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for url, page in sorted(report.pages.items()):
            if "insecure_form_action" not in page.issues:
                continue
            actions = getattr(page, "form_actions", None) or []
            insecure = [a for a in actions if (a or "").strip().lower().startswith("http://")]
            w.writerow(
                {
                    "url": url,
                    "form_action": " | ".join(insecure[:5]),
                    "indexability": page.indexability,
                }
            )
