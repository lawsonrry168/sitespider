"""可選 Scrapling 後端（難站／stealth）；未安裝時優雅降級。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExternalFetchResult:
    status: int
    final_url: str
    html: str
    error: str | None = None


def scrapling_available() -> bool:
    try:
        from scrapling.fetchers import Fetcher  # noqa: F401

        return True
    except ImportError:
        return False


def fetch_html(
    url: str,
    *,
    stealth: bool = False,
    timeout: float = 30.0,
) -> ExternalFetchResult:
    """以 Scrapling 抓取 HTML；未安裝則回傳 error。"""
    if not scrapling_available():
        return ExternalFetchResult(
            status=0,
            final_url=url,
            html="",
            error="scrapling not installed (pip install 'sitespider[scrapling]')",
        )
    try:
        if stealth:
            from scrapling.fetchers import StealthyFetcher

            page = StealthyFetcher.fetch(url, headless=True, network_idle=True)
        else:
            from scrapling.fetchers import Fetcher

            page = Fetcher.get(url, stealthy_headers=True, timeout=int(timeout))
        html = ""
        for attr in ("html_content", "html", "text", "body"):
            val = getattr(page, attr, None)
            if val:
                html = str(val)
                break
        if not html:
            html = str(page)
        final = getattr(page, "url", None) or url
        return ExternalFetchResult(status=200, final_url=final, html=html or "")
    except Exception as e:
        return ExternalFetchResult(status=0, final_url=url, html="", error=str(e))
