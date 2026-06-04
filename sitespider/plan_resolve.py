"""Resolve effective subscription plan (anti-tamper)."""

from __future__ import annotations

import os
from pathlib import Path

from sitespider.plans import PLANS, get_plan


def api_keys_configured() -> bool:
    from sitespider.api_keys import merged_key_map

    return bool(merged_key_map())


def strict_plan_enforcement(base: Path | None = None) -> bool:
    """When True, ignore client-supplied plan_id (use tenant record / API key only)."""
    if os.environ.get("SITESPIDER_ALLOW_CLIENT_PLAN", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return False
    if api_keys_configured():
        return True
    try:
        from sitespider.billing_stripe import load_tenants
        from sitespider.stripe_checkout import stripe_configured

        if stripe_configured() or load_tenants(base):
            return True
    except ImportError:
        pass
    return os.environ.get("SITESPIDER_STRICT_PLAN", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def client_plan_selectable(base: Path | None = None) -> bool:
    return not strict_plan_enforcement(base)


def resolve_effective_plan_id(
    tenant_id: str,
    *,
    ctx_plan_id: str,
    client_plan_id: str | None = None,
    base: Path | None = None,
) -> str:
    from sitespider.billing_stripe import resolve_tenant_plan

    stored = resolve_tenant_plan(tenant_id, base)
    if stored:
        return get_plan(stored).id
    if strict_plan_enforcement(base):
        return get_plan(ctx_plan_id).id
    if client_plan_id:
        pid = str(client_plan_id).strip().lower()
        if pid in PLANS:
            return pid
    return get_plan(ctx_plan_id).id
