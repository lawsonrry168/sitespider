"""
SERP 排名查詢（SerpAPI）— 需環境變數 SERPAPI_KEY 與 Pro+ 方案。
"""

from __future__ import annotations

import csv
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote_plus, urlparse

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport


def serpapi_available() -> bool:
    return bool(os.environ.get("SERPAPI_KEY", "").strip())


def _domain_match(result_url: str, site_host: str) -> str:
    try:
        host = urlparse(result_url).netloc.lower().replace("www.", "")
        target = site_host.lower().replace("www.", "")
        if host == target:
            return "match"
        if host.endswith("." + target) or target.endswith("." + host):
            return "partial"
    except Exception:
        pass
    return "no"


def _fetch_serp(query: str, *, gl: str = "hk", hl: str = "zh-tw") -> dict | None:
    key = os.environ.get("SERPAPI_KEY", "").strip()
    if not key:
        return None
    import urllib.request

    url = (
        "https://serpapi.com/search.json?"
        f"q={quote_plus(query)}&engine=google&api_key={quote_plus(key)}"
        f"&gl={gl}&hl={hl}&num=20"
    )
    try:
        with urllib.request.urlopen(url, timeout=25) as resp:
            import json

            return json.loads(resp.read().decode("utf-8"))
    except OSError:
        return None


def collect_serp_queries(report: CrawlReport, *, max_queries: int = 15) -> list[tuple[str, str]]:
    """(url, query) 以 title 或 path 為查詢詞。"""
    from sitespider.link_metrics import compute_page_link_stats

    stats = compute_page_link_stats(report)
    ranked = sorted(
        report.pages.keys(),
        key=lambda u: stats.get(u).link_score if stats.get(u) else 0,
        reverse=True,
    )
    out: list[tuple[str, str]] = []
    site_host = urlparse(report.start_url).netloc
    for url in ranked:
        if len(out) >= max_queries:
            break
        page = report.pages.get(url)
        if not page or page.status != 200:
            continue
        q = (page.title or "").strip()
        if not q or len(q) < 4:
            path = urlparse(url).path.strip("/").replace("-", " ")
            q = path[:60]
        if not q:
            continue
        out.append((url, q[:80]))
    return out


def export_serp_rank_csv(
    report: CrawlReport,
    path: Path,
    *,
    max_queries: int = 15,
    delay_sec: float = 1.2,
) -> int:
    """回傳實際 API 查詢次數。"""
    if not serpapi_available():
        path.write_text(
            "Address,Query,Position,Result URL,Match,Featured Snippet\n",
            encoding="utf-8-sig",
        )
        return 0

    site_host = urlparse(report.start_url).netloc
    rows: list[dict[str, str]] = []
    queries = 0
    for url, query in collect_serp_queries(report, max_queries=max_queries):
        data = _fetch_serp(query)
        queries += 1
        if delay_sec > 0:
            time.sleep(delay_sec)
        if not data:
            rows.append(
                {
                    "Address": url,
                    "Query": query,
                    "Position": "",
                    "Result URL": "",
                    "Match": "api_error",
                    "Featured Snippet": "",
                }
            )
            continue
        organic = data.get("organic_results") or []
        position = ""
        result_url = ""
        match = "not_in_top20"
        for i, item in enumerate(organic[:20], start=1):
            link = str(item.get("link") or "")
            if _domain_match(link, site_host) in ("match", "partial"):
                position = str(i)
                result_url = link
                match = _domain_match(link, site_host)
                break
        rows.append(
            {
                "Address": url,
                "Query": query,
                "Position": position,
                "Result URL": result_url,
                "Match": match,
                "Featured Snippet": "yes" if data.get("answer_box") else "",
            }
        )

    fields = ["Address", "Query", "Position", "Result URL", "Match", "Featured Snippet"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return queries
