"""AI 設定合併與狀態分類。"""

from __future__ import annotations

from sitespider.ai_settings_store import (
    classify_ai_run_status,
    merge_ai_into_payload,
)


def test_merge_prefers_server_when_api_key_saved():
    payload = {
        "ai_provider": "openai",
        "ai_model": "gpt-5.4-mini",
        "ai_api_key": "sk-stale",
        "auto_ai_polish": False,
    }
    saved = {
        "ai_provider": "google",
        "ai_model": "gemini-3-flash",
        "ai_api_key": "AIza-real",
        "auto_ai_polish": True,
    }
    out = merge_ai_into_payload(payload, saved)
    assert out["ai_provider"] == "google"
    assert out["ai_model"] == "gemini-3-flash"
    assert out["ai_api_key"] == "AIza-real"
    assert out["auto_ai_polish"] is True


def test_merge_fills_empty_from_server_without_key():
    payload = {"ai_provider": "openai"}
    saved = {"ai_provider": "google", "ai_model": "gemini-2.0-flash"}
    out = merge_ai_into_payload(payload, saved)
    assert out["ai_provider"] == "openai"
    assert out["ai_model"] == "gemini-2.0-flash"


def test_classify_ai_run_status_error_on_401_only_hub():
    st = classify_ai_run_status(
        written=["ai-hub.html", "inspector.html"],
        errors=["page-copy: HTTP Error 401: Unauthorized"],
        ok=True,
    )
    assert st == "error"


def test_classify_ai_run_status_done_with_core():
    st = classify_ai_run_status(
        written=["ai-page-copy.html", "ai-hub.html"],
        errors=[],
        ok=True,
    )
    assert st == "done"
