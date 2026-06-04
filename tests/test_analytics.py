"""分析儀表板測試。"""

from pathlib import Path

from sitespider.crawler import CrawlReport, PageResult
from sitespider.report_analytics import compute_analytics, export_dashboard_html


def test_compute_analytics():
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["/a"] = PageResult(
        url="/a",
        status=200,
        content_type="text/html",
        response_ms=1,
        title="A" * 40,
        meta_description="m",
        meta_robots=None,
        canonical="/b",
        indexability="Non-Indexable",
        indexability_status="Canonicalised",
        issues=["canonical_mismatch"],
    )
    data = compute_analytics(report)
    assert data["url_count"] == 1
    assert "Canonicalised" in data["indexability_status"]
    assert data["health_score"] >= 0
    assert data["health_grade"] in {"A", "B", "C", "D", "F"}
    assert "HTTP 回應正常" in data["score_breakdown"]
    assert data["issue_samples"]


def test_export_dashboard_html(tmp_path: Path):
    template = Path(__file__).resolve().parents[1] / "sitespider" / "ui" / "analytics_dashboard.html"
    assert template.exists(), "analytics_dashboard.html template missing"
    report = CrawlReport(start_url="https://x/", mode="http")
    report.finished_at = report.started_at + 1
    report.pages["https://x/"] = PageResult(
        url="https://x/",
        status=200,
        content_type="text/html",
        response_ms=1,
        title="Home",
        meta_description=None,
        meta_robots=None,
        canonical=None,
        indexability="Indexable",
    )
    path = tmp_path / "dashboard.html"
    export_dashboard_html(report, path)
    text = path.read_text(encoding="utf-8")
    assert "chart-issues" in text
    assert "技術 SEO 健康分" in text
    assert "score-breakdown" in text
    assert "問題清單" in text
