"""
Chrome UX Report (CrUX) API — 來源（origin）層級 Core Web Vitals。
"""

from __future__ import annotations

import csv
import json
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport

_CRUX_ENDPOINT = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"


def _origin_from_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme or "https"
    host = parsed.netloc
    if not host:
        return ""
    return f"{scheme}://{host}"


def _metric_value(record: dict[str, Any], metric: str) -> float | None:
    metrics = (record.get("record") or {}).get("metrics") or {}
    data = metrics.get(metric) or {}
    percentiles = data.get("percentiles") or {}
    if "p75" in percentiles:
        try:
            return float(percentiles["p75"])
        except (TypeError, ValueError):
            return None
    hist = data.get("histogram") or []
    if hist and isinstance(hist[0], dict) and "start" in hist[0]:
        try:
            return float(hist[0]["start"])
        except (TypeError, ValueError):
            return None
    return None


def _fetch_origin_record(origin: str, api_key: str) -> dict[str, Any]:
    qs = urllib.parse.urlencode({"key": api_key})
    url = f"{_CRUX_ENDPOINT}?{qs}"
    body = json.dumps({"origin": origin}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _is_poor_cwv(metrics: dict[str, float | None]) -> bool:
    lcp = metrics.get("largest_contentful_paint")
    inp = metrics.get("interaction_to_next_paint") or metrics.get("experimental_time_to_first_input")
    cls = metrics.get("cumulative_layout_shift")
    poor = False
    if lcp is not None and lcp > 4000:
        poor = True
    if inp is not None and inp > 500:
        poor = True
    if cls is not None and cls > 0.25:
        poor = True
    return poor


def run_crux_audit(
    report: CrawlReport,
    api_key: str,
    *,
    max_origins: int = 5,
) -> None:
    """查詢 CrUX origin 紀錄，寫入 report.crux_metrics 並標記 crux_poor。"""
    if not api_key:
        report.errors.append("CrUX audit skipped: missing api_key")
        return

    origins: list[str] = []
    seen: set[str] = set()
    for url in report.pages:
        origin = _origin_from_url(url)
        if not origin or origin in seen:
            continue
        seen.add(origin)
        origins.append(origin)
        if len(origins) >= max_origins:
            break

    report.crux_metrics = []
    pages_by_origin: dict[str, list[str]] = defaultdict(list)
    for url in report.pages:
        origin = _origin_from_url(url)
        if origin:
            pages_by_origin[origin].append(url)

    for origin in origins:
        row: dict[str, Any] = {"origin": origin, "error": ""}
        try:
            payload = _fetch_origin_record(origin, api_key)
            record = payload.get("record") or payload
            metrics = {
                "largest_contentful_paint": _metric_value({"record": record}, "largest_contentful_paint"),
                "interaction_to_next_paint": _metric_value({"record": record}, "interaction_to_next_paint"),
                "cumulative_layout_shift": _metric_value({"record": record}, "cumulative_layout_shift"),
            }
            row.update(metrics)
            row["poor_cwv"] = _is_poor_cwv(metrics)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            row["error"] = str(exc)[:200]

        report.crux_metrics.append(row)

        for page_url in pages_by_origin.get(origin, []):
            page = report.pages.get(page_url)
            if not page:
                continue
            setattr(page, "crux_lcp", row.get("largest_contentful_paint"))
            setattr(page, "crux_inp", row.get("interaction_to_next_paint"))
            setattr(page, "crux_cls", row.get("cumulative_layout_shift"))
            if row.get("poor_cwv") and "crux_poor" not in page.issues:
                page.issues.append("crux_poor")


def export_crux_csv(report: CrawlReport, path) -> None:
    from pathlib import Path

    out = Path(path)
    rows = getattr(report, "crux_metrics", None) or []
    fields = [
        "origin",
        "largest_contentful_paint",
        "interaction_to_next_paint",
        "cumulative_layout_shift",
        "poor_cwv",
        "error",
    ]
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})
