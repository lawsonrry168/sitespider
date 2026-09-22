"""
LanguageTool HTTP API 文法稽核（預設公開端點或自架 languagetool-server）。
"""

from __future__ import annotations

import csv
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport, PageResult

_DEFAULT_API = "https://api.languagetool.org/v2/check"


def _page_text(page: PageResult, *, max_chars: int = 4000) -> str:
    parts = [
        page.title or "",
        page.meta_description or "",
        " ".join(page.h1 or []),
        " ".join(page.h2 or []),
    ]
    text = "\n".join(p.strip() for p in parts if p and p.strip())
    return text[:max_chars]


def _check_text(api_url: str, text: str, *, language: str = "auto") -> list[dict[str, Any]]:
    if not text.strip():
        return []
    data = urllib.parse.urlencode(
        {
            "text": text,
            "language": language,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        api_url.rstrip("/"),
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return []
    matches = payload.get("matches") or []
    rows: list[dict[str, Any]] = []
    for m in matches:
        if not isinstance(m, dict):
            continue
        offset = int(m.get("offset") or 0)
        length = int(m.get("length") or 0)
        snippet = text[max(0, offset - 20) : offset + length + 20]
        rows.append(
            {
                "rule_id": str((m.get("rule") or {}).get("id") or ""),
                "message": str(m.get("message") or ""),
                "offset": offset,
                "length": length,
                "snippet": snippet.strip(),
            }
        )
    return rows


def run_grammar_audit(
    report: CrawlReport,
    api_url: str = _DEFAULT_API,
    *,
    max_pages: int = 50,
) -> None:
    """稽核 report 內 HTML 200 頁，寫入 report.grammar_issues 並標記 grammar_error。"""
    report.grammar_issues = []
    checked = 0
    for url, page in sorted(report.pages.items()):
        if page.status != 200:
            continue
        if checked >= max_pages:
            break
        text = _page_text(page)
        if not text.strip():
            continue
        matches = _check_text(api_url, text)
        checked += 1
        if not matches:
            continue
        if "grammar_error" not in page.issues:
            page.issues.append("grammar_error")
        for m in matches:
            report.grammar_issues.append(
                {
                    "url": url,
                    "rule_id": m.get("rule_id", ""),
                    "message": m.get("message", ""),
                    "offset": m.get("offset", 0),
                    "length": m.get("length", 0),
                    "snippet": m.get("snippet", ""),
                }
            )


def export_grammar_csv(report: CrawlReport, path: Path) -> None:
    rows = getattr(report, "grammar_issues", None) or []
    fields = ["url", "rule_id", "message", "offset", "length", "snippet"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})
