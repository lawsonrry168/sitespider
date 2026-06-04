"""JSON 報告還原測試。"""

import json
from pathlib import Path

from sitespider.crawler import CrawlReport, PageResult, report_to_dict
from sitespider.report import export_csv_pages
from sitespider.report_load import load_report_json, report_from_dict


def test_report_roundtrip_dataclasses(tmp_path: Path):
    report = CrawlReport(start_url="https://example.com/", mode="http")
    report.pages["https://example.com/"] = PageResult(
        url="https://example.com/",
        status=200,
        content_type="text/html",
        response_ms=1,
        title="Home",
        meta_description="desc",
        meta_robots=None,
        canonical="https://example.com/",
        h1=["H"],
        indexability="Indexable",
    )
    raw = report_to_dict(report)
    restored = report_from_dict(raw)
    assert len(restored.pages) == 1
    p = restored.pages["https://example.com/"]
    assert p.title == "Home"
    assert isinstance(p, PageResult)

    export_csv_pages(restored, tmp_path / "pages.csv")
    assert "Home" in (tmp_path / "pages.csv").read_text(encoding="utf-8")


def test_load_report_json_file(tmp_path: Path):
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/a"] = PageResult(
        url="https://x/a",
        status=200,
        content_type="text/html",
        response_ms=1,
        title="A",
        meta_description=None,
        meta_robots=None,
        canonical=None,
    )
    path = tmp_path / "crawl-report.json"
    path.write_text(json.dumps(report_to_dict(report), ensure_ascii=False), encoding="utf-8")
    loaded = load_report_json(path)
    assert loaded.pages["https://x/a"].title == "A"
