"""客戶只讀報告分享連結（Portal）。"""

from __future__ import annotations

import json
import secrets
import time
from pathlib import Path

# 客戶 Portal 允許的副檔名（不含 crawl-report.json 等敏感大檔）
PORTAL_SUFFIXES = frozenset({".html", ".md", ".txt", ".draft"})

DEFAULT_TTL_DAYS = 30


def shares_path(base: Path | None = None) -> Path:
    root = (base or Path.cwd()).resolve()
    return root / ".sitespider" / "report-shares.json"


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def create_report_share(
    *,
    tenant_id: str,
    job_id: str,
    report_dir: Path,
    label: str = "",
    ttl_days: int = DEFAULT_TTL_DAYS,
    base: Path | None = None,
) -> dict:
    """建立分享 token，回傳 {token, share_path, expires_at}。"""
    report_dir = report_dir.resolve()
    if not (report_dir / "crawl-report.json").is_file():
        raise FileNotFoundError(f"找不到報告：{report_dir}")

    token = secrets.token_urlsafe(24)
    now = time.time()
    expires = now + ttl_days * 86400
    rec = {
        "tenant_id": tenant_id,
        "job_id": job_id,
        "report_dir": str(report_dir),
        "label": label or job_id,
        "created_at": now,
        "expires_at": expires,
    }
    path = shares_path(base)
    db = _load(path)
    db[token] = rec
    _save(path, db)
    return {
        "token": token,
        "share_path": f"/portal/{token}",
        "expires_at": expires,
        "ttl_days": ttl_days,
    }


def resolve_share(token: str, base: Path | None = None) -> dict | None:
    if not token or len(token) < 16:
        return None
    rec = _load(shares_path(base)).get(token)
    if not rec:
        return None
    if float(rec.get("expires_at") or 0) < time.time():
        return None
    report_dir = Path(rec["report_dir"])
    if not report_dir.is_dir():
        return None
    return rec


def find_share_for_report(report_dir: Path, base: Path | None = None) -> dict | None:
    """回傳指向此報告目錄的有效分享（含 token）。"""
    target = report_dir.resolve()
    now = time.time()
    best: tuple[float, str, dict] | None = None
    for token, rec in _load(shares_path(base)).items():
        if float(rec.get("expires_at") or 0) < now:
            continue
        try:
            if Path(rec.get("report_dir", "")).resolve() != target:
                continue
        except OSError:
            continue
        created = float(rec.get("created_at") or 0)
        if best is None or created > best[0]:
            best = (created, token, rec)
    if not best:
        return None
    _, token, rec = best
    return {"token": token, "share_path": f"/portal/{token}", **rec}


def portal_file_path(report_dir: Path, rel: str) -> Path | None:
    """解析 Portal 可讀取的檔案路徑。"""
    rel = (rel or "").strip().lstrip("/")
    if not rel or ".." in rel.split("/"):
        return None
    report_dir = report_dir.resolve()
    fp = (report_dir / rel).resolve()
    try:
        fp.relative_to(report_dir)
    except ValueError:
        return None
    if not fp.is_file():
        return None
    if fp.name == "crawl-report.json":
        return None
    if fp.suffix.lower() not in PORTAL_SUFFIXES:
        return None
    return fp


def portal_manifest(report_dir: Path, label: str, *, expires_at: float | None = None) -> dict:
    """客戶 Portal 導覽用檔案列表。"""
    from sitespider.delivery_manifest import files_in_report, grouped_files_in_report

    report_dir = report_dir.resolve()
    files = files_in_report(report_dir)
    out: dict = {"label": label, "files": files, "groups": grouped_files_in_report(report_dir)}
    if expires_at:
        out["expires_at"] = expires_at
    return out
