"""AI 報告模型說明（設定 vs 實際 API）。"""

from sitespider.ai_meta_display import ai_model_caption, enrich_ai_meta, patch_ai_html_model_line


def test_caption_no_remap_when_same():
    cap = ai_model_caption(
        {
            "provider_id": "google",
            "provider_name": "Google Gemini",
            "model_requested": "gemini-2.5-flash",
            "model_resolved": "gemini-2.5-flash",
        }
    )
    assert "設定" not in cap
    assert "gemini-2.5-flash" in cap


def test_caption_shows_remap_when_legacy():
    cap = ai_model_caption(
        {
            "provider_id": "google",
            "model": "gemini-1.5-flash",
        }
    )
    assert "設定" in cap
    assert "gemini-1.5-flash" in cap
    assert "gemini-2.0-flash" in cap


def test_enrich_legacy_model_field():
    m = enrich_ai_meta({"provider_id": "google", "model": "gemini-1.5-pro"})
    assert m["model_requested"] == "gemini-1.5-pro"
    assert m["model_resolved"] == "gemini-2.5-pro"


def test_patch_html_lead_from_meta(tmp_path):
    (tmp_path / "ai-polish-meta.json").write_text(
        '{"provider_id":"google","model_requested":"gemini-1.5-flash","model_resolved":"gemini-2.0-flash"}',
        encoding="utf-8",
    )
    html = '<p class="lead">平台 Google · 模型 <code>gemini-2.5-flash</code></p><h1>Hub</h1>'
    out = patch_ai_html_model_line(html, tmp_path)
    assert "設定" in out
    assert "gemini-1.5-flash" in out
    assert "gemini-2.0-flash" in out
