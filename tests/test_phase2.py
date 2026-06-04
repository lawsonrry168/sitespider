"""Phase 2：客戶 README、增量 compare、多站比較。"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from sitespider.client_readme import build_client_readme_text
from sitespider.compare import compare_reports, urls_with_changes
from sitespider.multi_site_compare import build_multi_site_compare_html
from sitespider.package_report import package_report_dir


def test_client_readme_contains_basics(tmp_path: Path):
    cr = tmp_path / "crawl-report.json"
    cr.write_text(
        json.dumps({"start_url": "https://example.com", "page_count": 10, "pages": {}}),
        encoding="utf-8",
    )
    text = build_client_readme_text(tmp_path)
    assert "example.com" in text
    assert "REPORT-zh" in text


def test_compare_changed_urls_only():
    baseline = {
        "page_count": 2,
        "pages": {
            "/a": {"issues": ["missing_h1"], "status": 200},
            "/b": {"issues": [], "status": 200},
        },
    }
    current = {
        "page_count": 2,
        "pages": {
            "/a": {"issues": [], "status": 200},
            "/b": {"issues": [], "status": 200},
        },
    }
    changed = urls_with_changes(baseline, current)
    assert "/a" in changed
    assert "/b" not in changed
    inc = compare_reports(baseline, current, changed_urls_only=True)
    assert inc.changed_urls_only
    assert not inc.new_issues
    assert "/a" in inc.fixed_issues.get("missing_h1", [])


def test_package_includes_client_readme(tmp_path: Path):
    (tmp_path / "REPORT-zh.md").write_text("# test", encoding="utf-8")
    (tmp_path / "crawl-report.json").write_text("{}", encoding="utf-8")
    zpath = package_report_dir(tmp_path)
    with zipfile.ZipFile(zpath) as zf:
        names = zf.namelist()
    assert any("README-客戶.txt" in n for n in names)


def test_multi_site_compare_html(tmp_path: Path):
    p1 = tmp_path / "a" / "crawl-report.json"
    p2 = tmp_path / "b" / "crawl-report.json"
    p1.parent.mkdir()
    p2.parent.mkdir()
    p1.write_text(
        json.dumps(
            {"page_count": 5, "start_url": "https://a.com", "summary_issues": {"missing_h1": ["/x"]}}
        ),
        encoding="utf-8",
    )
    p2.write_text(
        json.dumps({"page_count": 8, "start_url": "https://b.com", "summary_issues": {}}),
        encoding="utf-8",
    )
    html = build_multi_site_compare_html([p1, p2])
    assert "a.com" in html
    assert "b.com" in html
    assert "missing_h1" in html or "H1" in html
