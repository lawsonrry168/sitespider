"""API Key 驗證（多租戶 SaaS）。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from sitespider.plans import get_plan


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    plan_id: str
    label: str = ""

    @property
    def plan(self):
        return get_plan(self.plan_id)


def _load_key_map() -> dict[str, dict]:
    from sitespider.api_keys import merged_key_map

    return merged_key_map()


def resolve_bearer(authorization: str | None) -> TenantContext | None:
    """
    Authorization: Bearer <api_key>
    金鑰對應 JSON：{"<key>": {"tenant": "acme", "plan": "pro", "label": "Acme Corp"}}
    未設定 SITESPIDER_API_KEYS 時不強制驗證（本機模式）。
    """
    key_map = _load_key_map()
    if not key_map:
        return None
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    meta = key_map.get(token)
    if not meta or not isinstance(meta, dict):
        return None
    tenant = str(meta.get("tenant") or meta.get("tenant_id") or "").strip()
    if not tenant:
        return None
    return TenantContext(
        tenant_id=tenant,
        plan_id=str(meta.get("plan") or meta.get("plan_id") or "pro"),
        label=str(meta.get("label") or tenant),
    )


def require_tenant(authorization: str | None, payload_tenant: str | None) -> TenantContext:
    """有設定 API keys 時必須驗證；否則使用 payload 或 default。"""
    ctx = resolve_bearer(authorization)
    if ctx:
        return ctx
    if _load_key_map():
        raise PermissionError("Invalid or missing API key")
    tid = (payload_tenant or "default").strip() or "default"
    from sitespider.plans import default_local_plan_id

    return TenantContext(tenant_id=tid, plan_id=default_local_plan_id(), label=tid)
