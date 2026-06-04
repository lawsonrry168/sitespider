"""管理後台 AI 加購。"""

from pathlib import Path

import pytest

from sitespider.admin_api import grant_ai_polish_bonus, list_tenants_dashboard, set_plan, verify_admin
from sitespider.billing_stripe import set_tenant_plan


def test_grant_ai_bonus_pro(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    set_tenant_plan("acme", "pro")
    out = grant_ai_polish_bonus("acme", 5)
    assert out["added"] == 5
    assert out["ai_polish_bonus"] == 5
    assert out["ai_polish_limit_effective"] == 20


def test_grant_ai_bonus_starter_rejected(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    set_tenant_plan("x", "starter")
    with pytest.raises(ValueError, match="不含 AI"):
        grant_ai_polish_bonus("x", 10)


def test_admin_set_plan(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    set_tenant_plan("t1", "free")
    out = set_plan("t1", "pro")
    assert out["plan_id"] == "pro"
    assert out["plan_name"] == "Pro"


def test_admin_dashboard_includes_ai_limits(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    set_tenant_plan("t1", "pro")
    grant_ai_polish_bonus("t1", 3)
    dash = list_tenants_dashboard()
    row = next(r for r in dash["tenants"] if r["tenant_id"] == "t1")
    assert row["limits"]["ai_polish_bonus"] == 3


def test_verify_admin_requires_key(monkeypatch):
    monkeypatch.delenv("SITESPIDER_ADMIN_KEY", raising=False)
    assert verify_admin(None)
    monkeypatch.setenv("SITESPIDER_ADMIN_KEY", "secret")
    assert not verify_admin("Bearer wrong")
    assert verify_admin("Bearer secret")
