"""設定檔載入與合併測試。"""

import json
from argparse import Namespace
from pathlib import Path

from sitespider.site_config import (
    SiteConfig,
    load_site_config,
    merge_cli_with_config,
    write_default_config,
)
from sitespider.sitemap import _http_url_to_local_path


def test_load_site_config(tmp_path: Path):
    cfg_file = tmp_path / "sitespider.json"
    cfg_file.write_text(
        json.dumps(
            {
                "site_url": "https://prod.example/",
                "sitemap_path_prefixes": ["demo"],
                "crawl": {"max_pages": 42},
                "audit": {"thin_content_min_words": 100},
            }
        ),
        encoding="utf-8",
    )
    cfg, path = load_site_config(tmp_path)
    assert path == cfg_file
    assert cfg.site_url == "https://prod.example/"
    assert cfg.sitemap_path_prefixes == ("demo/",)
    assert cfg.max_pages == 42
    assert cfg.thin_content_min_words == 100


def test_merge_cli_without_config_sets_defaults():
    args = Namespace(
        mode=None,
        url=None,
        output=None,
        max_pages=None,
        max_depth=None,
        workers=None,
        lighthouse_max=None,
        thin_content_min=None,
        require_json_ld=False,
        lighthouse=False,
        check_external=False,
        no_robots=False,
        no_sitemap=False,
        xlsx=False,
        client_report=False,
        client_label=None,
    )
    merge_cli_with_config(args, None)
    assert args.thin_content_min == 300
    assert args.max_pages == 500
    assert args.workers == 4


def test_merge_cli_with_config():
    cfg = SiteConfig(max_pages=99, require_json_ld=True, export_xlsx=True)
    args = Namespace(
        mode=None,
        url=None,
        output=None,
        max_pages=None,
        max_depth=None,
        workers=None,
        lighthouse_max=None,
        thin_content_min=None,
        require_json_ld=False,
        lighthouse=False,
        check_external=False,
        no_robots=False,
        no_sitemap=False,
        xlsx=False,
    )
    merge_cli_with_config(args, cfg)
    assert args.max_pages == 99
    assert args.require_json_ld is True
    assert args.xlsx is True


def test_sitemap_path_prefix_strip(tmp_path: Path):
    (tmp_path / "index.html").write_text("<html></html>")
    fp = _http_url_to_local_path(
        "https://x.github.io/demo/index.html",
        tmp_path,
        path_prefixes=("demo/",),
    )
    assert fp is not None and fp.name == "index.html"


def test_write_default_config(tmp_path: Path):
    path = write_default_config(tmp_path / "sitespider.json", site_url="https://a.test/")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["site_url"] == "https://a.test/"
