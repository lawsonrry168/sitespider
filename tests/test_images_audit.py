"""圖片尺寸稽核測試。"""

from sitespider.crawler import CrawlReport, ImageInfo, PageResult, _parse_img_dimension
from sitespider.post_crawl import audit_images


def test_parse_img_dimension():
    assert _parse_img_dimension("800") == 800
    assert _parse_img_dimension("50%") is None
    assert _parse_img_dimension(None) is None


def test_image_missing_dimensions():
    p = PageResult(
        url="https://x/",
        status=200,
        content_type="text/html",
        response_ms=1,
        title="Title long enough",
        meta_description="x" * 60,
        meta_robots=None,
        canonical="https://x/",
        h1=["H"],
        images=[ImageInfo(src="/i.jpg", alt="x", resolved="https://x/i.jpg", status=200)],
    )
    report = CrawlReport(start_url="https://x/", mode="http")
    report.pages["https://x/"] = p
    audit_images(report)
    assert "image_missing_dimensions" in p.issues
