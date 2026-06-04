"""Image download and gallery export."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from sitespider.crawler import CrawlConfig, CrawlReport, ImageInfo, PageResult
from sitespider.image_export import (
    download_report_images,
    export_images_gallery_html,
    iter_unique_images,
)


def _report_with_image(url: str = "https://example.com/img/a.png") -> CrawlReport:
    page = PageResult(
        url="https://example.com/",
        status=200,
        content_type="text/html",
        response_ms=1.0,
        title="T",
        meta_description=None,
        meta_robots=None,
        canonical=None,
        images=[ImageInfo(src="/a.png", alt="Hero", resolved=url, status=200)],
    )
    return CrawlReport(
        start_url="https://example.com/",
        mode="http",
        config=CrawlConfig(download_images=True),
        pages={"https://example.com/": page},
    )


def test_iter_unique_images_dedupes():
    report = _report_with_image()
    report.pages["https://example.com/about"] = PageResult(
        url="https://example.com/about",
        status=200,
        content_type="text/html",
        response_ms=1.0,
        title="A",
        meta_description=None,
        meta_robots=None,
        canonical=None,
        images=[ImageInfo(src="/a.png", alt="", resolved="https://example.com/img/a.png", status=200)],
    )
    assert len(iter_unique_images(report)) == 1


def test_download_report_images(tmp_path: Path):
    report = _report_with_image()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "image/png"}
    mock_resp.iter_content = lambda chunk_size=65536: [b"fakepng"]
    with patch("sitespider.image_export.requests.Session") as sess:
        sess.return_value.get.return_value = mock_resp
        n, img_dir = download_report_images(report, tmp_path, max_images=10)
    assert n == 1
    assert img_dir.is_dir()
    assert report.pages["https://example.com/"].images[0].local_file
    assert (tmp_path / report.pages["https://example.com/"].images[0].local_file).is_file()


def test_export_images_gallery_html(tmp_path: Path):
    report = _report_with_image()
    report.pages["https://example.com/"].images[0].local_file = "images/0001_test.png"
    out = tmp_path / "images-gallery.html"
    export_images_gallery_html(report, out)
    html = out.read_text(encoding="utf-8")
    assert "圖片稽核" in html
    assert "Hero" in html
    assert "images/0001_test.png" in html
