from pathlib import Path
from unittest.mock import MagicMock, patch

from sitespider.crawler import CrawlConfig, CrawlReport, PageResult
from sitespider.gsc_inspection import (
    inspect_url,
    normalize_gsc_site_url,
    run_gsc_rich_inspections,
    select_urls_for_inspection,
)
from sitespider.link_graph import export_link_graph_html, export_link_graph_simple_html
from sitespider.spelling_check import collect_spelling_rows, spelling_engine_name


def _page(url: str, **kw) -> PageResult:
    d = dict(
        status=200,
        content_type="text/html",
        response_ms=1,
        title="Hello world",
        meta_description="Welcome",
        meta_robots=None,
        canonical=url,
        indexability="Indexable",
        has_json_ld=True,
        json_ld_types=["Product"],
    )
    d.update(kw)
    return PageResult(url=url, **d)


def test_oauth_client_detection(tmp_path: Path):
    from sitespider.gsc_inspection import _is_oauth_client_secrets

    oauth = tmp_path / "oauth.json"
    oauth.write_text('{"installed":{"client_id":"x","client_secret":"y"}}', encoding="utf-8")
    sa = tmp_path / "sa.json"
    sa.write_text('{"type":"service_account","client_email":"a@b.iam.gserviceaccount.com"}', encoding="utf-8")
    assert _is_oauth_client_secrets(oauth)
    assert not _is_oauth_client_secrets(sa)


def test_normalize_gsc_site_url_trailing_slash():
    assert normalize_gsc_site_url("https://x.com", None) == "https://x.com/"
    assert normalize_gsc_site_url("https://x.com", "sc-domain:x.com") == "sc-domain:x.com"


def test_select_urls_prefers_json_ld():
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/a"] = _page("https://x/a", has_json_ld=False)
    report.pages["https://x/b"] = _page("https://x/b", has_json_ld=True)
    urls = select_urls_for_inspection(report, limit=1)
    assert urls == ["https://x/b"]


@patch("sitespider.gsc_inspection._build_service")
def test_run_gsc_inspections(mock_build):
    service = MagicMock()
    mock_build.return_value = service
    service.urlInspection().index().inspect().execute.return_value = {
        "inspectionResult": {
            "richResultsResult": {
                "verdict": "PASS",
                "detectedItems": [{"richResultType": "Product", "items": []}],
            }
        }
    }
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/a"] = _page("https://x/a")
    run_gsc_rich_inspections(
        report, site_url="https://x/", max_urls=1, delay_sec=0
    )
    assert report.gsc_rich_inspections["https://x/a"]["GSC Verdict"] == "PASS"


def test_inspect_url_api_error():
    svc = MagicMock()
    svc.urlInspection().index().inspect().execute.side_effect = RuntimeError("quota")
    row = inspect_url(svc, site_url="https://x/", inspection_url="https://x/a")
    assert row["GSC Status"] == "API Error"


def test_interactive_link_graph_has_d3(tmp_path: Path):
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/a"] = _page("https://x/a")
    export_link_graph_html(report, tmp_path / "link_graph.html")
    text = (tmp_path / "link_graph.html").read_text(encoding="utf-8")
    assert "d3.min.js" in text
    assert "forceSimulation" in text
    export_link_graph_simple_html(report, tmp_path / "simple.html")
    assert (tmp_path / "simple.html").exists()


def test_spelling_engine_column():
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/a"] = _page("https://x/a", title="Zzzqxv product")
    rows = collect_spelling_rows(report)
    assert rows
    assert "Engine" in rows[0]
    assert rows[0]["Engine"] == spelling_engine_name()
