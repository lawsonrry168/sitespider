from pathlib import Path

from sitespider.list_crawl import load_url_list


def test_load_url_list_absolute(tmp_path: Path):
    f = tmp_path / "urls.txt"
    f.write_text("https://a.com/1\n# comment\nhttps://a.com/2\n", encoding="utf-8")
    assert load_url_list(f) == ["https://a.com/1", "https://a.com/2"]


def test_load_url_list_relative(tmp_path: Path):
    f = tmp_path / "urls.txt"
    f.write_text("/page-a\npage-b\n", encoding="utf-8")
    urls = load_url_list(f, base_url="https://example.com/")
    assert urls[0] == "https://example.com/page-a"
