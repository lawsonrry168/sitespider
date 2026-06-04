"""YAML 設定檔測試。"""

import pytest

yaml = pytest.importorskip("yaml")

from sitespider.site_config import load_site_config


def test_load_yaml_config(tmp_path):
    (tmp_path / "sitespider.yaml").write_text(
        "site_url: https://yaml.test/\nsitemap_path_prefixes: [demo]\n",
        encoding="utf-8",
    )
    cfg, path = load_site_config(tmp_path)
    assert path.name == "sitespider.yaml"
    assert cfg.site_url == "https://yaml.test/"
    assert cfg.sitemap_path_prefixes == ("demo/",)
