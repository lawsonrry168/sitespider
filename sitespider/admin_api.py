"""管理後台 API（租戶、用量、API Key）。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sitespider.api_keys import issue_tenant_key, list_tenant_keys, merged_key_map
from sitespider.billing_stripe import load_tenants, set_tenant_plan
from sitespider.plans import PLANS, default_local_plan_id, get_plan, plans_public_json
from sitespider.usage import add_ai_polish_bonus, tenant_usage, usage_limits_json


def admin_key_configured() -> bool:
    return bool(os.environ.get("SITESPIDER_ADMIN_KEY", "").strip())


def verify_admin(header: str | None) -> bool:
    expected = os.environ.get("SITESPIDER_ADMIN_KEY", "").strip()
    if not expected:
        return True  # 未設定時僅限本機開發
    if not header or not header.lower().startswith("bearer "):
        return False
    return header.split(" ", 1)[1].strip() == expected


def list_tenants_dashboard(base: Path | None = None) -> dict[str, Any]:
    tenants_db = load_tenants(base)
    keys = list_tenant_keys(base)
    all_ids = sorted(set(tenants_db.keys()) | set(keys.keys()))
    rows: list[dict[str, Any]] = []
    for tid in all_ids:
        rec = tenants_db.get(tid) or {}
        plan_id = rec.get("plan_id", default_local_plan_id())
        plan = get_plan(plan_id)
        u = tenant_usage(tid, base)
        lim = usage_limits_json(plan, u)
        rows.append(
            {
                "tenant_id": tid,
                "plan_id": plan_id,
                "plan_name": plan.name,
                "usage": u,
                "limits": lim,
                "stripe_customer": rec.get("stripe_customer", ""),
                "email": rec.get("email", ""),
                "api_key_hints": keys.get(tid, []),
            }
        )
    return {"tenants": rows, "total": len(rows), "plans": plans_public_json()}


def rotate_tenant_api_key(tenant_id: str, base: Path | None = None) -> dict[str, str]:
    plan_id = (load_tenants(base).get(tenant_id) or {}).get("plan_id", default_local_plan_id())
    token = issue_tenant_key(tenant_id, plan_id, base=base)
    return {"tenant_id": tenant_id, "api_key": token, "plan_id": plan_id}


def set_plan(tenant_id: str, plan_id: str, base: Path | None = None) -> dict[str, str]:
    if plan_id not in PLANS:
        raise ValueError(f"unknown plan: {plan_id}")
    set_tenant_plan(tenant_id, plan_id, base=base)
    issue_tenant_key(tenant_id, plan_id, base=base)
    plan = get_plan(plan_id)
    return {"tenant_id": tenant_id, "plan_id": plan_id, "plan_name": plan.name}


def grant_ai_polish_bonus(tenant_id: str, extra: int, base: Path | None = None) -> dict[str, Any]:
    """管理員手動加購 AI 文案次數。"""
    extra = max(0, int(extra))
    if extra <= 0:
        raise ValueError("extra must be positive")
    plan_id = (load_tenants(base).get(tenant_id) or {}).get("plan_id", default_local_plan_id())
    plan = get_plan(plan_id)
    if not plan.allows_ai_bonus_purchase():
        raise ValueError(f"方案 {plan_id} 不含 AI 加購（僅 Pro / Agency 可手動加購）")
    total_bonus = add_ai_polish_bonus(tenant_id, extra, base)
    u = tenant_usage(tenant_id, base)
    lim = usage_limits_json(plan, u)
    return {
        "tenant_id": tenant_id,
        "added": extra,
        "ai_polish_bonus": total_bonus,
        "ai_polishes_used": u["ai_polishes"],
        "ai_polish_limit_effective": lim["ai_polish_limit_effective"],
    }
