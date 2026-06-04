"""租戶用量計量（訂閱配額）。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sitespider.plans import Plan, get_plan


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def usage_path(base: Path | None = None) -> Path:
    root = (base or Path.cwd()).resolve()
    return root / ".sitespider" / "usage.json"


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _empty_bucket() -> dict:
    return {
        "crawls": 0,
        "pages": 0,
        "serp_queries": 0,
        "ai_polishes": 0,
        "ai_polish_bonus": 0,
    }


def effective_ai_polish_limit(plan: Plan, usage: dict) -> int:
    if not plan.has("ai_polish"):
        return 0
    return plan.max_ai_polish_per_month + int(usage.get("ai_polish_bonus") or 0)


@dataclass
class QuotaCheck:
    allowed: bool
    reason: str = ""
    crawls_used: int = 0
    crawls_limit: int = 0
    serp_used: int = 0
    serp_limit: int = 0
    ai_used: int = 0
    ai_limit: int = 0


def tenant_usage(tenant_id: str, base: Path | None = None) -> dict:
    data = _load(usage_path(base))
    month = _month_key()
    bucket = (data.get(month) or {}).get(tenant_id) or _empty_bucket()
    return {
        "crawls": int(bucket.get("crawls", 0)),
        "pages": int(bucket.get("pages", 0)),
        "serp_queries": int(bucket.get("serp_queries", 0)),
        "ai_polishes": int(bucket.get("ai_polishes", 0)),
        "ai_polish_bonus": int(bucket.get("ai_polish_bonus", 0)),
    }


def quota_checks_enabled() -> bool:
    return os.environ.get("SITESPIDER_SKIP_QUOTA", "").strip().lower() not in (
        "1",
        "true",
        "yes",
    )


def check_crawl_quota(
    tenant_id: str,
    plan: Plan,
    *,
    pages_requested: int,
    base: Path | None = None,
) -> QuotaCheck:
    if not quota_checks_enabled():
        return QuotaCheck(True, crawls_limit=plan.max_crawls_per_month)
    u = tenant_usage(tenant_id, base)
    if u["crawls"] >= plan.max_crawls_per_month:
        return QuotaCheck(
            False,
            f"本月爬取次數已達上限（{plan.max_crawls_per_month}）",
            u["crawls"],
            plan.max_crawls_per_month,
        )
    if pages_requested > plan.max_pages_per_crawl:
        return QuotaCheck(
            False,
            f"單次頁數超過方案上限（{plan.max_pages_per_crawl}）",
            u["crawls"],
            plan.max_crawls_per_month,
        )
    return QuotaCheck(True, crawls_used=u["crawls"], crawls_limit=plan.max_crawls_per_month)


def check_ai_polish_quota(tenant_id: str, plan: Plan, base: Path | None = None) -> QuotaCheck:
    if not plan.has("ai_polish"):
        return QuotaCheck(
            False,
            "AI 文案需 Pro 或以上方案",
            ai_limit=plan.max_ai_polish_per_month,
        )
    u = tenant_usage(tenant_id, base)
    limit = effective_ai_polish_limit(plan, u)
    if limit <= 0:
        return QuotaCheck(False, "目前方案不含 AI 文案額度", ai_limit=0)
    used = u["ai_polishes"]
    if used >= limit:
        return QuotaCheck(
            False,
            f"本月 AI 文案次數已達上限（{limit}）",
            ai_used=used,
            ai_limit=limit,
        )
    return QuotaCheck(True, ai_used=used, ai_limit=limit)


def add_ai_polish_bonus(tenant_id: str, extra: int, base: Path | None = None) -> int:
    """加購 AI 次數（回傳加購後總額度加成）。"""
    path = usage_path(base)
    data = _load(path)
    month = _month_key()
    data.setdefault(month, {})
    bucket = data[month].setdefault(tenant_id, _empty_bucket())
    bucket["ai_polish_bonus"] = int(bucket.get("ai_polish_bonus", 0)) + max(0, extra)
    _save(path, data)
    return int(bucket["ai_polish_bonus"])


def reset_tenant_usage(tenant_id: str, base: Path | None = None) -> None:
    """重設指定帳號當月用量（本機／開發用）。"""
    path = usage_path(base)
    data = _load(path)
    month = _month_key()
    data.setdefault(month, {})
    data[month][tenant_id] = _empty_bucket()
    _save(path, data)


def record_crawl(
    tenant_id: str,
    *,
    pages: int,
    serp_queries: int = 0,
    base: Path | None = None,
) -> None:
    path = usage_path(base)
    data = _load(path)
    month = _month_key()
    data.setdefault(month, {})
    bucket = data[month].setdefault(tenant_id, _empty_bucket())
    bucket["crawls"] = int(bucket.get("crawls", 0)) + 1
    bucket["pages"] = int(bucket.get("pages", 0)) + pages
    bucket["serp_queries"] = int(bucket.get("serp_queries", 0)) + serp_queries
    _save(path, data)


def record_ai_polish(tenant_id: str, base: Path | None = None) -> None:
    path = usage_path(base)
    data = _load(path)
    month = _month_key()
    data.setdefault(month, {})
    bucket = data[month].setdefault(tenant_id, _empty_bucket())
    bucket["ai_polishes"] = int(bucket.get("ai_polishes", 0)) + 1
    _save(path, data)


def check_serp_quota(tenant_id: str, plan: Plan, count: int, base: Path | None = None) -> bool:
    if not plan.has("serp_rank"):
        return False
    u = tenant_usage(tenant_id, base)
    return u.get("serp_queries", 0) + count <= plan.max_serp_queries_per_month


def usage_limits_json(plan: Plan, usage: dict) -> dict:
    ai_cap = effective_ai_polish_limit(plan, usage)
    return {
        "max_pages_per_crawl": plan.max_pages_per_crawl,
        "max_crawls_per_month": plan.max_crawls_per_month,
        "max_serp_queries_per_month": plan.max_serp_queries_per_month,
        "max_ai_polish_per_month": plan.max_ai_polish_per_month,
        "ai_polish_bonus": int(usage.get("ai_polish_bonus") or 0),
        "ai_polish_limit_effective": ai_cap,
        "crawls_remaining": max(0, plan.max_crawls_per_month - usage.get("crawls", 0)),
        "ai_polishes_remaining": max(0, ai_cap - usage.get("ai_polishes", 0))
        if plan.has("ai_polish")
        else 0,
    }
