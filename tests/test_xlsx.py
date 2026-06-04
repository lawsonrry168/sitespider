"""Excel 匯出測試。"""

import pytest

from sitespider.crawler import CrawlReport, PageResult
from sitespider.report_xlsx import export_xlsx, xlsx_available


@pytest.mark.skipif(not xlsx_available(), reason="openpyxl not installed")
def test_export_xlsx(tmp_path):
    report = CrawlReport(start_url="https://x/", mode="file")
    report.pages["/a"] = PageResult(
        url="/a",
        status=200,
        content_type=None,
        response_ms=1,
        title="Title",
        meta_description="desc",
        meta_robots=None,
        canonical="/a",
        issues=["missing_h1"],
    )
    path = tmp_path / "out.xlsx"
    export_xlsx(report, path)
    assert path.stat().st_size > 500
