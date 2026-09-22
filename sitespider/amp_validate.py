"""
AMP 頁面驗證 — validator API 或啟發式（rel=amphtml / ⚡ / amp 屬性）。
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport

_AMP_VALIDATOR = "https://amp-validator.appspot.com/v1/tags"
_AMP_HTML_MARKERS = (
    re.compile(r"<html[^>]+(?:\bamp\b|⚡)", re.I),
    re.compile(r"rel\s*=\s*['\"]amphtml['\"]", re.I),
)


def _is_amp_page(page) -> bool:
    if getattr(page, "amp_html_url", None):
        return True
    url = page.url or ""
    if "/amp/" in urlparse(url).path.lower():
        return True
    html = getattr(page, "raw_html", None) or getattr(page, "html", None) or ""
    if html:
        for pat in _AMP_HTML_MARKERS:
            if pat.search(html):
                return True
    return False


def _validate_amp_url(target_url: str) -> tuple[bool, str]:
    qs = urllib.parse.urlencode({"format": "json", "url": target_url})
    req = urllib.request.Request(f"{_AMP_VALIDATOR}?{qs}", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return False, str(exc)[:200]

    status = str(payload.get("status") or "").upper()
    if status == "PASS":
        return True, ""
    errors = payload.get("errors") or []
    if errors and isinstance(errors[0], dict):
        return False, str(errors[0].get("message") or errors[0].get("code") or "invalid")
    return False, status or "invalid"


def audit_amp_pages(report: CrawlReport) -> None:
    """標記 amp_invalid；寫入 report.amp_validation 摘要。"""
    report.amp_validation = []
    for url, page in report.pages.items():
        if page.status != 200 or not _is_amp_page(page):
            continue
        target = page.amp_html_url or url
        ok, detail = _validate_amp_url(target)
        report.amp_validation.append({"url": url, "target": target, "valid": ok, "detail": detail})
        if not ok and "amp_invalid" not in page.issues:
            page.issues.append("amp_invalid")


def export_amp_validation_csv(report: CrawlReport, path) -> None:
    import csv
    from pathlib import Path

    out = Path(path)
    rows = getattr(report, "amp_validation", None) or []
    fields = ["url", "target", "valid", "detail"]
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})
