"""CLI ai-polish 測試。"""

from pathlib import Path

from sitespider.ai_polish_cli import main


def test_ai_polish_missing_report(tmp_path: Path):
    assert main([str(tmp_path / "missing")]) == 1


def test_ai_polish_list_providers(capsys):
    assert main(["--list-providers"]) == 0
    out = capsys.readouterr().out
    assert "openai" in out
    assert "gpt-5.4-mini" in out
    assert "minimax" in out
