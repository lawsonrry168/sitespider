"""
Playwright + axe-core 無障礙稽核（從 CDN 注入 axe，執行 axe.run()）。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport

AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"


def _violation_row(url: str, v: dict[str, Any]) -> dict[str, Any]:
    nodes = v.get("nodes") or []
    return {
        "url": url,
        "id": str(v.get("id") or ""),
        "impact": str(v.get("impact") or ""),
        "help": str(v.get("help") or v.get("description") or ""),
        "nodes_count": len(nodes),
    }


def run_a11y_on_page(page_obj, url: str) -> list[dict[str, Any]]:
    """
    在 Playwright Page 上注入 axe-core 並回傳 violation 列（dict 列表）。
    page_obj: playwright.sync_api.Page
    """
    page_obj.add_script_tag(url=AXE_CDN)
    page_obj.wait_for_function("typeof axe !== 'undefined'", timeout=15_000)
    raw = page_obj.evaluate(
        """async () => {
            const results = await axe.run(document, { resultTypes: ['violations'] });
            return results.violations || [];
        }"""
    )
    violations: list[dict[str, Any]] = []
    for item in raw or []:
        if isinstance(item, dict):
            violations.append(_violation_row(url, item))
    return violations


def apply_a11y_results(
    report: CrawlReport,
    url: str,
    violations: list[dict[str, Any]],
) -> None:
    """寫入 report.a11y_violations 並在頁面標記 a11y_violation。"""
    if not hasattr(report, "a11y_violations") or report.a11y_violations is None:
        report.a11y_violations = []
    report.a11y_violations.extend(violations)

    page = report.pages.get(url)
    if not page:
        return
    if violations and "a11y_violation" not in page.issues:
        page.issues.append("a11y_violation")


def export_a11y_csv(report: CrawlReport, path: Path) -> None:
    rows = list(getattr(report, "a11y_violations", None) or [])
    fields = ["url", "id", "impact", "help", "nodes_count"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def export_a11y_json(report: CrawlReport, path: Path) -> None:
    rows = getattr(report, "a11y_violations", None) or []
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def audit_accessibility(report: CrawlReport) -> None:
    """Violations 已在 Playwright 渲染時收集；此處僅在已有資料時略過。"""
    if getattr(report, "a11y_violations", None):
        return
