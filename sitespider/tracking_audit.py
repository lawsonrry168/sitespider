"""
靜態 HTML 追蹤標籤稽核：GTM / GA4 / UA / Facebook Pixel / dataLayer。
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport, PageResult

_GTM = re.compile(r"googletagmanager\.com/gtm\.js\?id=(GTM-[A-Z0-9]+)", re.I)
_GTM_NOSCRIPT = re.compile(r"googletagmanager\.com/ns\.html\?id=(GTM-[A-Z0-9]+)", re.I)
_GA4 = re.compile(r"googletagmanager\.com/gtag/js\?id=(G-[A-Z0-9]+)", re.I)
_GA4_CONFIG = re.compile(r"""gtag\s*\(\s*['"]config['"]\s*,\s*['"](G-[A-Z0-9]+)['"]""", re.I)
_UA = re.compile(r"""gtag\s*\(\s*['"]config['"]\s*,\s*['"](UA-\d+-\d+)['"]""", re.I)
_UA_LEGACY = re.compile(r"google-analytics\.com/(?:analytics|ga)\.js", re.I)
_UA_CREATE = re.compile(r"""['"]create['"]\s*,\s*['"](UA-\d+-\d+)['"]""", re.I)
_FB = re.compile(r"""connect\.facebook\.net/[^'"]+/fbevents\.js""", re.I)
_FB_ID = re.compile(r"""fbq\s*\(\s*['"]init['"]\s*,\s*['"](\d+)['"]""", re.I)
_DATALAYER = re.compile(r"dataLayer\s*=\s*dataLayer\s*\|\|\s*\[\]", re.I)
_DATALAYER_PUSH = re.compile(r"dataLayer\.push\s*\(", re.I)


def audit_html_tracking(html: str) -> dict[str, Any]:
    """掃描 HTML 字串，回傳追蹤 footprint dict。"""
    text = html or ""
    gtm_ids = sorted(set(_GTM.findall(text) + _GTM_NOSCRIPT.findall(text)))
    ga4_ids = sorted(set(_GA4.findall(text) + _GA4_CONFIG.findall(text)))
    ua_ids = sorted(set(_UA.findall(text) + _UA_CREATE.findall(text)))
    fb_ids = sorted(set(_FB_ID.findall(text)))
    has_fb = bool(_FB.search(text) or fb_ids)
    has_datalayer = bool(_DATALAYER.search(text) or _DATALAYER_PUSH.search(text))
    has_ua_legacy = bool(_UA_LEGACY.search(text))

    return {
        "gtm_ids": gtm_ids,
        "ga4_ids": ga4_ids,
        "ua_ids": ua_ids,
        "fb_pixel_ids": fb_ids,
        "has_gtm": bool(gtm_ids),
        "has_ga4": bool(ga4_ids),
        "has_ua": bool(ua_ids) or has_ua_legacy,
        "has_fb_pixel": has_fb,
        "has_datalayer": has_datalayer,
        "has_any_tracking": bool(gtm_ids or ga4_ids or ua_ids or has_fb or has_ua_legacy),
    }


def apply_page_tracking(page: PageResult, footprint: dict[str, Any]) -> None:
    """將 footprint 存到 page.tracking_footprint。"""
    setattr(page, "tracking_footprint", dict(footprint))


def _page_html(page: PageResult) -> str:
    return getattr(page, "raw_html", None) or getattr(page, "html", None) or ""


def scan_report_tracking(report: CrawlReport) -> None:
    """對所有 200 HTML 頁執行 audit_html_tracking。"""
    for page in report.pages.values():
        if page.status != 200:
            continue
        html = _page_html(page)
        if not html:
            continue
        apply_page_tracking(page, audit_html_tracking(html))


def apply_site_tracking_issues(report: CrawlReport) -> None:
    """
    全站追蹤一致性問題：
    - missing_tracking：可索引 200 頁完全無追蹤
    - inconsistent_ga4：站內 GA4 ID 超過一組
    - legacy_ua_only：僅 UA、無 GA4
    """
    ga4_all: set[str] = set()
    ua_all: set[str] = set()
    indexed_pages = 0
    pages_with_tracking = 0

    for url, page in report.pages.items():
        if page.status != 200 or page.indexability != "Indexable":
            continue
        indexed_pages += 1
        fp = getattr(page, "tracking_footprint", None) or {}
        if fp.get("has_any_tracking"):
            pages_with_tracking += 1
        ga4_all.update(fp.get("ga4_ids") or [])
        ua_all.update(fp.get("ua_ids") or [])

        if not fp.get("has_any_tracking"):
            if "missing_tracking" not in page.issues:
                page.issues.append("missing_tracking")
        if fp.get("has_ua") and not fp.get("has_ga4"):
            if "legacy_ua_only" not in page.issues:
                page.issues.append("legacy_ua_only")

    if len(ga4_all) > 1:
        for page in report.pages.values():
            if page.status != 200:
                continue
            fp = getattr(page, "tracking_footprint", None) or {}
            if fp.get("ga4_ids") and "inconsistent_ga4" not in page.issues:
                page.issues.append("inconsistent_ga4")

    report.tracking_summary = {
        "indexed_pages": indexed_pages,
        "pages_with_tracking": pages_with_tracking,
        "ga4_ids": sorted(ga4_all),
        "ua_ids": sorted(ua_all),
        "ga4_id_count": len(ga4_all),
    }


def _locale_key(path: str) -> str:
    parts = [p for p in path.strip("/").split("/") if p]
    if not parts:
        return "/"
    if parts[0].lower() in {"en", "zh-hant", "zh-hk", "zh-tw", "zh-cn"}:
        rest = "/".join(parts[1:]) or "/"
        return rest if rest.startswith("/") else f"/{rest}"
    return path if path.startswith("/") else f"/{path}"


def compute_locale_tracking_comparison(report: CrawlReport) -> list[dict[str, Any]]:
    """
    比對 en / zh-hant 路徑對的追蹤 footprint 差異。
    回傳 list of dict（path_key, en_url, zh_url, diff_fields）。
    """
    by_locale: dict[str, dict[str, tuple[str, dict[str, Any]]]] = defaultdict(dict)
    for url, page in report.pages.items():
        if page.status != 200:
            continue
        parsed = urlparse(url)
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if not parts:
            continue
        locale = parts[0].lower()
        if locale not in {"en", "zh-hant", "zh-hk", "zh-tw"}:
            continue
        norm_locale = "zh-hant" if locale in {"zh-hant", "zh-hk", "zh-tw"} else "en"
        key = _locale_key(parsed.path)
        fp = getattr(page, "tracking_footprint", None) or audit_html_tracking(_page_html(page))
        by_locale[norm_locale][key] = (url, fp)

    rows: list[dict[str, Any]] = []
    en_map = by_locale.get("en", {})
    zh_map = by_locale.get("zh-hant", {})
    for key in sorted(set(en_map) & set(zh_map)):
        en_url, en_fp = en_map[key]
        zh_url, zh_fp = zh_map[key]
        diff_fields: list[str] = []
        for field in ("gtm_ids", "ga4_ids", "ua_ids", "fb_pixel_ids", "has_datalayer"):
            if en_fp.get(field) != zh_fp.get(field):
                diff_fields.append(field)
        rows.append(
            {
                "path_key": key,
                "en_url": en_url,
                "zh_url": zh_url,
                "diff_fields": ";".join(diff_fields),
                "en_ga4": ";".join(en_fp.get("ga4_ids") or []),
                "zh_ga4": ";".join(zh_fp.get("ga4_ids") or []),
            }
        )
    report.locale_tracking_comparison = rows
    return rows


def export_tracking_bundle(report: CrawlReport, out_dir: str | Path) -> list[str]:
    """寫入 tracking.csv、tracking-events.csv、tracking-audit.html。"""
    base = Path(out_dir)
    base.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    page_fields = [
        "url",
        "has_gtm",
        "gtm_ids",
        "has_ga4",
        "ga4_ids",
        "has_ua",
        "ua_ids",
        "has_fb_pixel",
        "fb_pixel_ids",
        "has_datalayer",
        "issues",
    ]
    tracking_csv = base / "tracking.csv"
    with tracking_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=page_fields)
        w.writeheader()
        for url, page in sorted(report.pages.items()):
            fp = getattr(page, "tracking_footprint", None) or {}
            w.writerow(
                {
                    "url": url,
                    "has_gtm": fp.get("has_gtm", False),
                    "gtm_ids": ";".join(fp.get("gtm_ids") or []),
                    "has_ga4": fp.get("has_ga4", False),
                    "ga4_ids": ";".join(fp.get("ga4_ids") or []),
                    "has_ua": fp.get("has_ua", False),
                    "ua_ids": ";".join(fp.get("ua_ids") or []),
                    "has_fb_pixel": fp.get("has_fb_pixel", False),
                    "fb_pixel_ids": ";".join(fp.get("fb_pixel_ids") or []),
                    "has_datalayer": fp.get("has_datalayer", False),
                    "issues": ";".join(
                        i
                        for i in page.issues
                        if i in {"missing_tracking", "inconsistent_ga4", "legacy_ua_only"}
                    ),
                }
            )
    written.append("tracking.csv")

    event_rows: list[dict[str, str]] = []
    for url, page in report.pages.items():
        fp = getattr(page, "tracking_footprint", None) or {}
        for gtm in fp.get("gtm_ids") or []:
            event_rows.append({"url": url, "type": "GTM", "id": gtm})
        for ga4 in fp.get("ga4_ids") or []:
            event_rows.append({"url": url, "type": "GA4", "id": ga4})
        for ua in fp.get("ua_ids") or []:
            event_rows.append({"url": url, "type": "UA", "id": ua})
        for fb in fp.get("fb_pixel_ids") or []:
            event_rows.append({"url": url, "type": "FB_PIXEL", "id": fb})

    events_csv = base / "tracking-events.csv"
    with events_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["url", "type", "id"])
        w.writeheader()
        w.writerows(event_rows)
    written.append("tracking-events.csv")

    summary = getattr(report, "tracking_summary", None) or {}
    locale_rows = getattr(report, "locale_tracking_comparison", None) or []
    html_parts = [
        "<!DOCTYPE html><html lang='zh-Hant'><head><meta charset='utf-8'/>",
        f"<title>Tracking Audit — {escape(report.start_url)}</title>",
        "<style>body{font-family:system-ui;margin:1.5rem} table{border-collapse:collapse;width:100%}",
        "th,td{border:1px solid #ccc;padding:6px;text-align:left}</style></head><body>",
        f"<h1>Tracking Audit</h1><p>{len(report.pages)} pages</p>",
        f"<pre>{escape(json.dumps(summary, ensure_ascii=False, indent=2))}</pre>",
    ]
    if locale_rows:
        html_parts.append("<h2>Locale comparison (en vs zh-hant)</h2><table><tr>")
        for col in ("path_key", "en_url", "zh_url", "diff_fields", "en_ga4", "zh_ga4"):
            html_parts.append(f"<th>{escape(col)}</th>")
        html_parts.append("</tr>")
        for row in locale_rows:
            html_parts.append("<tr>")
            for col in ("path_key", "en_url", "zh_url", "diff_fields", "en_ga4", "zh_ga4"):
                html_parts.append(f"<td>{escape(str(row.get(col, '')))}</td>")
            html_parts.append("</tr>")
        html_parts.append("</table>")
    html_parts.append("</body></html>")
    audit_html = base / "tracking-audit.html"
    audit_html.write_text("".join(html_parts), encoding="utf-8")
    written.append("tracking-audit.html")
    return written
