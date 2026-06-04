"""爬取完成通知：Slack、Webhook、Email。"""

from __future__ import annotations

import json
import os
import smtplib
from email.mime.text import MIMEText
from typing import Any
from urllib.request import Request, urlopen


def _post_json(url: str, payload: dict[str, Any], headers: dict | None = None) -> bool:
    body = json.dumps(payload).encode("utf-8")
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    req = Request(url, data=body, headers=hdrs, method="POST")
    try:
        with urlopen(req, timeout=15) as resp:
            return 200 <= resp.status < 300
    except OSError:
        return False


def notify_slack(webhook_url: str, text: str) -> bool:
    return _post_json(webhook_url, {"text": text})


def notify_webhook(url: str, payload: dict[str, Any]) -> bool:
    return _post_json(url, payload)


def notify_email(
    to_addrs: list[str],
    subject: str,
    body: str,
    *,
    smtp_host: str | None = None,
    smtp_port: int | None = None,
    smtp_user: str | None = None,
    smtp_pass: str | None = None,
    from_addr: str | None = None,
) -> bool:
    host = smtp_host or os.environ.get("SITESPIDER_SMTP_HOST", "")
    if not host or not to_addrs:
        return False
    port = smtp_port or int(os.environ.get("SITESPIDER_SMTP_PORT", "587"))
    user = smtp_user or os.environ.get("SITESPIDER_SMTP_USER", "")
    password = smtp_pass or os.environ.get("SITESPIDER_SMTP_PASS", "")
    sender = from_addr or os.environ.get("SITESPIDER_SMTP_FROM", user or "sitespider@localhost")
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(to_addrs)
    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if user:
                smtp.starttls()
                smtp.login(user, password)
            smtp.sendmail(sender, to_addrs, msg.as_string())
        return True
    except OSError:
        return False


def notify_crawl_complete(
    *,
    tenant_id: str,
    job_id: str,
    site_url: str,
    pages: int,
    report_dir: str,
    package_url: str = "",
    notify: dict[str, Any] | None = None,
) -> dict[str, bool]:
    """依 notify 設定發送；回傳各通道是否成功。"""
    n = notify or {}
    text = (
        f"SiteSpider 爬取完成\n"
        f"租戶：{tenant_id}\n"
        f"Job：{job_id}\n"
        f"網站：{site_url}\n"
        f"頁數：{pages}\n"
        f"報告：{report_dir}\n"
    )
    if package_url:
        text += f"ZIP：{package_url}\n"
    results: dict[str, bool] = {}
    if n.get("slack_webhook"):
        results["slack"] = notify_slack(str(n["slack_webhook"]), text)
    if n.get("webhook_url"):
        results["webhook"] = notify_webhook(
            str(n["webhook_url"]),
            {
                "event": "crawl.complete",
                "tenant_id": tenant_id,
                "job_id": job_id,
                "pages": pages,
                "report_dir": report_dir,
                "package_url": package_url,
            },
        )
    emails = n.get("email_to") or []
    if isinstance(emails, str):
        emails = [e.strip() for e in emails.split(",") if e.strip()]
    if emails:
        results["email"] = notify_email(
            list(emails),
            f"SiteSpider 完成 — {site_url}",
            text,
        )
    return results
