"""share-report CLI。"""

import json
from pathlib import Path

from sitespider.share_report_cli import main


def test_share_report_cli(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    report = tmp_path / "demo-r"
    report.mkdir()
    (report / "crawl-report.json").write_text("{}", encoding="utf-8")
    rc = main([str(report), "--label", "CLI Test", "--ttl-days", "3"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Portal" in out or "portal" in out.lower()
    shares = json.loads((tmp_path / ".sitespider" / "report-shares.json").read_text())
    assert shares
