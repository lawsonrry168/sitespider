"""Tenant branding persistence."""

from __future__ import annotations

from pathlib import Path

from sitespider.branding import branding_for_plan
from sitespider.plans import get_plan
from sitespider.tenant_branding import get_tenant_branding, set_tenant_branding


def test_set_and_get_branding(tmp_path: Path):
    saved = set_tenant_branding(
        "acme",
        {
            "consultant_name": "Acme SEO",
            "logo_url": "https://example.com/logo.png",
            "accent_color": "#112233",
        },
        base=tmp_path,
    )
    assert saved["consultant_name"] == "Acme SEO"
    assert get_tenant_branding("acme", base=tmp_path)["logo_url"].endswith("logo.png")


def test_branding_for_plan_gates():
    raw = {
        "consultant_name": "Acme",
        "logo_url": "https://x/logo.png",
        "accent_color": "#ff0000",
    }
    lite = branding_for_plan(get_plan("starter"), raw)
    assert lite.consultant_name == "Acme"
    assert lite.logo_url == ""

    full = branding_for_plan(get_plan("agency"), raw)
    assert full.logo_url == raw["logo_url"]

    free = branding_for_plan(get_plan("free"), raw)
    assert free.consultant_name == ""
