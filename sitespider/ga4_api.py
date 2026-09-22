"""
Google Analytics 4 Data API — 合併流量指標至爬取報告（可選依賴）。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport, PageResult

_DATE_RANGE = tuple[str, str]


def ga4_available() -> bool:
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient  # noqa: F401

        return True
    except ImportError:
        return False


def _issue(page: PageResult, code: str) -> None:
    if code not in page.issues:
        page.issues.append(code)


def _normalize_path(url: str) -> str:
    path = urlparse(url).path or "/"
    if not path.startswith("/"):
        path = "/" + path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return path


def _build_client(credentials_path: str | Path):
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.oauth2 import service_account

    path = Path(credentials_path)
    if path.is_file():
        creds = service_account.Credentials.from_service_account_file(str(path))
        return BetaAnalyticsDataClient(credentials=creds)
    return BetaAnalyticsDataClient()


def _fetch_metrics(
    property_id: str,
    credentials_path: str,
    date_range: _DATE_RANGE,
) -> dict[str, dict[str, float]]:
    from google.analytics.data_v1beta.types import (
        DateRange,
        Dimension,
        Metric,
        RunReportRequest,
    )

    client = _build_client(credentials_path)
    prop = property_id if property_id.startswith("properties/") else f"properties/{property_id}"
    request = RunReportRequest(
        property=prop,
        date_ranges=[DateRange(start_date=date_range[0], end_date=date_range[1])],
        dimensions=[Dimension(name="pagePath")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
            Metric(name="bounceRate"),
        ],
        limit=100_000,
    )
    response = client.run_report(request)
    out: dict[str, dict[str, float]] = {}
    for row in response.rows:
        path = row.dimension_values[0].value or "/"
        sessions = float(row.metric_values[0].value or 0)
        pageviews = float(row.metric_values[1].value or 0)
        bounce = float(row.metric_values[2].value or 0)
        out[path] = {
            "sessions": sessions,
            "pageviews": pageviews,
            "bounce_rate": bounce,
        }
    return out


def _apply_metrics(page: PageResult, metrics: dict[str, float]) -> None:
    page.ga4_sessions = int(metrics.get("sessions", 0))
    page.ga4_pageviews = int(metrics.get("pageviews", 0))
    page.ga4_bounce_rate = round(float(metrics.get("bounce_rate", 0.0)), 4)
    if page.ga4_sessions == 0:
        _issue(page, "zero_traffic_page")


def run_ga4_merge(
    report: CrawlReport,
    property_id: str,
    credentials_path: str,
    date_range: _DATE_RANGE = ("30daysAgo", "today"),
) -> None:
    """
    以 GA4 pagePath 合併 sessions / pageviews / bounceRate。
    缺少 google-analytics-data 時寫入 report.errors，不拋出。
    """
    if not ga4_available():
        report.errors.append(
            'GA4 Data API：請安裝 pip install "google-analytics-data" google-auth'
        )
        return
    try:
        by_path = _fetch_metrics(property_id, credentials_path, date_range)
    except Exception as e:
        report.errors.append(f"GA4 Data API：{e}")
        return

    for url, page in report.pages.items():
        if page.status != 200:
            continue
        path = _normalize_path(url)
        metrics = by_path.get(path)
        if metrics is None and path.endswith("/"):
            metrics = by_path.get(path.rstrip("/"))
        if metrics is None and not path.endswith("/"):
            metrics = by_path.get(path + "/")
        if metrics:
            _apply_metrics(page, metrics)
