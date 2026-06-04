"""單檔客戶 HTML 報告。"""

from __future__ import annotations

from pathlib import Path

from sitespider.crawler import CrawlReport
from sitespider.standalone_client_report import STANDALONE_FILENAME, export_standalone_client_html


def test_export_standalone_client_html(tmp_path: Path):
    report = CrawlReport(start_url="https://example.com/", mode="http")
    out = export_standalone_client_html(tmp_path, report=report, site_label="Demo")
    assert out.name == STANDALONE_FILENAME
    html = out.read_text(encoding="utf-8")
    assert "SEO 客戶報告" in html
    assert "example.com" in html
    assert "主要問題" in html
