"""AI 文案 API 並發與配額行為。"""

from __future__ import annotations

from sitespider import server as srv


def test_acquire_ai_polish_running_is_exclusive():
    job_id = "job-ai-lock-test"
    srv._jobs.pop(job_id, None)
    try:
        assert srv._acquire_ai_polish_running(job_id) is True
        assert (srv._get_job(job_id).get("ai") or {}).get("status") == "running"
        assert srv._acquire_ai_polish_running(job_id) is False
    finally:
        srv._jobs.pop(job_id, None)
