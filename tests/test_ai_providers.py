"""AI 平台 registry 與設定解析測試。"""

import os

from sitespider.ai_client import resolve_ai_config
from sitespider.ai_providers import AI_PROVIDERS, get_provider, providers_public_json


def test_providers_list_includes_mainstream():
    ids = {p["id"] for p in providers_public_json()}
    assert "openai" in ids
    assert "anthropic" in ids
    assert "google" in ids
    assert "deepseek" in ids
    assert "openrouter" in ids
    assert "minimax" in ids
    assert "ollama" in ids


def test_all_providers_have_models_except_custom():
    for pid, prov in AI_PROVIDERS.items():
        if pid == "custom":
            assert prov.models == ()
            continue
        assert len(prov.models) >= 3, pid
        assert prov.default_model in prov.models, pid


def test_openai_models_include_gpt5():
    openai = AI_PROVIDERS["openai"]
    assert "gpt-5.4-mini" in openai.models
    assert openai.default_model == "gpt-5.4-mini"


def test_anthropic_models_include_opus_48():
    anthropic = AI_PROVIDERS["anthropic"]
    assert "claude-opus-4-8" in anthropic.models
    assert "claude-sonnet-4-6" in anthropic.models


def test_gemini_models_include_25_and_20():
    google = AI_PROVIDERS["google"]
    assert "gemini-2.5-flash" in google.models
    assert google.default_model == "gemini-2.5-flash"
    assert "gemini-2.0-flash" in google.models
    assert "gemini-1.5-flash" not in google.models


def test_moonshot_kimi_k25():
    moonshot = AI_PROVIDERS["moonshot"]
    assert "kimi-k2.5" in moonshot.models
    assert "kimi-k2.6" in moonshot.models


def test_resolve_openai_compat(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = resolve_ai_config(api_key="sk-test", provider_id="deepseek", model="deepseek-v4-flash")
    assert cfg is not None
    assert cfg.base_url == "https://api.deepseek.com/v1"
    assert cfg.model == "deepseek-v4-flash"
    assert cfg.api_style == "openai"


def test_resolve_anthropic_style():
    cfg = resolve_ai_config(
        api_key="sk-ant-test",
        provider_id="anthropic",
        model="claude-sonnet-4-6",
    )
    assert cfg.api_style == "anthropic"
    assert cfg.base_url == "https://api.anthropic.com"


def test_resolve_ollama_without_key(monkeypatch):
    monkeypatch.delenv("SITESPIDER_AI_API_KEY", raising=False)
    cfg = resolve_ai_config(provider_id="ollama", model="llama3.3")
    assert cfg is not None
    assert cfg.provider_id == "ollama"


def test_custom_base_url(monkeypatch):
    cfg = resolve_ai_config(
        api_key="k",
        provider_id="custom",
        base_url="https://example.com/v1",
        model="my-model",
    )
    assert cfg.base_url == "https://example.com/v1"


def test_env_provider_fallback(monkeypatch):
    monkeypatch.setenv("SITESPIDER_AI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_env")
    cfg = resolve_ai_config()
    assert cfg is not None
    assert cfg.provider_id == "groq"
    from sitespider.plans import get_plan

    assert get_plan("unknown").id == "free"
