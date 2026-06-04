"""CI 範本產生測試。"""

from sitespider.init_ci import write_github_workflow


def test_write_github_workflow(tmp_path):
    out = tmp_path / ".github/workflows/sitespider.yml"
    write_github_workflow(out, site_root="web")
    text = out.read_text(encoding="utf-8")
    assert "sitespider --mode file --root web" in text
    assert "fail-on-issues" in text
