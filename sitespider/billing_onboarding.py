"""訂閱開通信與 Stripe Customer Portal。"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from sitespider.notifications import notify_email
from sitespider.plans import get_plan


def public_app_url() -> str:
    """控制台對外網址（郵件與 Portal return_url）。"""
    explicit = os.environ.get("SITESPIDER_PUBLIC_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    host = os.environ.get("SITESPIDER_PUBLIC_HOST", "127.0.0.1:8765").strip()
    scheme = "https" if os.environ.get("SITESPIDER_PUBLIC_HTTPS") else "http"
    return f"{scheme}://{host}"


def build_welcome_email(
    *,
    tenant_id: str,
    plan_id: str,
    api_key: str,
    customer_email: str = "",
) -> tuple[str, str]:
    plan = get_plan(plan_id)
    base = public_app_url()
    subject = f"SiteSpider 訂閱已開通 — {plan.name}（{tenant_id}）"
    body = f"""您好，

感謝訂閱 SiteSpider {plan.name} 方案。

【帳號資訊】
租戶 ID：{tenant_id}
方案：{plan.name}
單次最多 {plan.max_pages_per_crawl} 頁 · 每月 {plan.max_crawls_per_month} 次爬取

【API Key】（請妥善保存，勿公開）
{api_key}

【使用方式】
1. 開啟控制台：{base}/
2. 在「訂閱 / API」貼上 API Key
3. 租戶 ID 填：{tenant_id}
4. 開始爬取並下載交付 ZIP

【管理訂閱】
{base}/pricing 頁面可開啟「管理訂閱」（Stripe Customer Portal）

如有問題請回覆此郵件或聯絡您的顧問窗口。

— SiteSpider
"""
    if customer_email:
        body = f"收件人：{customer_email}\n\n" + body
    return subject, body


def send_welcome_email(
    *,
    tenant_id: str,
    plan_id: str,
    api_key: str,
    to_email: str,
) -> bool:
    if not to_email.strip():
        return False
    subject, body = build_welcome_email(
        tenant_id=tenant_id,
        plan_id=plan_id,
        api_key=api_key,
        customer_email=to_email,
    )
    return notify_email([to_email.strip()], subject, body)


def _stripe_post(path: str, fields: dict[str, str]) -> dict[str, Any]:
    secret = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if not secret:
        return {"error": "STRIPE_SECRET_KEY not configured"}
    body = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.stripe.com/v1/{path.lstrip('/')}",
        data=body,
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"error": str(e)}
    except OSError as e:
        return {"error": str(e)}


def create_portal_session(
    *,
    stripe_customer_id: str,
    return_url: str | None = None,
) -> dict[str, Any]:
    """Stripe Billing Portal — 客戶自行改方案 / 取消 / 更新付款方式。"""
    if not stripe_customer_id:
        return {"error": "missing stripe customer id"}
    ret = return_url or f"{public_app_url()}/"
    data = _stripe_post(
        "billing_portal/sessions",
        {
            "customer": stripe_customer_id,
            "return_url": ret,
        },
    )
    if data.get("error"):
        return {"error": data.get("error")}
    url = data.get("url", "")
    if not url:
        return {"error": data.get("message") or "portal session failed"}
    return {"url": url, "session_id": data.get("id", "")}
