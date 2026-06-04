"""客戶 Markdown 報告測試。"""

from sitespider.client_report import generate_client_markdown


def test_generate_client_markdown():
    report = {
        "start_url": "https://example.com/",
        "page_count": 2,
        "duration_sec": 1.0,
        "summary_issues": {"missing_title": ["https://example.com/a"]},
        "pages": {
            "https://example.com/a": {
                "indexability": "Non-Indexable",
                "indexability_status": "Canonicalised",
                "status": 200,
            },
            "https://example.com/b": {
                "indexability": "Indexable",
                "indexability_status": "",
                "status": 200,
            },
        },
    }
    md = generate_client_markdown(report, site_label="Example")
    assert "SEO 稽核報告" in md
    assert "Canonicalised" in md
    assert "missing_title" in md or "缺少 title" in md
