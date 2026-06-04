"""任務歷史與 AI 狀態持久化。"""

from pathlib import Path

from sitespider.job_store import (
    append_job_record,
    clear_console_recent_jobs,
    list_job_history,
    load_hidden_job_ids,
    patch_job_ai,
)


def test_patch_job_ai(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    append_job_record(
        job_id="j1",
        status="done",
        site_url="https://example.com/",
        pages=3,
        report_dir_abs=str(tmp_path / "reports" / "j1"),
    )
    patch_job_ai("j1", {"status": "done", "model": "gpt-5.4-mini", "provider_name": "OpenAI"})
    rows = list_job_history()
    assert rows[0]["ai"]["status"] == "done"
    assert rows[0]["ai"]["model"] == "gpt-5.4-mini"


def test_clear_console_recent_jobs(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    report_dir = tmp_path / "reports" / "default" / "job1"
    report_dir.mkdir(parents=True)
    (report_dir / "crawl-report.json").write_text("{}", encoding="utf-8")
    append_job_record(
        job_id="job1",
        status="done",
        site_url="https://example.com/",
        report_dir_abs=str(report_dir),
    )
    assert list_job_history()
    clear_console_recent_jobs()
    assert list_job_history() == []
    assert "job1" in load_hidden_job_ids()
