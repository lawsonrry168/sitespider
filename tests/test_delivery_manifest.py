from pathlib import Path

from sitespider.delivery_manifest import DELIVERY_TILES, delivery_checklist, grouped_files_in_report


def test_delivery_tiles_use_current_labels():
    titles = {t for _f, t, _d in DELIVERY_TILES}
    assert "站內技術報告" in titles or any("站內" in t for t in titles)
    assert "SF 風格" not in titles


def test_grouped_manifest_order(tmp_path: Path):
    (tmp_path / "REPORT-zh.html").write_text("x", encoding="utf-8")
    (tmp_path / "dashboard.html").write_text("x", encoding="utf-8")
    groups = grouped_files_in_report(tmp_path)
    assert groups[0]["name"] == "客戶交付"
    assert groups[0]["files"][0]["file"] == "REPORT-zh.html"


def test_delivery_checklist_core(tmp_path: Path):
    (tmp_path / "REPORT-zh.html").write_text("x", encoding="utf-8")
    (tmp_path / "summary.json").write_text("{}", encoding="utf-8")
    (tmp_path / "issues.csv").write_text("x", encoding="utf-8")
    chk = delivery_checklist(tmp_path)
    assert chk["core_present"] == 3
    assert chk["core_total"] == 5
    assert not chk["core_complete"]


def test_delivery_checklist_images_meta(tmp_path: Path):
    img = tmp_path / "images"
    img.mkdir()
    (img / "a.png").write_bytes(b"x")
    chk = delivery_checklist(tmp_path)
    assert chk["images"]["downloaded_count"] == 1
    assert chk["images"]["zip_available"]
