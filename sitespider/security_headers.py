"""
HTTP 安全標頭稽核與分數。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport, PageResult

from sitespider.robots import meta_robots_noindex

_ALWAYS_HEADERS = (
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
    "content-security-policy",
)
_HSTS = "strict-transport-security"


def _issue(page: PageResult, code: str) -> None:
    if code not in page.issues:
        page.issues.append(code)


def _header_present(headers: dict[str, str], name: str) -> bool:
    return bool((headers.get(name) or "").strip())


def _expected_headers(page: PageResult) -> tuple[str, ...]:
    names = list(_ALWAYS_HEADERS)
    if page.is_https or (page.url or "").startswith("https://"):
        names.append(_HSTS)
    return tuple(names)


def security_score(page: PageResult) -> int:
    """0–100；每缺一项安全標頭扣分。"""
    headers = {k.lower(): v for k, v in (page.response_headers or {}).items()}
    expected = _expected_headers(page)
    if not expected:
        return 100
    present = sum(1 for h in expected if _header_present(headers, h))
    return max(0, min(100, round(100 * present / len(expected))))


def audit_security_headers(report: CrawlReport) -> None:
    """缺漏安全標頭時標記 missing_security_header。"""
    for page in report.pages.values():
        if page.status >= 400 or page.blocked_by_robots:
            continue
        if meta_robots_noindex(page.meta_robots):
            continue
        headers = {k.lower(): v for k, v in (page.response_headers or {}).items()}
        missing = [h for h in _expected_headers(page) if not _header_present(headers, h)]
        if missing:
            _issue(page, "missing_security_header")
        page.security_score = security_score(page)
