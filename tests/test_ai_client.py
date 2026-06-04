"""AI client 模型對應與錯誤訊息。"""

from __future__ import annotations

import urllib.error

from sitespider.ai_client import friendly_ai_error, resolve_ai_config
from sitespider.ai_providers import normalize_model_name


def test_normalize_gemini_15_to_current():
    assert normalize_model_name("google", "gemini-1.5-flash") == "gemini-2.0-flash"
    assert normalize_model_name("google", "gemini-1.5-pro") == "gemini-2.5-pro"
    assert normalize_model_name("openai", "gemini-1.5-flash") == "gemini-1.5-flash"


def test_resolve_maps_legacy_gemini_model():
    cfg = resolve_ai_config(
        api_key="test-key",
        provider_id="google",
        model="gemini-1.5-flash",
    )
    assert cfg is not None
    assert cfg.model == "gemini-2.0-flash"
    assert cfg.model_requested == "gemini-1.5-flash"


def test_resolve_keeps_gemini_25_when_selected():
    cfg = resolve_ai_config(
        api_key="test-key",
        provider_id="google",
        model="gemini-2.5-flash",
    )
    assert cfg is not None
    assert cfg.model == "gemini-2.5-flash"
    assert cfg.model_requested == "gemini-2.5-flash"


def test_friendly_ai_error_503():
    err = urllib.error.HTTPError(
        url="https://example.com",
        code=503,
        msg="Service Unavailable",
        hdrs=None,
        fp=None,
    )
    text = friendly_ai_error(err)
    assert "503" in text
    assert "忙碌" in text or "重試" in text
