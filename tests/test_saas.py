"""SaaS：方案、配額、GEXF、auth。"""

from __future__ import annotations

import json
from pathlib import Path

from sitespider.auth import resolve_bearer, require_tenant
from sitespider.link_export import export_link_graph_gexf
from sitespider.plans import get_plan
from sitespider.usage import check_crawl_quota, record_crawl, tenant_usage
from sitespider.crawler import CrawlConfig, CrawlReport, PageResult


def _page(url: str) -> PageResult:
    return PageResult(
        url=url,
        status=200,
        content_type="text/html",
        response_ms=1.0,
        title="Test",
        meta_description=None,
        meta_robots=None,
        canonical=None,
    )


def test_plan_limits():
    free = get_plan("free")
    assert free.max_pages_per_crawl == 50
    assert free.has("portal_share")
    p = get_plan("starter")
    assert p.max_pages_per_crawl == 200
    assert not p.has("serp_rank")
    assert p.has("ai_polish")
    assert p.max_ai_polish_per_month == 1
    assert p.has("branding_lite")
    assert get_plan("pro").has("ai_polish")
    assert get_plan("agency").has("ai_polish")


def test_quota(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    plan = get_plan("starter")
    q = check_crawl_quota("t1", plan, pages_requested=50)
    assert q.allowed
    record_crawl("t1", pages=10)
    assert tenant_usage("t1")["crawls"] == 1


def test_gexf(tmp_path: Path):
    r = CrawlReport(start_url="https://example.com/", mode="http", config=CrawlConfig())
    r.pages["https://example.com/"] = _page("https://example.com/")
    export_link_graph_gexf(r, tmp_path / "g.gexf", max_nodes=5)
    assert "<gexf" in (tmp_path / "g.gexf").read_text(encoding="utf-8")


def test_issue_api_key(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    key = __import__("sitespider.api_keys", fromlist=["issue_tenant_key"]).issue_tenant_key(
        "acme", "pro"
    )
    assert key.startswith("sk_live_")


def test_welcome_email_body():
    from sitespider.billing_onboarding import build_welcome_email

    subj, body = build_welcome_email(
        tenant_id="acme",
        plan_id="pro",
        api_key="sk_live_test123",
    )
    assert "acme" in body
    assert "sk_live_test123" in body
    assert "Pro" in subj or "pro" in subj.lower()


def test_portal_missing_customer():
    from sitespider.billing_onboarding import create_portal_session

    r = create_portal_session(stripe_customer_id="")
    assert "error" in r


def test_checkout_not_configured():
    from sitespider.stripe_checkout import create_checkout_session

    r = create_checkout_session(
        plan_id="pro",
        tenant_id="t1",
        success_url="http://localhost/success",
        cancel_url="http://localhost/pricing",
    )
    assert "error" in r


def test_auth_no_keys(monkeypatch):
    monkeypatch.delenv("SITESPIDER_API_KEYS", raising=False)
    monkeypatch.delenv("SITESPIDER_API_KEYS_FILE", raising=False)
    ctx = require_tenant(None, "myteam")
    assert ctx.tenant_id == "myteam"
