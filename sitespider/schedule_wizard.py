"""Generate cron / CLI commands for scheduled crawls."""

from __future__ import annotations

import shlex
from pathlib import Path


def schedule_commands(
    *,
    config_path: str = "",
    site_root: str = ".",
    output_parent: str = "reports/scheduled",
    baseline: str = "",
    cwd: Path | None = None,
) -> dict[str, str]:
    root = (cwd or Path.cwd()).resolve()
    parts = ["sitespider", "schedule", "--output", output_parent]
    if config_path.strip():
        parts.extend(["--config", config_path.strip()])
    if site_root.strip() and site_root.strip() != ".":
        parts.extend(["--root", site_root.strip()])
    if baseline.strip():
        parts.extend(["--baseline", baseline.strip()])
    cmd = " ".join(shlex.quote(p) for p in parts)
    cron = f"0 3 * * 1 cd {shlex.quote(str(root))} && {cmd} >> .sitespider/schedule.log 2>&1"
    return {
        "command": cmd,
        "cron_weekly": cron,
        "note": "Pro 方案含排程比對；將 cron 貼到伺服器 crontab 或使用 GitHub Actions 定時執行。",
        "log_hint": str(root / ".sitespider" / "schedule.log"),
    }
