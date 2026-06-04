"""
Stripe 訂閱 Webhook（自架 SaaS 用）。

設定：
  STRIPE_WEBHOOK_SECRET=whsec_...
  STRIPE_PRICE_STARTER=price_...
  STRIPE_PRICE_PRO=price_...
  STRIPE_PRICE_AGENCY=price_...

Webhook 事件 customer.subscription.updated → 更新租戶方案（寫入 .sitespider/tenants.json）
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Any


PRICE_TO_PLAN = {
    os.environ.get("STRIPE_PRICE_STARTER", ""): "starter",
    os.environ.get("STRIPE_PRICE_PRO", ""): "pro",
    os.environ.get("STRIPE_PRICE_AGENCY", ""): "agency",
}


def tenants_db_path(base: Path | None = None) -> Path:
    root = (base or Path.cwd()).resolve()
    return root / ".sitespider" / "tenants.json"


def load_tenants(base: Path | None = None) -> dict[str, dict]:
    p = tenants_db_path(base)
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_tenants(data: dict, base: Path | None = None) -> None:
    p = tenants_db_path(base)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def set_tenant_plan(
    tenant_id: str,
    plan_id: str,
    *,
    stripe_customer: str = "",
    stripe_subscription: str = "",
    email: str = "",
    base: Path | None = None,
) -> None:
    db = load_tenants(base)
    prev = db.get(tenant_id) or {}
    db[tenant_id] = {
        "plan_id": plan_id,
        "stripe_customer": stripe_customer or prev.get("stripe_customer", ""),
        "stripe_subscription": stripe_subscription or prev.get("stripe_subscription", ""),
        "email": email or prev.get("email", ""),
        "updated_at": time.time(),
    }
    save_tenants(db, base)


def verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    if not secret or not sig_header:
        return False
    parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
    timestamp = parts.get("t", "")
    v1 = parts.get("v1", "")
    if not timestamp or not v1:
        return False
    signed = f"{timestamp}.{payload.decode('utf-8')}"
    expected = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1)


def handle_ai_polish_pack_checkout(
    obj: dict[str, Any], meta: dict[str, Any], base: Path | None = None
) -> str:
    """一次性 Checkout：AI 潤飾加購包。"""
    from sitespider.stripe_checkout import ai_bonus_pack_size
    from sitespider.usage import add_ai_polish_bonus

    tenant_id = str(
        meta.get("tenant_id")
        or obj.get("client_reference_id")
        or obj.get("customer")
        or ""
    ).strip()
    if not tenant_id:
        return "ai_polish_pack checkout but no tenant_id"
    from sitespider.plans import get_plan

    plan_id = str((load_tenants(base).get(tenant_id) or {}).get("plan_id") or "free")
    if not get_plan(plan_id).allows_ai_bonus_purchase():
        return f"ai_polish_pack rejected: plan {plan_id} cannot purchase AI bonus"
    try:
        pack = int(meta.get("pack_size") or ai_bonus_pack_size())
    except (TypeError, ValueError):
        pack = ai_bonus_pack_size()
    pack = max(1, pack)
    total = add_ai_polish_bonus(tenant_id, pack, base)
    return f"tenant {tenant_id} +{pack} AI polish credits (bonus pool {total})"


def handle_checkout_completed(obj: dict[str, Any], base: Path | None = None) -> str:
    """checkout.session.completed → 開通租戶、API Key、寄歡迎信。"""
    from sitespider.api_keys import issue_tenant_key
    from sitespider.billing_onboarding import send_welcome_email

    meta = obj.get("metadata") or {}
    if str(meta.get("purchase_type") or "") == "ai_polish_pack":
        return handle_ai_polish_pack_checkout(obj, meta, base)
    tenant_id = str(
        meta.get("tenant_id")
        or obj.get("client_reference_id")
        or obj.get("customer")
        or ""
    ).strip()
    plan_id = str(meta.get("plan_id") or "pro")
    if not tenant_id:
        return "checkout completed but no tenant_id"
    customer = str(obj.get("customer") or "")
    email = str(obj.get("customer_details", {}).get("email") or obj.get("customer_email") or "")
    set_tenant_plan(
        tenant_id,
        plan_id,
        stripe_customer=customer,
        email=email,
        base=base,
    )
    api_key = issue_tenant_key(tenant_id, plan_id, label=tenant_id, base=base)
    mailed = False
    if email:
        mailed = send_welcome_email(
            tenant_id=tenant_id,
            plan_id=plan_id,
            api_key=api_key,
            to_email=email,
        )
    mail_note = "email sent" if mailed else ("email skipped" if not email else "email failed")
    return (
        f"tenant {tenant_id} activated plan {plan_id}; "
        f"api_key_prefix={api_key[:20]}…; {mail_note}"
    )


def handle_stripe_event(event: dict[str, Any], base: Path | None = None) -> str:
    """處理單一 Stripe event dict，回傳說明文字。"""
    etype = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}
    if etype == "checkout.session.completed":
        return handle_checkout_completed(obj, base)
    if etype in ("customer.subscription.updated", "customer.subscription.created"):
        sub_id = obj.get("id", "")
        customer = obj.get("customer", "")
        items = (obj.get("items") or {}).get("data") or []
        price_id = ""
        if items:
            price_id = ((items[0].get("price") or {}).get("id") or "")
        plan_id = PRICE_TO_PLAN.get(price_id, "pro")
        meta = obj.get("metadata") or {}
        tenant_id = str(meta.get("tenant_id") or meta.get("tenant") or customer)
        set_tenant_plan(
            tenant_id,
            plan_id,
            stripe_customer=str(customer),
            stripe_subscription=str(sub_id),
            base=base,
        )
        return f"tenant {tenant_id} → plan {plan_id}"
    if etype == "customer.subscription.deleted":
        meta = obj.get("metadata") or {}
        tenant_id = str(meta.get("tenant_id") or obj.get("customer", ""))
        set_tenant_plan(tenant_id, "free", base=base)
        return f"tenant {tenant_id} downgraded to free"
    return f"ignored {etype}"


def resolve_tenant_plan(tenant_id: str, base: Path | None = None) -> str | None:
    rec = load_tenants(base).get(tenant_id)
    if not rec:
        return None
    return str(rec.get("plan_id") or "pro")
