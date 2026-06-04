from pathlib import Path

from sitespider.report_theme import (
    console_home_href,
    export_ai_placeholders,
    locate_report_job_dir,
    report_back_button,
    report_console_button,
    report_nav_links,
    report_topbar,
)


def test_report_nav_hides_missing_files(tmp_path: Path):
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    nav = report_nav_links(tmp_path, active="index.html")
    assert "站內技術報告" in nav
    assert "nav-active" in nav
    assert "AI 交付" not in nav or "nav-locked" in nav
    assert "ai-hub.html" not in nav


def test_ai_placeholders_created(tmp_path: Path):
    written = export_ai_placeholders(tmp_path)
    assert "ai-hub.html" in written
    assert (tmp_path / "ai-hub.html").is_file()
    nav = report_nav_links(tmp_path)
    assert 'href="ai-hub.html"' in nav


def test_report_topbar_includes_brand(tmp_path: Path):
    report_dir = tmp_path / "reports" / "default" / "job1"
    report_dir.mkdir(parents=True)
    (report_dir / "index.html").write_text("<html></html>", encoding="utf-8")
    bar = report_topbar(report_dir, "分析圖表", active="dashboard.html", site_url="https://example.com/")
    assert "SiteSpider" in bar
    assert "分析圖表" in bar
    assert "<svg" in bar
    assert "← 返回" in bar
    assert "ss-console-home" in bar
    assert "爬取中心" in bar
    assert "job=job1" in bar
    assert "report-topbar-docs" in bar
    assert "report-view-site-btn" in bar
    assert "檢視網站" in bar
    assert 'href="/guide"' in bar
    assert "report-guide-link" in bar


def test_report_back_button_has_fallback():
    btn = report_back_button(fallback="REPORT-zh.html")
    assert "← 返回" in btn
    assert "REPORT-zh.html" in btn


def test_console_home_href_includes_job(tmp_path: Path):
    report_dir = tmp_path / "reports" / "default" / "abc123"
    report_dir.mkdir(parents=True)
    (report_dir / "crawl-report.json").write_text("{}", encoding="utf-8")
    href = console_home_href(report_dir)
    assert "job=abc123" in href
    assert "tenant=default" in href
    assert "step=3" in href
    btn = report_console_button(out_dir=report_dir)
    assert "job=abc123" in btn


def test_console_home_href_flat_demo_job(tmp_path: Path):
    """扁平 reports/{job_id}/（如 123deal-smoke）應回到 default 租戶。"""
    report_dir = tmp_path / "reports" / "123deal-smoke"
    report_dir.mkdir(parents=True)
    (report_dir / "crawl-report.json").write_text("{}", encoding="utf-8")
    gallery = report_dir / "images-gallery.html"
    gallery.write_text("<html></html>", encoding="utf-8")
    assert locate_report_job_dir(gallery) == report_dir.resolve()
    href = console_home_href(gallery)
    assert "job=123deal-smoke" in href
    assert "tenant=default" in href
    assert "images-gallery" not in href


def test_console_home_href_from_url_like_path(tmp_path: Path):
    """模擬 /reports/123deal-smoke/page.html 的檔案路徑。"""
    report_dir = tmp_path / "reports" / "123deal-smoke"
    report_dir.mkdir(parents=True)
    page = report_dir / "REPORT-zh.html"
    page.write_text("<html></html>", encoding="utf-8")
    href = console_home_href(page)
    assert href.endswith("step=3")
    assert "job=123deal-smoke" in href
    assert "tenant=default" in href
