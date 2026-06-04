"""內建示範報告資訊（123deal 煙霧）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEMO_DIR_NAME = "123deal-smoke"
DEMO_LABEL = "123deal.com.hk · 範例報告"
DEMO_SITE_URL = "https://123deal.com.hk/"


def demo_report_dir(base: Path | None = None) -> Path:
    return (base or Path.cwd()).resolve() / "reports" / DEMO_DIR_NAME


def demo_crawl_hint() -> str:
    return (
        "sitespider -c examples/123deal-sitespider.json "
        "--max-pages 12 -o reports/123deal-smoke"
    )


def demo_info_json(base: Path | None = None) -> dict[str, Any]:
    report_dir = demo_report_dir(base)
    cr = report_dir / "crawl-report.json"
    if not cr.is_file():
        return {"available": False, "hint": demo_crawl_hint()}

    out: dict[str, Any] = {
        "available": True,
        "report_base": "/reports/demo/",
        "report_dir": str(report_dir),
        "label": DEMO_LABEL,
        "site_url": DEMO_SITE_URL,
    }

    try:
        summary = json.loads((report_dir / "summary.json").read_text(encoding="utf-8"))
        out["pages"] = summary.get("url_count")
        out["health_score"] = summary.get("health_score")
        out["health_grade"] = summary.get("health_grade_label")
        out["duration_sec"] = summary.get("duration_sec")
    except (OSError, json.JSONDecodeError, TypeError):
        pass

    try:
        crawl = json.loads(cr.read_text(encoding="utf-8"))
        out["site_url"] = crawl.get("site_url") or out["site_url"]
        pages = crawl.get("pages") or {}
        if out.get("pages") is None:
            out["pages"] = len(pages)
    except (OSError, json.JSONDecodeError, TypeError):
        pass

    from sitespider.report_share import find_share_for_report, portal_manifest

    share = find_share_for_report(report_dir, base)
    if share:
        out["portal_path"] = share["share_path"]
        out["portal_expires_at"] = share.get("expires_at")

    from sitespider.delivery_manifest import files_in_report, grouped_files_in_report

    manifest = portal_manifest(report_dir, DEMO_LABEL)
    out["files"] = files_in_report(report_dir) or manifest.get("files") or []
    out["groups"] = grouped_files_in_report(report_dir) or manifest.get("groups") or []
    meta = report_dir / "ai-polish-meta.json"
    out["has_ai"] = meta.is_file() and "page-copy" in meta.read_text(encoding="utf-8", errors="ignore")
    return out
