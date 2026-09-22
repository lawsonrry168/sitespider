"""
反向連結 API（Ahrefs / Moz）— 可注入 fetch 以利測試。
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable
from urllib.parse import urlparse

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport, PageResult

FetchFn = Callable[[str, dict[str, str]], Any]


class BacklinkProvider(ABC):
    name: str = "base"

    def __init__(self, api_key: str, *, fetch: FetchFn | None = None) -> None:
        self.api_key = api_key
        self._fetch = fetch

    @abstractmethod
    def fetch_url_metrics(self, url: str) -> dict[str, float | int]:
        """回傳 backlinks_count, referring_domains, domain_rating（可選）。"""


class AhrefsProvider(BacklinkProvider):
    name = "ahrefs"

    def fetch_url_metrics(self, url: str) -> dict[str, float | int]:
        if self._fetch:
            data = self._fetch(
                "https://api.ahrefs.com/v3/site-explorer/backlinks-stats",
                {"target": url, "mode": "exact"},
            )
        else:
            import requests

            r = requests.get(
                "https://api.ahrefs.com/v3/site-explorer/backlinks-stats",
                headers={"Authorization": f"Bearer {self.api_key}"},
                params={"target": url, "mode": "exact"},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
        metrics = data.get("metrics") or data
        return {
            "backlinks_count": int(metrics.get("backlinks") or metrics.get("backlinks_count") or 0),
            "referring_domains": int(
                metrics.get("refdomains") or metrics.get("referring_domains") or 0
            ),
            "domain_rating": float(metrics.get("domain_rating") or metrics.get("rating") or 0),
        }


class MozProvider(BacklinkProvider):
    name = "moz"

    def fetch_url_metrics(self, url: str) -> dict[str, float | int]:
        if self._fetch:
            data = self._fetch(
                "https://lsapi.seomoz.com/v2/url_metrics",
                {"targets": [url]},
            )
        else:
            import requests

            r = requests.post(
                "https://lsapi.seomoz.com/v2/url_metrics",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps({"targets": [url]}),
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
        row = (data.get("results") or [data])[0] if isinstance(data, dict) else {}
        return {
            "backlinks_count": int(row.get("external_pages_to_page") or row.get("backlinks") or 0),
            "referring_domains": int(
                row.get("root_domains_to_page") or row.get("referring_domains") or 0
            ),
            "domain_rating": float(row.get("domain_authority") or row.get("domain_rating") or 0),
        }


def _provider(name: str, api_key: str, fetch: FetchFn | None) -> BacklinkProvider:
    key = name.lower().strip()
    if key == "ahrefs":
        return AhrefsProvider(api_key, fetch=fetch)
    if key == "moz":
        return MozProvider(api_key, fetch=fetch)
    raise ValueError(f"不支援的 backlink provider: {name}")


def _apply_backlink(page: PageResult, metrics: dict[str, float | int]) -> None:
    page.backlinks_count = int(metrics.get("backlinks_count", 0))
    page.referring_domains = int(metrics.get("referring_domains", 0))
    page.domain_rating = float(metrics.get("domain_rating", 0))


def run_backlink_fetch(
    report: CrawlReport,
    provider: str,
    api_key: str,
    max_urls: int = 200,
    *,
    fetch: FetchFn | None = None,
) -> None:
    """
    對報告內 URL 拉取反向連結指標（最多 max_urls 筆）。
    fetch(url, payload) 可注入 mock 回應。
    """
    try:
        client = _provider(provider, api_key, fetch)
    except ValueError as e:
        report.errors.append(str(e))
        return

    urls = [
        url
        for url, page in sorted(report.pages.items())
        if page.status == 200 and not page.blocked_by_robots
    ][:max_urls]

    for url in urls:
        page = report.pages[url]
        try:
            metrics = client.fetch_url_metrics(url)
            _apply_backlink(page, metrics)
        except Exception as e:
            host = urlparse(url).netloc
            report.errors.append(f"Backlink ({client.name}) {host}: {e}")
