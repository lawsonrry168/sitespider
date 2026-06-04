"""爬取任務歷史（控制台用，持久化於 .sitespider/job-history.json）。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_HISTORY: Path | None = None
_MAX = 50


def history_path(base: Path | None = None) -> Path:
    global _HISTORY
    root = (base or Path.cwd()).resolve()
    return root / ".sitespider" / "job-history.json"


def _load(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def append_job_record(
    *,
    job_id: str,
    status: str,
    site_url: str = "",
    client_label: str = "",
    pages: int = 0,
    report_dir_abs: str = "",
    tenant_id: str = "",
    base: Path | None = None,
) -> None:
    path = history_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = _load(path)
    rows = [r for r in rows if r.get("job_id") != job_id]
    rows.insert(
        0,
        {
            "job_id": job_id,
            "status": status,
            "site_url": site_url,
            "client_label": client_label,
            "pages": pages,
            "report_dir_abs": report_dir_abs,
            "tenant_id": tenant_id,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    path.write_text(
        json.dumps(rows[:_MAX], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def list_job_history(limit: int = 20, base: Path | None = None) -> list[dict]:
    return _load(history_path(base))[:limit]


def hidden_jobs_path(base: Path | None = None) -> Path:
    root = (base or Path.cwd()).resolve()
    return root / ".sitespider" / "job-history-hidden.json"


def load_hidden_job_ids(base: Path | None = None) -> set[str]:
    path = hidden_jobs_path(base)
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {str(x) for x in data if x}
    except (json.JSONDecodeError, OSError):
        pass
    return set()


def save_hidden_job_ids(ids: set[str], *, base: Path | None = None) -> None:
    path = hidden_jobs_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(sorted(ids), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def iter_report_job_ids(base: Path | None = None) -> set[str]:
    """掃描 reports/ 下含 crawl-report.json 的任務 id。"""
    root = (base or Path.cwd()).resolve() / "reports"
    found: set[str] = set()
    if not root.is_dir():
        return found
    for p in root.iterdir():
        if not p.is_dir():
            continue
        if (p / "crawl-report.json").is_file():
            found.add(p.name)
            continue
        for child in p.iterdir():
            if child.is_dir() and (child / "crawl-report.json").is_file():
                found.add(child.name)
    return found


def clear_console_recent_jobs(*, base: Path | None = None) -> int:
    """清空 job-history.json，並將目前列表中的任務標為隱藏（不刪 reports/ 檔案）。"""
    root = base or Path.cwd()
    hidden = load_hidden_job_ids(root)
    before = len(hidden)
    for row in _load(history_path(root)):
        jid = str(row.get("job_id") or "").strip()
        if jid:
            hidden.add(jid)
    hidden |= iter_report_job_ids(root)
    save_hidden_job_ids(hidden, base=root)
    path = history_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[]\n", encoding="utf-8")
    return len(hidden) - before


def patch_job_ai(
    job_id: str,
    ai: dict,
    *,
    base: Path | None = None,
) -> None:
    """更新歷史紀錄中的 AI 狀態（ai-polish 完成後）。"""
    path = history_path(base)
    if not path.is_file():
        return
    rows = _load(path)
    changed = False
    for row in rows:
        if row.get("job_id") == job_id:
            row["ai"] = ai
            changed = True
            break
    if changed:
        path.write_text(
            json.dumps(rows[:_MAX], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
