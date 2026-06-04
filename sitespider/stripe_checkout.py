"""Stripe Checkout Session（訂閱制收款）。"""

from __future__ import annotations

import os
import urllib.parse
import urllib.request
from typing import Any

from sitespider.plans import PLANS

PLAN_TO_PRICE = {
    "starter": os.environ.get("STRIPE_PRICE_STARTER", ""),
    "pro": os.environ.get("STRIPE_PRICE_PRO", ""),
    "agency": os.environ.get("STRIPE_PRICE_AGENCY", ""),
}


def ai_bonus_pack_size() -> int:
    try:
        return max(1, int(os.environ.get("STRIPE_AI_BONUS_PACK_SIZE", "10")))
    except ValueError:
        return 10


def ai_bonus_checkout_configured() -> bool:
    return bool(
        stripe_configured()
        and os.environ.get("STRIPE_PRICE_AI_BONUS", "").strip()
    )


def stripe_configured() -> bool:
    return bool(os.environ.get("STRIPE_SECRET_KEY", "").strip())


def create_checkout_session(
    *,
    plan_id: str,
    tenant_id: str,
    success_url: str,
    cancel_url: str,
    customer_email: str = "",
) -> dict[str, Any]:
    """
    建立 Stripe Checkout（subscription mode）。
    回傳 {"url": "...", "session_id": "..."} 或 {"error": "..."}
    """
    secret = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    price_id = PLAN_TO_PRICE.get(plan_id, "")
    if not secret:
        return {"error": "STRIPE_SECRET_KEY not configured"}
    if plan_id not in PLANS:
        return {"error": f"unknown plan: {plan_id}"}
    if plan_id == "free":
        return {"error": "Free 方案無需付款，請直接使用控制台"}
    if not price_id:
        return {"error": f"STRIPE_PRICE for {plan_id} not configured"}

    fields = {
        "mode": "subscription",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": tenant_id,
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "subscription_data[metadata][tenant_id]": tenant_id,
        "subscription_data[metadata][plan_id]": plan_id,
        "metadata[tenant_id]": tenant_id,
        "metadata[plan_id]": plan_id,
    }
    if customer_email:
        fields["customer_email"] = customer_email

    body = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        "https://api.stripe.com/v1/checkout/sessions",
        data=body,
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            import json

            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err = e.read().decode("utf-8")
        except OSError:
            err = str(e)
        return {"error": err}
    except OSError as e:
        return {"error": str(e)}

    return {
        "url": data.get("url", ""),
        "session_id": data.get("id", ""),
        "plan_id": plan_id,
        "tenant_id": tenant_id,
    }


def create_ai_bonus_checkout_session(
    *,
    tenant_id: str,
    success_url: str,
    cancel_url: str,
    customer_email: str = "",
    pack_size: int | None = None,
) -> dict[str, Any]:
    """Stripe Checkout 一次性付款：AI 潤飾加購包。"""
    secret = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    price_id = os.environ.get("STRIPE_PRICE_AI_BONUS", "").strip()
    pack = pack_size if pack_size is not None else ai_bonus_pack_size()
    if not secret:
        return {"error": "STRIPE_SECRET_KEY not configured"}
    if not price_id:
        return {"error": "STRIPE_PRICE_AI_BONUS not configured"}
    if not tenant_id.strip():
        return {"error": "tenant_id required"}

    fields = {
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": tenant_id,
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1",
        "metadata[tenant_id]": tenant_id,
        "metadata[purchase_type]": "ai_polish_pack",
        "metadata[pack_size]": str(pack),
    }
    if customer_email:
        fields["customer_email"] = customer_email

    body = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        "https://api.stripe.com/v1/checkout/sessions",
        data=body,
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            import json

            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err = e.read().decode("utf-8")
        except OSError:
            err = str(e)
        return {"error": err}
    except OSError as e:
        return {"error": str(e)}

    return {
        "url": data.get("url", ""),
        "session_id": data.get("id", ""),
        "tenant_id": tenant_id,
        "pack_size": pack,
        "purchase_type": "ai_polish_pack",
    }
