"""CSV URL 比對測試。"""

from __future__ import annotations

from pathlib import Path

from sitespider.diff_csv import compare_csv_urls, normalize_url


def test_normalize_url_trailing_slash():
    a = normalize_url("https://Example.com/page/")
    b = normalize_url("https://example.com/page")
    assert a == b


def test_compare_csv_urls(tmp_path: Path):
    sf = tmp_path / "sf.csv"
    ours = tmp_path / "ours.csv"
    sf.write_text(
        "Address,Title 1\n"
        "https://example.com/a,Title A\n"
        "https://example.com/b,Title B\n"
        "https://example.com/only-sf,Title\n",
        encoding="utf-8",
    )
    ours.write_text(
        "Address,Title 1\n"
        "https://example.com/a,Title A\n"
        "https://example.com/c,Title C\n",
        encoding="utf-8",
    )
    diff = compare_csv_urls(sf, ours)
    assert diff.sf_count == 3
    assert diff.ours_count == 2
    assert len(diff.in_both) == 1
    assert "https://example.com/b" in diff.only_sf
    assert "https://example.com/c" in diff.only_ours
