"""Plan resolution anti-tamper."""

from __future__ import annotations

from pathlib import Path

from sitespider.billing_stripe import set_tenant_plan
from sitespider.plan_resolve import (
    client_plan_selectable,
    resolve_effective_plan_id,
    strict_plan_enforcement,
)


def test_dev_mode_allows_client_plan(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SITESPIDER_API_KEYS", raising=False)
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    assert not strict_plan_enforcement()
    pid = resolve_effective_plan_id(
        "default",
        ctx_plan_id="free",
        client_plan_id="agency",
    )
    assert pid == "agency"


def test_stripe_tenant_blocks_client_plan(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    set_tenant_plan("acme", "pro", base=tmp_path)
    assert strict_plan_enforcement(base=tmp_path)
    pid = resolve_effective_plan_id(
        "acme",
        ctx_plan_id="free",
        client_plan_id="agency",
        base=tmp_path,
    )
    assert pid == "pro"


def test_api_keys_strict(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(
        "SITESPIDER_API_KEYS",
        '{"sk_test":{"tenant":"acme","plan":"starter"}}',
    )
    assert strict_plan_enforcement()
    assert not client_plan_selectable()
