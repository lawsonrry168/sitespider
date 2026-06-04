"""AI 匯出單元測試（不含真實 API）。"""

from sitespider.ai_exports import CopyVariant, PageCopyDraft, _validate, export_page_copy_files, faq_body_html, faq_json_ld, faq_schema_script_tag


def test_validate_title_meta():
    ok_t = _validate("A" * 45, "title")
    assert ok_t.ok and ok_t.chars == 45
    bad_t = _validate("x" * 70, "title")
    assert not bad_t.ok
    ok_m = _validate("m" * 120, "meta")
    assert ok_m.ok
    bad_m = _validate("short", "meta")
    assert not bad_m.ok


def test_faq_json_ld():
    faqs = [{"question": "Q?", "answer": "A."}]
    ld = faq_json_ld(faqs)
    assert ld["@type"] == "FAQPage"
    assert len(ld["mainEntity"]) == 1


def test_faq_body_html():
    html = faq_body_html([{"question": "如何預約？", "answer": "線上填表即可。"}])
    assert "faq-section" in html
    assert "如何預約" in html
    tag = faq_schema_script_tag(faq_json_ld([{"question": "Q", "answer": "A"}]))
    assert "application/ld+json" in tag


def test_export_page_copy_html(tmp_path):
    drafts = [
        PageCopyDraft(
            url="https://x.com/",
            segment="homepage",
            current_title="Old",
            current_meta="",
            titles=(_validate("新標題 " * 5, "title"),),
            metas=(_validate("描述" * 30, "meta"),),
            h1="H1 方向",
        )
    ]
    written = export_page_copy_files(drafts, tmp_path)
    assert "ai-page-copy.html" in written
    html = (tmp_path / "ai-page-copy.html").read_text(encoding="utf-8")
    assert "AI Title / Meta" in html
