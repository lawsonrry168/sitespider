from pathlib import Path

from sitespider.server_config import load_config_form, safe_project_path


def test_safe_project_path_blocks_traversal(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "examples" / "x.json"
    f.parent.mkdir(parents=True)
    f.write_text('{"site_url":"https://x/","mode":"http"}', encoding="utf-8")
    ok = safe_project_path("examples/x.json")
    assert ok == f.resolve()
    assert safe_project_path("../outside.json") is None


def test_load_config_form_123deal():
    root = Path(__file__).resolve().parents[1]
    p = root / "examples" / "123deal-sitespider.json"
    if not p.exists():
        return
    form = load_config_form(p)
    assert form["site_url"] == "https://123deal.com.hk/"
    assert form["gsc_inspect_max"] == 0
