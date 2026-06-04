"""
Google Search Console URL Inspection API — Rich Results 驗證。

憑證（二擇一）：
- 服務帳戶 JSON：GOOGLE_APPLICATION_CREDENTIALS / GSC_CREDENTIALS_JSON
- OAuth 用戶端 JSON（installed / web）：GSC_OAUTH_CLIENT_JSON（首次會開瀏覽器授權）

非 Gemini / AI Studio API Key。
"""

from __future__ import annotations

import csv
import json
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport

from sitespider.robots import meta_robots_noindex

_SCOPES = ("https://www.googleapis.com/auth/webmasters.readonly",)


def gsc_available() -> bool:
    try:
        import googleapiclient.discovery  # noqa: F401
        import google.auth  # noqa: F401

        return True
    except ImportError:
        return False


def _credentials_path() -> Path | None:
    for key in (
        "GSC_OAUTH_CLIENT_JSON",
        "GSC_CREDENTIALS_JSON",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ):
        raw = os.environ.get(key, "").strip()
        if raw and Path(raw).is_file():
            return Path(raw)
    return None


def _is_oauth_client_secrets(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and ("installed" in data or "web" in data)


def _oauth_token_path() -> Path:
    raw = os.environ.get("GSC_OAUTH_TOKEN_PATH", "").strip()
    if raw:
        return Path(raw)
    return Path.home() / ".config" / "sitespider" / "gsc-oauth-token.json"


def _load_oauth_credentials(client_secrets: Path):
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError as e:
        raise RuntimeError(
            'OAuth 需要：pip install "sitespider[gsc]"（含 google-auth-oauthlib）'
        ) from e

    token_path = _oauth_token_path()
    creds = None
    if token_path.is_file():
        creds = Credentials.from_authorized_user_file(str(token_path), list(_SCOPES))
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        import sys

        print(
            "\n[GSC] 即將開啟瀏覽器，請用具 Search Console 權限的 Google 帳號登入並允許存取…\n",
            file=sys.stderr,
        )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secrets), list(_SCOPES)
        )
        creds = flow.run_local_server(port=0, open_browser=True)
        print(f"[GSC] 授權完成，token 已儲存：{token_path}\n", file=sys.stderr)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def _build_service():
    if not gsc_available():
        raise RuntimeError(
            '未安裝 GSC 依賴：pip install "sitespider[gsc]"'
        )
    from googleapiclient.discovery import build

    path = _credentials_path()
    if path:
        if _is_oauth_client_secrets(path):
            creds = _load_oauth_credentials(path)
        else:
            from google.oauth2 import service_account

            creds = service_account.Credentials.from_service_account_file(
                str(path),
                scopes=list(_SCOPES),
            )
    else:
        import google.auth

        creds, _ = google.auth.default(scopes=list(_SCOPES))
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def normalize_gsc_site_url(start_url: str, configured: str | None) -> str:
    """URL-prefix 屬性須含尾隨 /。"""
    if configured:
        s = configured.strip()
        if s.startswith("sc-domain:"):
            return s
        return s if s.endswith("/") else s + "/"
    p = urlparse(start_url)
    return f"{p.scheme}://{p.netloc}/"


def _parse_inspection_response(data: dict[str, Any]) -> dict[str, str]:
    result = data.get("inspectionResult") or {}
    rr = result.get("richResultsResult") or {}
    verdict = str(rr.get("verdict") or "")
    types: list[str] = []
    issues: list[str] = []
    for group in rr.get("detectedItems") or []:
        rt = group.get("richResultType") or ""
        if rt:
            types.append(str(rt))
        for item in group.get("items") or []:
            for iss in item.get("issues") or []:
                msg = iss.get("issueMessage") or ""
                sev = iss.get("severity") or ""
                if msg:
                    issues.append(f"{sev}:{msg}" if sev else msg)
    return {
        "GSC Verdict": verdict,
        "GSC Rich Types": "; ".join(types),
        "GSC Issues": " | ".join(issues[:8]),
        "GSC Status": "OK" if verdict in ("PASS", "NEUTRAL") else ("Error" if verdict else "No data"),
    }


def inspect_url(
    service: Any,
    *,
    site_url: str,
    inspection_url: str,
    language_code: str = "zh-TW",
) -> dict[str, str]:
    body = {
        "inspectionUrl": inspection_url,
        "siteUrl": site_url,
        "languageCode": language_code,
    }
    try:
        resp = service.urlInspection().index().inspect(body=body).execute()
        row = _parse_inspection_response(resp)
        row["GSC Error"] = ""
        return row
    except Exception as e:
        return {
            "GSC Verdict": "",
            "GSC Rich Types": "",
            "GSC Issues": "",
            "GSC Status": "API Error",
            "GSC Error": str(e)[:200],
        }


def select_urls_for_inspection(report: CrawlReport, *, limit: int) -> list[str]:
    from sitespider.link_metrics import compute_page_link_stats

    stats = compute_page_link_stats(report)
    candidates: list[tuple[int, str]] = []
    for url, page in report.pages.items():
        if page.status != 200 or page.blocked_by_robots:
            continue
        if meta_robots_noindex(page.meta_robots):
            continue
        score = stats.get(url).link_score if stats.get(url) else 0
        bonus = 10 if page.has_json_ld else 0
        candidates.append((bonus + int(score * 100), url))
    candidates.sort(reverse=True)
    return [u for _, u in candidates[:limit]]


def run_gsc_rich_inspections(
    report: CrawlReport,
    *,
    site_url: str,
    max_urls: int,
    delay_sec: float = 1.0,
) -> dict[str, dict[str, str]]:
    """呼叫 GSC API，結果寫入 report.gsc_rich_inspections。"""
    if max_urls <= 0:
        return {}
    service = _build_service()
    gsc_site = normalize_gsc_site_url(report.start_url, site_url)
    urls = select_urls_for_inspection(report, limit=max_urls)
    out: dict[str, dict[str, str]] = {}
    for i, url in enumerate(urls):
        out[url] = inspect_url(service, site_url=gsc_site, inspection_url=url)
        if i + 1 < len(urls) and delay_sec > 0:
            time.sleep(delay_sec)
    report.gsc_rich_inspections = out
    return out


def export_gsc_rich_results_csv(report: CrawlReport, path: Path) -> None:
    from sitespider.rich_results import evaluate_rich_results

    fields = [
        "Address",
        "Status",
        "JSON-LD Types",
        "Rich Result Status",
        "GSC Status",
        "GSC Verdict",
        "GSC Rich Types",
        "GSC Issues",
        "GSC Error",
        "Notes",
    ]
    rows: list[dict[str, str]] = []
    gsc = report.gsc_rich_inspections or {}
    for page in sorted(report.pages.values(), key=lambda x: x.url):
        base = evaluate_rich_results(page)
        merged = {k: base.get(k, "") for k in fields}
        if page.url in gsc:
            merged.update(gsc[page.url])
        elif gsc:
            merged["GSC Status"] = "Not inspected"
        rows.append({f: str(merged.get(f, "")) for f in fields})

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
