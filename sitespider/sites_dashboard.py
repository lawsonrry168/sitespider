"""Agency multi-site dashboard data."""

from __future__ import annotations

import json
from pathlib import Path

from sitespider.job_store import list_job_history


def _read_summary(report_dir: Path) -> dict:
    p = report_dir / "summary.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _is_report_dir(path: Path) -> bool:
    return path.is_dir() and (
        (path / "REPORT-zh.html").is_file()
        or (path / "summary.json").is_file()
        or (path / "crawl-report.json").is_file()
    )


def _resolve_report_dir(
    report_abs: str,
    *,
    job_id: str,
    tenant_id: str,
    reports_root: Path,
) -> Path | None:
    if report_abs:
        p = Path(report_abs)
        if p.is_dir():
            return p.resolve()
        # 舊 job-history 可能指向已搬遷的絕對路徑：改以 job_id 在本機 reports 下找
        if p.name and (reports_root / p.parent.name / p.name).is_dir():
            candidate = reports_root / p.parent.name / p.name
            if _is_report_dir(candidate):
                return candidate.resolve()
    tid = tenant_id or "default"
    for candidate in (
        reports_root / tid / job_id,
        reports_root / job_id,
    ):
        if _is_report_dir(candidate):
            return candidate.resolve()
    return None


def _site_row(tenant_id: str, job_id: str, report_dir: Path, *, extra: dict | None = None) -> dict:
    extra = extra or {}
    summary = _read_summary(report_dir)
    return {
        "tenant_id": tenant_id,
        "job_id": job_id,
        "site_url": str(extra.get("site_url") or summary.get("site_label") or "").strip(),
        "client_label": str(extra.get("client_label") or "").strip(),
        "pages": int(extra.get("pages") or summary.get("url_count") or 0),
        "health_score": summary.get("health_score"),
        "health_grade_label": summary.get("health_grade_label"),
        "finished_at": str(extra.get("finished_at") or ""),
        "report_path": str(report_dir),
    }


def _discover_from_filesystem(
    reports_root: Path,
    *,
    tenant_filter: str | None,
    all_tenants: bool,
    seen: set[tuple[str, str]],
    sites: list[dict],
) -> None:
    if not reports_root.is_dir():
        return
    for entry in sorted(reports_root.iterdir(), key=lambda p: p.name):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if _is_report_dir(entry):
            tid = "demo" if entry.name in ("123deal-smoke", "demo") else "legacy"
            if not all_tenants:
                if tenant_filter and tenant_filter not in (tid, "default", entry.name):
                    continue
            key = (tid, entry.name)
            if key in seen:
                continue
            seen.add(key)
            sites.append(_site_row(tid, entry.name, entry))
            continue
        if not _is_report_dir(entry):
            for job_dir in sorted(entry.iterdir(), reverse=True):
                if not job_dir.is_dir() or not _is_report_dir(job_dir):
                    continue
                tid = entry.name
                if not all_tenants and tenant_filter and tid != tenant_filter:
                    continue
                key = (tid, job_dir.name)
                if key in seen:
                    continue
                seen.add(key)
                sites.append(_site_row(tid, job_dir.name, job_dir))


def sites_dashboard_json(
    *,
    tenant_filter: str | None = None,
    all_tenants: bool = False,
    limit: int = 40,
    base: Path | None = None,
) -> dict:
    root = (base or Path.cwd()).resolve()
    reports_root = root / "reports"
    sites: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for row in list_job_history(limit=limit * 2, base=base):
        job_id = str(row.get("job_id") or "")
        if not job_id:
            continue
        tid = str(row.get("tenant_id") or "").strip()
        report_dir = _resolve_report_dir(
            str(row.get("report_dir_abs") or ""),
            job_id=job_id,
            tenant_id=tid,
            reports_root=reports_root,
        )
        if report_dir is None:
            continue
        rel_tid = tid
        try:
            rel_tid = report_dir.relative_to(reports_root).parts[0]
        except ValueError:
            rel_tid = tid or "default"
        if not all_tenants and tenant_filter and rel_tid != tenant_filter:
            try:
                if report_dir.name != tenant_filter and rel_tid != tenant_filter:
                    continue
            except (ValueError, TypeError):
                continue
        key = (rel_tid, job_id)
        if key in seen:
            continue
        seen.add(key)
        sites.append(
            _site_row(
                rel_tid,
                job_id,
                report_dir,
                extra={
                    "site_url": row.get("site_url"),
                    "client_label": row.get("client_label"),
                    "pages": row.get("pages"),
                    "finished_at": row.get("finished_at"),
                },
            )
        )

    _discover_from_filesystem(
        reports_root,
        tenant_filter=tenant_filter,
        all_tenants=all_tenants,
        seen=seen,
        sites=sites,
    )

    sites.sort(key=lambda s: (s.get("finished_at") or "", s.get("job_id") or ""), reverse=True)
    return {"sites": sites[:limit], "count": len(sites)}
