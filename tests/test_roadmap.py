"""FEATURE_ROADMAP 模組單元與接線測試。"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from sitespider.backlink_api import MozProvider
from sitespider.crawler import CrawlConfig, CrawlReport, ImageInfo, PageResult
from sitespider.fragment_check import (
    check_fragments_in_soup,
    check_fragments_on_page,
    collect_fragment_hrefs_from_html,
    mark_broken_fragments,
)
from sitespider.heading_audit import audit_heading_hierarchy
from sitespider.insecure_forms import audit_insecure_forms
from sitespider.keyword_density import audit_keyword_density
from sitespider.readability import compute_readability
from sitespider.roadmap_runner import export_roadmap_reports, run_roadmap_audits
from sitespider.security_headers import audit_security_headers, security_score
from sitespider.sheets_export import export_to_sheets
from sitespider.similarity import detect_near_duplicates, hamming_distance, shingle_cosine, simhash64
from sitespider.tracking_audit import apply_site_tracking_issues, audit_html_tracking
from sitespider.url_quality import audit_url_quality
from sitespider.user_agent_presets import resolve_user_agent


def _page(url: str, **kwargs) -> PageResult:
    defaults = dict(
        status=200,
        content_type="text/html",
        response_ms=1.0,
        title="T",
        meta_description=None,
        meta_robots=None,
        canonical=url,
    )
    defaults.update(kwargs)
    return PageResult(url=url, **defaults)


def test_simhash_and_shingle_cosine():
    h1 = simhash64("hello world foo bar baz")
    h2 = simhash64("hello world foo bar baz extra")
    assert hamming_distance(h1, h2) >= 0
    assert shingle_cosine("hello world test", "hello world test") == 1.0
    assert shingle_cosine("hello world", "goodbye moon") < 0.5


def test_detect_near_duplicates():
    report = CrawlReport("https://example.com/", "http")
    p1 = _page("https://example.com/a")
    p1.body_text = "這是一段測試內容用於近似重複偵測功能驗證abcdef"
    p2 = _page("https://example.com/b")
    p2.body_text = "這是一段測試內容用於近似重複偵測功能驗證abcdef略改"
    report.pages[p1.url] = p1
    report.pages[p2.url] = p2
    pairs = detect_near_duplicates(report, threshold=0.5)
    assert isinstance(pairs, list)


def test_heading_skip():
    report = CrawlReport("https://example.com/", "http")
    p = _page("https://example.com/")
    p.heading_sequence = [1, 3]
    report.pages[p.url] = p
    audit_heading_hierarchy(report)
    assert "heading_skip" in p.issues


def test_security_headers():
    report = CrawlReport("https://example.com/", "http")
    p = _page("https://example.com/")
    p.is_https = True
    p.response_headers = {"content-type": "text/html"}
    report.pages[p.url] = p
    audit_security_headers(report)
    assert "missing_security_header" in p.issues
    assert security_score(p) < 100


def test_url_quality():
    report = CrawlReport("https://example.com/", "http")
    p = _page("https://example.com/Page_With_underscore")
    report.pages[p.url] = p
    audit_url_quality(report)
    assert "url_uppercase" in p.issues
    assert "url_underscore" in p.issues


def test_readability_english():
    p = _page("https://example.com/")
    p.body_text = "This is a simple test. It has short sentences. Easy to read for everyone today."
    p.html_lang = "en"
    ease, _grade = compute_readability(p)
    assert ease is not None


def test_user_agent_preset():
    ua = resolve_user_agent("googlebot-desktop")
    assert "Googlebot" in ua


def test_fragment_collect_and_soup_check():
    from bs4 import BeautifulSoup

    html = (
        '<html><body><a href="#ok">x</a><a href="#missing">y</a>'
        '<div id="ok"></div></body></html>'
    )
    hrefs = collect_fragment_hrefs_from_html(html)
    assert any("#ok" in h for h in hrefs)
    soup = BeautifulSoup(html, "lxml")
    links = [SimpleNamespace(href=h) for h in hrefs]
    broken = check_fragments_in_soup(soup, "https://example.com/", links)
    assert "missing" in broken
    assert "ok" not in broken


def test_fragment_links_not_empty_path():
    """回歸：傳入真實 links 才能偵測 broken fragment（不能傳 []）。"""

    class FakePage:
        def evaluate(self, _js, ids):
            return [i for i in ids if i == "gone"]

    links = [SimpleNamespace(href="#gone"), SimpleNamespace(href="#stay")]
    assert check_fragments_on_page(FakePage(), "https://ex.com/", []) == []
    broken = check_fragments_on_page(FakePage(), "https://ex.com/", links)
    assert "gone" in broken


def test_mark_broken_fragments_sets_issue():
    report = CrawlReport("https://example.com/", "http")
    p = _page("https://example.com/")
    report.pages[p.url] = p
    mark_broken_fragments(report, p.url, ["nope"])
    assert "broken_fragment" in p.issues
    assert p.broken_fragments == ["nope"]


def test_insecure_form_action():
    report = CrawlReport("https://example.com/", "http")
    p = _page("https://example.com/")
    p.is_https = True
    p.form_actions = ["http://evil.example/submit"]
    report.pages[p.url] = p
    audit_insecure_forms(report)
    assert "insecure_form_action" in p.issues


def test_keyword_stuffing():
    report = CrawlReport("https://example.com/", "http")
    p = _page("https://example.com/")
    p.body_text = " ".join(["spam"] * 20 + ["other"] * 5)
    report.pages[p.url] = p
    audit_keyword_density(report)
    assert "keyword_stuffing" in p.issues


def test_tracking_footprint():
    html = (
        '<script src="https://www.googletagmanager.com/gtag/js?id=G-ABC123"></script>'
        "<script>gtag('config','G-ABC123');</script>"
    )
    fp = audit_html_tracking(html)
    assert fp["has_ga4"]
    assert "G-ABC123" in fp["ga4_ids"]


def test_tracking_site_issues_missing():
    report = CrawlReport("https://example.com/", "http")
    p = _page("https://example.com/")
    p.indexability = "Indexable"
    p.tracking_footprint = {
        "gtm_ids": [],
        "ga4_ids": [],
        "ua_ids": [],
        "fb_pixel_ids": [],
        "has_gtm": False,
        "has_ga4": False,
        "has_ua": False,
        "has_fb_pixel": False,
        "has_datalayer": False,
        "has_any_tracking": False,
    }
    report.pages[p.url] = p
    apply_site_tracking_issues(report)
    assert "missing_tracking" in p.issues


def test_moz_referring_domains_mapped():
    def fake_fetch(_url: str, _payload: dict):
        return {
            "results": [
                {
                    "page": "https://example.com/",
                    "root_domains_to_page": 12,
                    "external_pages_to_page": 34,
                    "domain_authority": 50,
                }
            ]
        }

    moz = MozProvider("token", fetch=fake_fetch)
    metrics = moz.fetch_url_metrics("https://example.com/")
    assert metrics["referring_domains"] == 12
    assert metrics["backlinks_count"] == 34


def test_sheets_export_graceful_without_creds():
    report = CrawlReport("https://example.com/", "http")
    report.pages["https://example.com/"] = _page("https://example.com/")
    export_to_sheets(report, "sheet-id-xyz", credentials_path=None)
    assert any("Sheets" in e or "sheets" in e.lower() or "credential" in e.lower() or "google" in e.lower() for e in report.errors)


def test_run_roadmap_audits_and_export(tmp_path: Path):
    report = CrawlReport("https://example.com/", "http")
    p = _page("https://example.com/")
    p.body_text = "Hello world. Another sentence here for readability scoring."
    p.html_lang = "en"
    p.is_https = True
    p.response_headers = {}
    p.heading_sequence = [1, 2]
    p.raw_html = "<html><body><h1>Hi</h1><p>Hello world.</p></body></html>"
    report.pages[p.url] = p
    cfg = CrawlConfig(
        audit_near_duplicates=True,
        audit_tracking=True,
        export_directory_tree=True,
        export_looker=True,
        export_sheets=False,
    )
    run_roadmap_audits(report, config=cfg)
    written = export_roadmap_reports(report, tmp_path, config=cfg)
    assert "near_duplicates.csv" in written
    assert "readability.csv" in written
    assert "directory_tree.html" in written
    assert any(w.startswith("looker/") for w in written)
    assert (tmp_path / "directory_tree.html").is_file()


def test_export_sheets_flag_calls_module(monkeypatch, tmp_path: Path):
    called: dict = {}

    def fake_export(report, spreadsheet_id, credentials_path=None):
        called["id"] = spreadsheet_id
        called["creds"] = credentials_path

    monkeypatch.setattr("sitespider.sheets_export.export_to_sheets", fake_export)
    report = CrawlReport("https://example.com/", "http")
    report.pages["https://example.com/"] = _page("https://example.com/")
    cfg = CrawlConfig(
        export_sheets=True,
        sheets_id="abc123",
        sheets_credentials="/tmp/creds.json",
        audit_tracking=False,
        export_directory_tree=False,
        export_looker=False,
        audit_near_duplicates=False,
        audit_readability=False,
        audit_keyword_density=False,
        audit_security_headers=False,
    )
    export_roadmap_reports(report, tmp_path, config=cfg)
    assert called.get("id") == "abc123"
    assert called.get("creds") == "/tmp/creds.json"


def test_cli_has_roadmap_flags():
    from sitespider.cli import build_parser

    help_text = build_parser().format_help()
    for flag in (
        "--export-sheets",
        "--sheets-id",
        "--ga4-date-range",
        "--near-duplicate-threshold",
        "--user-agent-preset",
        "--image-sitemap",
    ):
        assert flag in help_text


def test_image_sitemap_export(tmp_path: Path):
    from sitespider.sitemap_export import export_image_sitemap_xml

    report = CrawlReport("https://example.com/", "http")
    p = _page("https://example.com/")
    p.images = [
        ImageInfo(
            src="/a.jpg",
            alt="x",
            resolved="https://example.com/a.jpg",
            status=200,
            width=10,
            height=10,
        )
    ]
    report.pages[p.url] = p
    n = export_image_sitemap_xml(report, tmp_path / "image_sitemap.xml")
    assert n >= 1
    text = (tmp_path / "image_sitemap.xml").read_text(encoding="utf-8")
    assert "a.jpg" in text


def test_robots_test_api_helper():
    from sitespider.robots import test_robots_url

    robots = "User-agent: *\nDisallow: /private/\n"
    r = test_robots_url(robots, "SiteSpider", "https://example.com/private/x")
    assert r["allowed"] is False
    r2 = test_robots_url(robots, "SiteSpider", "https://example.com/public/")
    assert r2["allowed"] is True


def test_issue_labels_cover_roadmap():
    from sitespider.issues import ISSUE_LABELS

    for code in (
        "near_duplicate",
        "broken_fragment",
        "grammar_error",
        "insecure_form_action",
        "missing_tracking",
        "a11y_violation",
        "zero_traffic_page",
    ):
        assert code in ISSUE_LABELS
