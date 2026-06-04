"""
訂閱方案與功能開關（SaaS / 自架多租戶）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass


FEATURE_LABELS: dict[str, str] = {
    "heatmap": "問題熱力圖",
    "zip": "交付 ZIP",
    "compare": "報告比對",
    "webgl": "WebGL 內鏈圖",
    "gexf": "Gephi 匯出",
    "serp_rank": "SERP 排名",
    "notifications": "Slack / Email 通知",
    "schedule": "排程爬取",
    "gsc": "GSC Rich Results",
    "pdf": "交付 PDF",
    "ai_polish": "AI 文案（多平台）",
    "branding_lite": "報告署名（公司名）",
    "white_label": "完整報告品牌",
    "api": "API 多租戶",
    "multi_tenant": "多站儀表板",
    "portal_share": "客戶分享連結",
}


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    price_usd_month: int
    max_pages_per_crawl: int
    max_crawls_per_month: int
    max_serp_queries_per_month: int
    max_ai_polish_per_month: int
    features: frozenset[str]
    tagline: str = ""

    def has(self, feature: str) -> bool:
        return feature in self.features

    def allows_ai_bonus_purchase(self) -> bool:
        """手動／Stripe 加購 AI 次數（Starter 僅含方案內建額度）。"""
        return self.id in ("pro", "agency")


PLANS: dict[str, Plan] = {
    "free": Plan(
        id="free",
        name="Free",
        price_usd_month=0,
        max_pages_per_crawl=50,
        max_crawls_per_month=2,
        max_serp_queries_per_month=0,
        max_ai_polish_per_month=0,
        features=frozenset({"heatmap", "zip", "compare", "portal_share"}),
        tagline="試用與小型站點",
    ),
    "starter": Plan(
        id="starter",
        name="Starter",
        price_usd_month=49,
        max_pages_per_crawl=200,
        max_crawls_per_month=8,
        max_serp_queries_per_month=0,
        max_ai_polish_per_month=1,
        features=frozenset(
            {"heatmap", "zip", "compare", "portal_share", "branding_lite", "ai_polish"}
        ),
        tagline="獨立顧問入門 · 每月 1 次 AI 文案",
    ),
    "pro": Plan(
        id="pro",
        name="Pro",
        price_usd_month=149,
        max_pages_per_crawl=2_000,
        max_crawls_per_month=40,
        max_serp_queries_per_month=100,
        max_ai_polish_per_month=15,
        features=frozenset(
            {
                "heatmap",
                "zip",
                "compare",
                "webgl",
                "gexf",
                "serp_rank",
                "notifications",
                "schedule",
                "gsc",
                "pdf",
                "ai_polish",
                "portal_share",
            }
        ),
        tagline="顧問交付主力方案",
    ),
    "agency": Plan(
        id="agency",
        name="Agency",
        price_usd_month=399,
        max_pages_per_crawl=10_000,
        max_crawls_per_month=200,
        max_serp_queries_per_month=500,
        max_ai_polish_per_month=60,
        features=frozenset(
            {
                "heatmap",
                "zip",
                "compare",
                "webgl",
                "gexf",
                "serp_rank",
                "notifications",
                "schedule",
                "gsc",
                "pdf",
                "white_label",
                "api",
                "multi_tenant",
                "ai_polish",
                "portal_share",
            }
        ),
        tagline="多客戶團隊與白標",
    ),
}


def get_plan(plan_id: str | None) -> Plan:
    pid = (plan_id or "").strip().lower()
    if pid in PLANS:
        return PLANS[pid]
    return PLANS["free"]


def default_local_plan_id() -> str:
    return os.environ.get("SITESPIDER_DEFAULT_PLAN", "free").strip().lower() or "free"


def plans_public_json() -> list[dict]:
    out: list[dict] = []
    for p in PLANS.values():
        out.append(
            {
                "id": p.id,
                "name": p.name,
                "tagline": p.tagline,
                "price_usd_month": p.price_usd_month,
                "max_pages_per_crawl": p.max_pages_per_crawl,
                "max_crawls_per_month": p.max_crawls_per_month,
                "max_serp_queries_per_month": p.max_serp_queries_per_month,
                "max_ai_polish_per_month": p.max_ai_polish_per_month,
                "allows_ai_bonus_purchase": p.allows_ai_bonus_purchase(),
                "features": sorted(p.features),
                "feature_labels": [FEATURE_LABELS.get(f, f) for f in sorted(p.features)],
                "requires_stripe": p.price_usd_month > 0,
            }
        )
    order = ("free", "starter", "pro", "agency")
    out.sort(key=lambda x: order.index(x["id"]) if x["id"] in order else 99)
    return out
