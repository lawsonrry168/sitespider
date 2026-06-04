"""報告比對測試。"""

from __future__ import annotations

from sitespider.compare import compare_reports


def _report(pages: dict, summary: dict | None = None) -> dict:
    return {
        "page_count": len(pages),
        "pages": pages,
        "summary_issues": summary or {},
    }


def test_compare_new_and_fixed_issues():
    baseline = _report(
        {
            "/a": {"issues": ["missing_h1"]},
            "/b": {"issues": []},
        }
    )
    current = _report(
        {
            "/a": {"issues": []},
            "/b": {"issues": ["missing_title"]},
        }
    )
    result = compare_reports(baseline, current)
    assert "/b" in result.new_issues.get("missing_title", [])
    assert "/a" in result.fixed_issues.get("missing_h1", [])
    assert result.has_regressions


def test_compare_url_and_status_delta():
    baseline = _report(
        {"/a": {"issues": [], "status": 200}, "/gone": {"issues": [], "status": 404}}
    )
    current = _report(
        {"/a": {"issues": [], "status": 301}, "/new": {"issues": [], "status": 200}}
    )
    result = compare_reports(baseline, current)
    assert "/new" in result.urls_added
    assert "/gone" in result.urls_removed
    assert result.status_changes["/a"] == (200, 301)
    assert result.has_regressions


def test_compare_changed_urls_only_filters_unchanged():
    baseline = _report(
        {
            "/a": {"issues": ["missing_h1"]},
            "/b": {"issues": []},
        }
    )
    current = _report(
        {
            "/a": {"issues": []},
            "/b": {"issues": []},
        }
    )
    full = compare_reports(baseline, current)
    inc = compare_reports(baseline, current, changed_urls_only=True)
    assert "/a" in full.fixed_issues.get("missing_h1", [])
    assert "/a" in inc.fixed_issues.get("missing_h1", [])
    assert inc.changed_urls_only


def test_compare_no_regression():
    issues = {"missing_h1": ["/a"]}
    baseline = _report({"/a": {"issues": ["missing_h1"]}}, issues)
    current = _report({"/a": {"issues": ["missing_h1"]}}, issues)
    result = compare_reports(baseline, current)
    assert not result.has_regressions
