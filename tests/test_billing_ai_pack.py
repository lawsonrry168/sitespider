"""Stripe AI 加購包 webhook。"""

from pathlib import Path

from sitespider.billing_stripe import handle_checkout_completed, handle_stripe_event
from sitespider.billing_stripe import set_tenant_plan
from sitespider.usage import tenant_usage


def test_checkout_ai_polish_pack(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    set_tenant_plan("acme", "pro")
    msg = handle_checkout_completed(
        {
            "client_reference_id": "acme",
            "metadata": {
                "purchase_type": "ai_polish_pack",
                "tenant_id": "acme",
                "pack_size": "7",
            },
        }
    )
    assert "+7" in msg
    assert tenant_usage("acme")["ai_polish_bonus"] == 7


def test_ai_polish_pack_starter_rejected(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    set_tenant_plan("starter1", "starter")
    msg = handle_checkout_completed(
        {
            "metadata": {
                "purchase_type": "ai_polish_pack",
                "tenant_id": "starter1",
                "pack_size": "10",
            },
        }
    )
    assert "rejected" in msg
    assert tenant_usage("starter1")["ai_polish_bonus"] == 0


def test_stripe_event_routes_ai_pack(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    set_tenant_plan("t2", "pro")
    msg = handle_stripe_event(
        {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {
                        "purchase_type": "ai_polish_pack",
                        "tenant_id": "t2",
                        "pack_size": "10",
                    },
                }
            },
        }
    )
    assert "t2" in msg
    assert tenant_usage("t2")["ai_polish_bonus"] == 10
