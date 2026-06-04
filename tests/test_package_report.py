import zipfile
from pathlib import Path

from sitespider.package_report import (
    count_downloaded_images,
    package_images_dir,
    package_report_dir,
)


def test_package_report_dir(tmp_path: Path):
    report = tmp_path / "run1"
    report.mkdir()
    (report / "REPORT-zh.md").write_text("# hi", encoding="utf-8")
    (report / "priority_summary.md").write_text("x", encoding="utf-8")
    (report / "internal.csv").write_text("a", encoding="utf-8-sig")
    z = package_report_dir(report)
    assert z.is_file()
    with zipfile.ZipFile(z) as zf:
        names = zf.namelist()
    assert any("REPORT-zh.md" in n for n in names)


def test_package_report_includes_images_dir(tmp_path: Path):
    report = tmp_path / "run2"
    img = report / "images"
    img.mkdir(parents=True)
    (img / "0001_a.png").write_bytes(b"\x89PNG")
    (report / "REPORT-zh.md").write_text("# hi", encoding="utf-8")
    z = package_report_dir(report)
    with zipfile.ZipFile(z) as zf:
        names = zf.namelist()
    assert any(n.endswith("images/0001_a.png") for n in names)
    assert count_downloaded_images(report) == 1


def test_package_images_dir_only(tmp_path: Path):
    report = tmp_path / "run3"
    img = report / "images"
    img.mkdir(parents=True)
    (img / "pic.jpg").write_bytes(b"jpg")
    (report / "images-gallery.html").write_text("<html></html>", encoding="utf-8")
    z = package_images_dir(report)
    with zipfile.ZipFile(z) as zf:
        names = zf.namelist()
    assert any("images/pic.jpg" in n for n in names)
    assert any("images-gallery.html" in n for n in names)
