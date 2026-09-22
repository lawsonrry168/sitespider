"""
Google Sheets 匯出（需 google-api-python-client + 憑證）。

失敗時寫入 report.errors，不拋出例外。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport


def _google_api_available() -> bool:
    try:
        from googleapiclient.discovery import build  # noqa: F401

        return True
    except ImportError:
        return False


def _build_service(credentials_path: str | None):
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    if credentials_path:
        creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    else:
        import os

        default = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        if not default:
            raise FileNotFoundError("缺少 credentials_path 或 GOOGLE_APPLICATION_CREDENTIALS")
        creds = Credentials.from_service_account_file(default, scopes=scopes)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _collect_issue_rows(report: CrawlReport) -> list[list[Any]]:
    header = ["url", "status", "issue", "title", "indexability"]
    rows: list[list[Any]] = [header]
    for url, page in sorted(report.pages.items()):
        if not page.issues:
            continue
        for issue in page.issues:
            rows.append([url, page.status, issue, page.title or "", page.indexability])
    return rows


def _collect_summary_rows(report: CrawlReport) -> list[list[Any]]:
    from collections import Counter

    issue_counts = Counter()
    for page in report.pages.values():
        for issue in page.issues:
            issue_counts[issue] += 1
    rows: list[list[Any]] = [
        ["metric", "value"],
        ["start_url", report.start_url],
        ["page_count", len(report.pages)],
        ["pages_with_issues", sum(1 for p in report.pages.values() if p.issues)],
        ["error_count", len(report.errors or [])],
    ]
    for issue, count in issue_counts.most_common():
        rows.append([f"issue:{issue}", count])
    return rows


def export_to_sheets(
    report: CrawlReport,
    spreadsheet_id: str,
    credentials_path: str | None = None,
) -> None:
    """匯出 Issues 與 Internal Summary 兩個工作表。"""
    if not spreadsheet_id:
        report.errors.append("Sheets export skipped: missing spreadsheet_id")
        return
    if not _google_api_available():
        report.errors.append(
            "Sheets export skipped: install google-api-python-client and google-auth"
        )
        return
    try:
        service = _build_service(credentials_path)
        sheets = service.spreadsheets()
        body = {
            "valueInputOption": "RAW",
            "data": [
                {"range": "Issues!A1", "values": _collect_issue_rows(report)},
                {"range": "Summary!A1", "values": _collect_summary_rows(report)},
            ],
        }
        sheets.values().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
    except Exception as exc:
        report.errors.append(f"Sheets export failed: {exc}")
