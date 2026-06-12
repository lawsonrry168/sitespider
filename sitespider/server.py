#!/usr/bin/env python3
"""
SiteSpider Web 控制台 — 深度限制與爬取選項的 GUI。
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import uuid
from html import escape as html_escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sitespider.crawler import CrawlConfig, SeoCrawler
from sitespider.issues import ISSUE_LABELS
from sitespider.lighthouse_runner import lighthouse_available
from sitespider.report import write_all_reports
from sitespider.report_xlsx import xlsx_available
from sitespider import __version__
from sitespider.site_config import load_site_config
from sitespider.branding import Branding, branding_for_plan
from sitespider.custom_presets import CUSTOM_PRESET_RULES, rules_from_payload, rules_from_preset_ids
from sitespider.job_store import (
    append_job_record,
    clear_console_recent_jobs,
    list_job_history,
    load_hidden_job_ids,
    patch_job_ai,
)
from sitespider.server_config import (
    list_example_configs,
    load_config_form,
    parse_uploaded_config,
    safe_project_path,
)

from sitespider.paths import default_reports_dir, package_dir, user_data_dir

PACKAGE_DIR = package_dir()
UI_DIR = PACKAGE_DIR / "ui"

# Static assets under /ui/ (favicon, brand mark, fonts, etc.)
UI_STATIC_TYPES: dict[str, str] = {
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
}

# 控制台 HTML 頁（/guide、/guide/、/guide.html 皆對應同一檔）
CONSOLE_HTML_ROUTES: dict[str, str] = {
    "/": "dashboard.html",
    "/dashboard": "dashboard.html",
    "/pricing": "pricing.html",
    "/about": "about.html",
    "/guide": "guide.html",
    "/help": "guide.html",
    "/contact": "contact.html",
    "/branding": "branding.html",
    "/workspace": "workspace.html",
    "/ai": "ai.html",
    "/admin": "admin.html",
    "/sites": "sites.html",
    "/demo": "demo.html",
    "/checkout/success": "checkout_success.html",
    "/checkout-success": "checkout_success.html",
}
def _default_root() -> Path:
    raw = os.environ.get("SITESPIDER_DATA_DIR", "").strip()
    if raw:
        reports = Path(raw) / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        return reports
    if getattr(sys, "frozen", False):
        return default_reports_dir()
    return Path.cwd()


DEFAULT_ROOT = _default_root()


def resolve_console_html(path: str) -> str | None:
    """將請求路徑對應到 ui/ 下的 HTML 檔名；無則 None。"""
    p = (path or "/").rstrip("/") or "/"
    if p.endswith(".html"):
        p = p[:-5] or "/"
    return CONSOLE_HTML_ROUTES.get(p)

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _get_job(job_id: str) -> dict | None:
    with _jobs_lock:
        return _jobs.get(job_id)


def _resolve_job_by_id(job_id: str) -> dict | None:
    """
    解析任務：記憶體 job → job-history → 本機 reports/（含 CLI／範例報告）。
    回傳的 dict 保證含 report_dir / report_dir_abs（若報告存在）。
    """
    jid = str(job_id or "").strip()
    if not jid:
        return None

    live = _get_job(jid)
    if live:
        out = dict(live)
        out["job_id"] = jid
        raw = str(out.get("report_dir_abs") or out.get("report_dir") or "").strip()
        if raw:
            rp = Path(raw)
            if rp.is_dir():
                out["report_dir"] = str(rp.resolve())
                out["report_dir_abs"] = out["report_dir"]
        # 進行中／匯出中：記憶體任務即可輪詢（尚未寫入 crawl-report.json）
        if out.get("status") in ("running", "exporting"):
            return out

    job: dict | None = None
    if live:
        job = dict(live)
    else:
        for row in list_job_history(50):
            if str(row.get("job_id") or "") == jid:
                job = dict(row)
                job["status"] = row.get("status") or "done"
                break

    reports_root = _reports_root()

    def _finalize(found: dict, report_path: Path) -> dict:
        rp = report_path.resolve()
        found["job_id"] = jid
        found["report_dir"] = str(rp)
        found["report_dir_abs"] = str(rp)
        if not found.get("status"):
            found["status"] = "done"
        return found

    if job:
        raw = str(job.get("report_dir_abs") or job.get("report_dir") or "").strip()
        if raw:
            rp = Path(raw)
            if rp.is_dir() and (rp / "crawl-report.json").is_file():
                return _finalize(job, rp)
            if rp.is_dir() and job.get("status") == "error":
                out_err = dict(job)
                out_err["report_dir"] = str(rp.resolve())
                out_err["report_dir_abs"] = out_err["report_dir"]
                out_err["job_id"] = jid
                return out_err
        for candidate in (reports_root / "default" / jid, reports_root / jid):
            if candidate.is_dir() and (candidate / "crawl-report.json").is_file():
                return _finalize(job, candidate)

    lookup_ids = ["123deal-smoke", jid] if jid == "demo" else [jid]
    seen_lookup: set[str] = set()
    for lookup in lookup_ids:
        if lookup in seen_lookup:
            continue
        seen_lookup.add(lookup)
        for candidate in (reports_root / "default" / lookup, reports_root / lookup):
            if candidate.is_dir() and (candidate / "crawl-report.json").is_file():
                return _finalize({"job_id": jid}, candidate)
        if reports_root.is_dir():
            for tenant_dir in reports_root.iterdir():
                if not tenant_dir.is_dir():
                    continue
                candidate = tenant_dir / lookup
                if candidate.is_dir() and (candidate / "crawl-report.json").is_file():
                    row = {"job_id": jid, "tenant_id": tenant_dir.name}
                    return _finalize(row, candidate)
    return None


def _job_report_dir(job: dict) -> Path:
    """任務對應報告目錄（呼叫前應已通過 _resolve_job_by_id）。"""
    raw = str(job.get("report_dir_abs") or job.get("report_dir") or "").strip()
    if not raw:
        raise FileNotFoundError("report_dir missing")
    return Path(raw).resolve()


def _set_job(job_id: str, data: dict) -> None:
    with _jobs_lock:
        _jobs[job_id] = data


def _patch_job(job_id: str, patch: dict) -> None:
    with _jobs_lock:
        cur = dict(_jobs.get(job_id) or {})
        cur.update(patch)
        _jobs[job_id] = cur


def _acquire_ai_polish_running(job_id: str) -> bool:
    """原子標記 AI 文案進行中；若已在執行則回傳 False。"""
    with _jobs_lock:
        cur = dict(_jobs.get(job_id) or {})
        if (cur.get("ai") or {}).get("status") == "running":
            return False
        ai = dict(cur.get("ai") or {})
        ai.update({"status": "running", "written": [], "errors": []})
        cur["ai"] = ai
        _jobs[job_id] = cur
        return True


def _enrich_job_history(rows: list[dict]) -> list[dict]:
    """合併記憶體 job 與報告目錄 ai-polish-meta.json。"""
    reports_root = _reports_root()
    hidden = load_hidden_job_ids(Path.cwd())
    out: list[dict] = []
    for row in list(rows):
        r = dict(row)
        jid = str(r.get("job_id") or "")
        if jid and jid in hidden:
            continue
        report_dir = str(r.get("report_dir_abs") or "").strip()
        if jid:
            if report_dir and not Path(report_dir).is_dir():
                report_dir = ""
            if not report_dir:
                # 舊紀錄可能保存了已搬遷的絕對路徑，嘗試在目前 reports/ 目錄重新定位
                for candidate in (reports_root / "default" / jid, reports_root / jid):
                    if candidate.is_dir() and (candidate / "crawl-report.json").is_file():
                        report_dir = str(candidate.resolve())
                        r["report_dir_abs"] = report_dir
                        break
        # 若此歷史任務沒有對應可用報告，直接略過，避免 UI 顯示可點卻必定失敗
        if report_dir:
            rp = Path(report_dir)
            if not (rp / "crawl-report.json").is_file():
                continue
        else:
            continue
        live = _get_job(jid) if jid else None
        if live and live.get("ai"):
            r["ai"] = live["ai"]
        elif not r.get("ai"):
            meta_path = Path(report_dir) / "ai-polish-meta.json"
            if report_dir and meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    from sitespider.ai_settings_store import classify_ai_run_status

                    written = meta.get("written") or []
                    errors = meta.get("errors") or []
                    r["ai"] = {
                        "status": classify_ai_run_status(
                            written=written,
                            errors=errors,
                            ok=meta.get("ok"),
                        ),
                        "provider_id": meta.get("provider_id"),
                        "provider_name": meta.get("provider_name"),
                        "model": meta.get("model"),
                        "written": written,
                        "errors": errors,
                    }
                except (json.JSONDecodeError, OSError):
                    pass
        out.append(r)
    # 補齊只存在於 reports/ 但不在 job-history 的本機報告（例如 CLI 直接輸出）
    known = {str(x.get("job_id") or "") for x in out}
    for p in sorted(reports_root.iterdir(), key=lambda x: x.name, reverse=True) if reports_root.is_dir() else []:
        if not p.is_dir():
            continue
        # 扁平報告：reports/123deal-smoke/
        if (p / "crawl-report.json").is_file() and p.name not in known and p.name not in hidden:
            out.append(
                {
                    "job_id": p.name,
                    "status": "done",
                    "site_url": "",
                    "client_label": "",
                    "pages": 0,
                    "report_dir_abs": str(p.resolve()),
                    "finished_at": "",
                }
            )
            known.add(p.name)
        # 多租戶報告：reports/{tenant}/{job_id}/
        for child in p.iterdir() if p.is_dir() else []:
            if not child.is_dir():
                continue
            if not (child / "crawl-report.json").is_file():
                continue
            if child.name in known or child.name in hidden:
                continue
            out.append(
                {
                    "job_id": child.name,
                    "status": "done",
                    "site_url": "",
                    "client_label": "",
                    "pages": 0,
                    "report_dir_abs": str(child.resolve()),
                    "tenant_id": p.name,
                    "finished_at": "",
                }
            )
            known.add(child.name)
    return out


def _run_ai_polish_async(
    job_id: str,
    report_dir: Path,
    *,
    label: str,
    api_key: str | None,
    model: str | None,
    provider_id: str | None = None,
    base_url: str | None = None,
    tenant_id: str = "default",
) -> None:
    _patch_job(
        job_id,
        {
            "ai": {
                "status": "running",
                "written": [],
                "errors": [],
                "provider_id": provider_id,
                "model": model,
            }
        },
    )
    try:
        from sitespider.ai_exports import run_ai_polish
        from sitespider.report_load import load_report_json

        report = load_report_json(report_dir / "crawl-report.json")
        result = run_ai_polish(
            report,
            report_dir,
            site_label=label,
            api_key=api_key,
            model=model,
            provider_id=provider_id,
            base_url=base_url,
        )
        from sitespider.ai_settings_store import classify_ai_run_status

        written = result.get("written") or []
        errors = result.get("errors") or []
        ai_view = {
            "status": classify_ai_run_status(
                written=written,
                errors=errors,
                ok=result.get("ok"),
            ),
            "written": written,
            "errors": errors,
            "model": result.get("model"),
            "provider_id": result.get("provider_id") or provider_id,
            "provider_name": result.get("provider_name"),
            "error": result.get("error"),
        }
        _patch_job(job_id, {"ai": ai_view})
        patch_job_ai(job_id, ai_view)
        if ai_view.get("status") == "done" and not (result.get("errors")):
            from sitespider.usage import record_ai_polish

            record_ai_polish(tenant_id)
    except Exception as e:
        ai_view = {
            "status": "error",
            "error": str(e),
            "written": [],
            "errors": [str(e)],
        }
        _patch_job(job_id, {"ai": ai_view})
        patch_job_ai(job_id, ai_view)


def _resolve_plan_id(ctx, payload: dict) -> str:
    from sitespider.plan_resolve import resolve_effective_plan_id

    return resolve_effective_plan_id(
        ctx.tenant_id,
        ctx_plan_id=ctx.plan_id,
        client_plan_id=payload.get("plan_id"),
    )


def _branding_for_crawl(tenant_id: str, plan_id: str, payload: dict, site_cfg) -> Branding:
    from sitespider.plans import get_plan
    from sitespider.tenant_branding import get_tenant_branding

    plan = get_plan(plan_id)
    brand_raw: dict = {}
    if isinstance(payload.get("branding"), dict):
        brand_raw = dict(payload["branding"])
    server_brand = get_tenant_branding(tenant_id)
    for key in ("consultant_name", "logo_url", "accent_color"):
        if not brand_raw.get(key) and server_brand.get(key):
            brand_raw[key] = server_brand[key]
    if site_cfg and site_cfg.branding and isinstance(site_cfg.branding, dict):
        for key in ("consultant_name", "logo_url", "accent_color"):
            if not brand_raw.get(key) and site_cfg.branding.get(key):
                brand_raw[key] = site_cfg.branding[key]
    return branding_for_plan(plan, brand_raw or None)


def _enrich_job_for_client(job: dict) -> dict:
    """補齊 report_files 與 AI 狀態，避免 UI 因 running 誤鎖已產出的交付檔。"""
    out = dict(job)
    raw = str(out.get("report_dir_abs") or out.get("report_dir") or "").strip()
    if not raw:
        return out
    rd = Path(raw)
    if not rd.is_dir():
        return out
    on_disk = {p.name for p in rd.iterdir() if p.is_file()}
    merged = set(out.get("report_files") or [])
    merged.update(on_disk)
    out["report_files"] = sorted(merged)
    ai = dict(out.get("ai") or {})
    if ai.get("status") == "running":
        meta_path = rd / "ai-polish-meta.json"
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                from sitespider.ai_settings_store import classify_ai_run_status

                written = meta.get("written") or []
                errors = meta.get("errors") or []
                ai.update(
                    {
                        "status": classify_ai_run_status(
                            written=written, errors=errors, ok=meta.get("ok")
                        ),
                        "written": written,
                        "errors": errors,
                        "provider_id": meta.get("provider_id") or ai.get("provider_id"),
                        "model": meta.get("model") or ai.get("model"),
                    }
                )
            except (json.JSONDecodeError, OSError):
                pass
        elif "ai-hub.html" in on_disk or "ai-faq-cms.html" in on_disk:
            ai["status"] = "partial"
            ai.setdefault("written", [f for f in ("ai-hub.html", "ai-faq-cms.html") if f in on_disk])
    out["ai"] = ai
    return out


def _job_public_view(job: dict) -> dict:
    """給瀏覽器輪詢用，不含巨大 crawl JSON（避免控制字元導致 parse 失敗）。"""
    view = {k: v for k, v in job.items() if k != "report_json"}
    return _enrich_job_for_client(view)


def _reports_root() -> Path:
    return (Path.cwd() / "reports").resolve()


def _resolve_reports_file(rel: str) -> Path | None:
    """解析 /reports/… 路徑；支援 demo 別名與 default/{job_id}/file 回退。"""
    reports_root = _reports_root()
    rel = (rel or "").strip().lstrip("/")
    if not rel or rel == "demo":
        rel = "123deal-smoke"
    elif rel.startswith("demo/"):
        rel = "123deal-smoke/" + rel[5:].lstrip("/")

    variants: list[str] = [rel]
    parts = rel.split("/")
    if len(parts) >= 3:
        variants.append(f"{parts[1]}/{'/'.join(parts[2:])}")
    if len(parts) >= 2 and parts[0] not in ("123deal-smoke",):
        variants.append("/".join(parts[1:]))

    seen: set[str] = set()
    for variant in variants:
        if variant in seen:
            continue
        seen.add(variant)
        fp = (reports_root / variant).resolve()
        try:
            fp.relative_to(reports_root)
        except ValueError:
            continue
        if fp.is_file():
            return fp

    if rel.rstrip("/") in ("123deal-smoke", "demo"):
        idx = reports_root / "123deal-smoke" / "REPORT-zh.html"
        if idx.is_file():
            return idx
    return None


def _report_dir(tenant_id: str, job_id: str) -> Path:
    """任務報告目錄（必先建立，避免寫入 snapshot / Lighthouse 失敗）。"""
    out = (Path.cwd() / "reports" / tenant_id / job_id).resolve()
    out.mkdir(parents=True, exist_ok=True)
    return out


def _write_crawl_snapshot(out_dir: Path, payload: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "crawl-config.snapshot.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _run_crawl(job_id: str, payload: dict) -> None:
    tenant_id = str(payload.get("tenant_id") or "default")
    plan_id = str(payload.get("plan_id") or "pro")
    site_root = Path(payload.get("root", str(DEFAULT_ROOT))).resolve()
    mode = payload.get("mode", "file")
    start_url = payload.get("url", "http://localhost:8080/")

    explicit_cfg = Path(payload["config_path"]).expanduser() if payload.get("config_path") else None
    site_cfg, _ = load_site_config(site_root, config_path=explicit_cfg)
    prefixes = site_cfg.sitemap_path_prefixes if site_cfg else ()
    if site_cfg and site_cfg.site_url and mode == "http":
        start_url = site_cfg.site_url

    if mode == "file":
        start_url = (site_root / "index.html").as_uri()

    preset_ids = payload.get("custom_preset_ids") or []
    custom_rules = list(rules_from_preset_ids(preset_ids)) + list(
        rules_from_payload(payload.get("custom_extractions"))
    )
    if not custom_rules and site_cfg and site_cfg.custom_extractions:
        from sitespider.custom_extract import ExtractionRule

        for raw in site_cfg.custom_extractions:
            if isinstance(raw, dict):
                r = ExtractionRule.from_dict(raw)
                if r:
                    custom_rules.append(r)

    brand_raw = payload.get("branding")
    if not brand_raw and site_cfg and site_cfg.branding:
        brand_raw = site_cfg.branding
    branding = _branding_for_crawl(tenant_id, plan_id, payload, site_cfg)
    out_dir = _report_dir(tenant_id, job_id)

    config = CrawlConfig(
        max_pages=int(payload.get("max_pages", site_cfg.max_pages if site_cfg and site_cfg.max_pages else 500)),
        max_depth=int(payload.get("max_depth", site_cfg.max_depth if site_cfg and site_cfg.max_depth else 10)),
        workers=int(payload.get("workers", site_cfg.workers if site_cfg and site_cfg.workers else 4)),
        respect_robots=bool(payload.get("respect_robots", True)),
        use_sitemap=bool(payload.get("use_sitemap", True)),
        check_external=bool(payload.get("check_external", False)),
        run_lighthouse=bool(payload.get("lighthouse", False)),
        lighthouse_max=int(payload.get("lighthouse_max", 5)),
        require_json_ld=bool(payload.get("require_json_ld", False))
        or bool(site_cfg and site_cfg.require_json_ld),
        thin_content_min_words=int(
            payload.get(
                "thin_content_min",
                site_cfg.thin_content_min_words if site_cfg and site_cfg.thin_content_min_words is not None else 300,
            )
        ),
        sitemap_path_prefixes=prefixes,
        exclude_path_prefixes=tuple(payload.get("exclude_paths") or ())
        or (site_cfg.exclude_path_prefixes if site_cfg else ()),
        defer_link_checks=bool(payload.get("defer_link_checks", True)),
        render_javascript=bool(payload.get("render_js", False))
        or bool(site_cfg and site_cfg.render_javascript),
        render_wait_until=str(
            payload.get("render_wait")
            or (site_cfg.render_wait_until if site_cfg and site_cfg.render_wait_until else "domcontentloaded")
        ),
        strip_query_string=bool(payload.get("strip_query", False))
        or bool(site_cfg and site_cfg.strip_query_string),
        gsc_site_url=payload.get("gsc_site_url")
        or (site_cfg.gsc_site_url if site_cfg else None)
        or (site_cfg.site_url if site_cfg else None),
        gsc_inspect_max=int(
            payload.get(
                "gsc_inspect_max",
                site_cfg.gsc_inspect_max if site_cfg and site_cfg.gsc_inspect_max is not None else 0,
            )
        ),
        custom_extractions=tuple(custom_rules),
        download_images=bool(payload.get("download_images", False)),
        max_images_download=int(payload.get("max_images_download", 300)),
        fetch_policy=str(payload.get("fetch_policy") or "http"),
        cache_responses=bool(payload.get("cache_responses", False)),
        cache_dir=str(out_dir / ".cache") if payload.get("cache_responses") else None,
        resume_crawl=bool(payload.get("resume_crawl", False)),
        adaptive_extractions=bool(payload.get("adaptive_extract", False)),
        stealth_headers=bool(payload.get("stealth_headers", False)),
        use_scrapling=bool(payload.get("scrapling", False)),
        crawldir=str(out_dir / ".crawl")
        if payload.get("checkpoint") or payload.get("resume_crawl")
        else None,
    )

    export_xlsx = bool(payload.get("xlsx")) or bool(site_cfg and site_cfg.export_xlsx)
    client_report = bool(payload.get("client_report")) or bool(
        site_cfg and site_cfg.client_report
    )
    client_label = payload.get("client_label") or (
        site_cfg.client_label if site_cfg else None
    )
    if export_xlsx and not xlsx_available():
        export_xlsx = False

    _patch_job(
        job_id,
        {
            "report_dir": str(out_dir),
            "report_dir_abs": str(out_dir.resolve()),
            "tenant_id": tenant_id,
            "plan_id": plan_id,
            "progress": {"done": 0, "total": 1, "current": "啟動中…"},
        },
    )
    try:
        _write_crawl_snapshot(out_dir, payload)
    except OSError:
        pass
    crawler_holder: dict[str, object] = {"crawler": None}

    def progress(done: int, total: int, url: str) -> None:
        live = {"issue_hits": 0, "issue_types": 0}
        cr = crawler_holder.get("crawler")
        if cr is not None:
            pages = getattr(getattr(cr, "report", None), "pages", None) or {}
            live["issue_hits"] = sum(len(p.issues) for p in pages.values())
            codes: set[str] = set()
            for p in pages.values():
                codes.update(p.issues)
            live["issue_types"] = len(codes)
        _set_job(
            job_id,
            {
                **_get_job(job_id),
                "progress": {"done": done, "total": max(total, done), "current": url},
                "live": live,
            },
        )

    try:
        crawler = SeoCrawler(
            start_url,
            mode=mode,
            site_root=site_root,
            config=config,
            on_progress=progress,
            lighthouse_out=out_dir / "lighthouse",
            crawldir=Path(config.crawldir) if config.crawldir else None,
        )
        crawler_holder["crawler"] = crawler
        report = crawler.crawl()
        _write_crawl_snapshot(out_dir, payload)
        from sitespider.report_tiers import (
            ExportOptions,
            export_fast_tier,
            export_pro_tier,
            export_standard_tier,
        )

        export_opts = ExportOptions(
            site_root=site_root,
            export_xlsx=export_xlsx,
            client_report=client_report,
            client_report_label=client_label,
            branding=branding,
            plan_id=plan_id,
            tenant_id=tenant_id,
        )
        fast_written = export_fast_tier(report, out_dir, export_opts)
        summary_extra: dict = {}
        summary_path = out_dir / "summary.json"
        if summary_path.is_file():
            try:
                summary_extra = json.loads(summary_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

        base_summary = {
            "pages": len(report.pages),
            "blocked": len(report.blocked_urls),
            "issues": report.summary_issues(),
            "duration": (report.finished_at or 0) - report.started_at,
            "gsc_inspected": len(report.gsc_rich_inspections or {}),
            "gsc_enabled": config.gsc_inspect_max > 0,
            "health_score": summary_extra.get("health_score"),
            "health_grade_label": summary_extra.get("health_grade_label"),
        }

        def _finish_exports() -> None:
            try:
                std = export_standard_tier(report, out_dir, export_opts)
                pro = export_pro_tier(report, out_dir, export_opts)
                all_written = list(dict.fromkeys(fast_written + std + pro))
                from sitespider.usage import record_crawl

                record_crawl(tenant_id, pages=len(report.pages), base=site_root)
                notify_cfg = payload.get("notify") if isinstance(payload.get("notify"), dict) else {}
                if notify_cfg:
                    from sitespider.notifications import notify_crawl_complete

                    notify_crawl_complete(
                        tenant_id=tenant_id,
                        job_id=job_id,
                        site_url=start_url,
                        pages=len(report.pages),
                        report_dir=str(out_dir),
                        package_url=f"/api/job/{job_id}/package.zip",
                        notify=notify_cfg,
                    )
                append_job_record(
                    job_id=job_id,
                    status="done",
                    site_url=start_url,
                    client_label=client_label or "",
                    pages=len(report.pages),
                    report_dir_abs=str(out_dir),
                    tenant_id=tenant_id,
                    base=site_root,
                )
                _set_job(
                    job_id,
                    {
                        "status": "done",
                        "export_phase": "complete",
                        "progress": {
                            "done": len(report.pages),
                            "total": len(report.pages),
                            "current": "",
                        },
                        "report_dir": str(out_dir),
                        "report_dir_abs": str(out_dir.resolve()),
                        "report_files": all_written,
                        "summary": base_summary,
                        "package_url": f"/api/job/{job_id}/package.zip",
                        "tenant_id": tenant_id,
                        "plan_id": plan_id,
                    },
                )
                # 後端保證版：爬取完成後自動觸發 AI 文案（避免前端時機遺漏）
                if bool(payload.get("auto_ai_polish")):
                    try:
                        from sitespider.ai_settings_store import (
                            get_tenant_ai_settings,
                            merge_ai_into_payload,
                        )
                        from sitespider.plans import get_plan
                        from sitespider.usage import check_ai_polish_quota

                        ai_payload = merge_ai_into_payload(
                            dict(payload),
                            get_tenant_ai_settings(tenant_id),
                        )
                        plan = get_plan(str(plan_id))
                        if plan.has("ai_polish") and _acquire_ai_polish_running(job_id):
                            ai_quota = check_ai_polish_quota(tenant_id, plan)
                            if ai_quota.allowed:
                                threading.Thread(
                                    target=_run_ai_polish_async,
                                    args=(job_id, out_dir),
                                    kwargs={
                                        "label": client_label or job_id,
                                        "api_key": str(ai_payload.get("ai_api_key") or "").strip()
                                        or None,
                                        "model": str(ai_payload.get("ai_model") or "").strip() or None,
                                        "provider_id": str(ai_payload.get("ai_provider") or "").strip()
                                        or None,
                                        "base_url": str(ai_payload.get("ai_base_url") or "").strip()
                                        or None,
                                        "tenant_id": tenant_id,
                                    },
                                    daemon=True,
                                ).start()
                            else:
                                _patch_job(
                                    job_id,
                                    {
                                        "ai": {
                                            "status": "error",
                                            "error": ai_quota.reason,
                                            "errors": [ai_quota.reason],
                                            "written": [],
                                        }
                                    },
                                )
                    except Exception as exc:
                        _patch_job(
                            job_id,
                            {
                                "ai": {
                                    "status": "error",
                                    "error": str(exc),
                                    "errors": [str(exc)],
                                    "written": [],
                                }
                            },
                        )
            except Exception as exc:
                _set_job(
                    job_id,
                    {
                        "status": "error",
                        "error": str(exc),
                        "tenant_id": tenant_id,
                        "report_files": fast_written,
                    },
                )

        _set_job(
            job_id,
            {
                "status": "exporting",
                "export_phase": "standard",
                "progress": {
                    "done": len(report.pages),
                    "total": len(report.pages),
                    "current": "產生完整報告…",
                },
                "report_dir": str(out_dir),
                "report_dir_abs": str(out_dir.resolve()),
                "report_files": fast_written,
                "summary": base_summary,
                "package_url": f"/api/job/{job_id}/package.zip",
                "tenant_id": tenant_id,
                "plan_id": plan_id,
            },
        )
        threading.Thread(target=_finish_exports, daemon=True).start()
    except Exception as e:
        try:
            _write_crawl_snapshot(out_dir, payload)
        except OSError:
            pass
        _set_job(job_id, {"status": "error", "error": str(e), "tenant_id": tenant_id})


class CrawlerHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _api_info_payload(self) -> dict:
        cfg, cfg_path = load_site_config(DEFAULT_ROOT)
        try:
            from sitespider.js_render import playwright_available

            render_js_available = playwright_available()
        except ImportError:
            render_js_available = False
        try:
            from sitespider.optional_scrapling import scrapling_available

            scrapling_ok = scrapling_available()
        except ImportError:
            scrapling_ok = False
        return {
            "lighthouse_available": lighthouse_available(),
            "xlsx_available": xlsx_available(),
            "render_js_available": render_js_available,
            "scrapling_available": scrapling_ok,
            "crawl_engine": {
                "fetch_policies": ["http", "auto", "js"],
                "checkpoint": True,
                "response_cache": True,
            },
            "default_root": str(DEFAULT_ROOT),
            "config_path": str(cfg_path) if cfg_path else None,
            "site_url": cfg.site_url if cfg else None,
            "version": __version__,
            "issue_labels": ISSUE_LABELS,
            "example_configs": list_example_configs(),
            "delivery_note": (
                "無 Search Console 授權亦可完成站內稽核；"
                "GSC 僅在客戶已驗證資源且 inspect_max>0 時啟用。"
            ),
            "custom_presets": [
                {"id": k, "label": v.get("name", k)}
                for k, v in CUSTOM_PRESET_RULES.items()
            ],
            "ai_configured": __import__(
                "sitespider.ai_client", fromlist=["ai_configured"]
            ).ai_configured(),
            "ai_providers": __import__(
                "sitespider.ai_providers", fromlist=["providers_public_json"]
            ).providers_public_json(),
            "ai_provider_default": os.environ.get("SITESPIDER_AI_PROVIDER", "openai"),
            "stripe_configured": __import__(
                "sitespider.stripe_checkout",
                fromlist=["stripe_configured"],
            ).stripe_configured(),
            "stripe_ai_bonus_configured": __import__(
                "sitespider.stripe_checkout",
                fromlist=["ai_bonus_checkout_configured"],
            ).ai_bonus_checkout_configured(),
            "ai_bonus_pack_size": __import__(
                "sitespider.stripe_checkout",
                fromlist=["ai_bonus_pack_size"],
            ).ai_bonus_pack_size(),
            "dev_skip_quota": not __import__(
                "sitespider.usage", fromlist=["quota_checks_enabled"]
            ).quota_checks_enabled(),
            "strict_plan": __import__(
                "sitespider.plan_resolve", fromlist=["strict_plan_enforcement"]
            ).strict_plan_enforcement(),
            "client_plan_selectable": __import__(
                "sitespider.plan_resolve", fromlist=["client_plan_selectable"]
            ).client_plan_selectable(),
        }

    def _send_api_info_browser_page(self, data: dict) -> None:
        """瀏覽器直接開 /api/info 時顯示深色說明頁，而非裸 JSON。"""
        from html import escape

        raw = json.dumps(data, ensure_ascii=False, indent=2)
        body = escape(raw)
        raw_js = json.dumps(raw, ensure_ascii=False)
        page = f"""<!DOCTYPE html>
<html lang="zh-TW"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SiteSpider API · /api/info</title>
<link rel="stylesheet" href="/ui/tokens.css">
<link rel="stylesheet" href="/ui/report-pages.css">
<link rel="stylesheet" href="/ui/report-theme-unified.css">
<script>
(function(){{try{{
document.documentElement.setAttribute("data-theme",localStorage.getItem("sitespider-theme")||"dark");
}}catch(e){{document.documentElement.setAttribute("data-theme","dark");}}}})();
</script>
<style>
.api-info-page{{max-width:56rem;margin:0 auto;padding:1.5rem 1.25rem 3rem}}
.api-info-page h1{{font-family:var(--font-display);font-size:1.35rem;margin:0 0 .5rem}}
.api-info-page p{{color:var(--muted);font-size:.9rem;line-height:1.6}}
.api-info-toolbar{{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;margin:1rem 0}}
.api-info-toolbar a,.api-info-toolbar button{{
  font-family:var(--font-display);font-size:.8rem;padding:.4rem .75rem;border-radius:999px;
  border:1px solid var(--border);background:var(--card);color:var(--link);cursor:pointer;text-decoration:none}}
.api-info-toolbar a:hover,.api-info-toolbar button:hover{{background:var(--accent-dim)}}
#api-json{{
  display:block;width:100%;min-height:50vh;padding:1rem;box-sizing:border-box;
  font-family:var(--font-mono);font-size:.75rem;line-height:1.55;
  background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:12px;
  white-space:pre;overflow:auto}}
#api-json.pretty{{white-space:pre-wrap;word-break:break-word}}
</style></head>
<body class="report-body">
<div class="api-info-page">
  <h1>/api/info</h1>
  <p>這是給控制台 JavaScript 用的 JSON API。若要操作介面請開啟
  <a href="/">爬取中心</a>。程式呼叫請用 <code>Accept: application/json</code>。</p>
  <div class="api-info-toolbar">
    <button type="button" class="theme-toggle" title="切換主題">◑</button>
    <label><input type="checkbox" id="pretty"> 美化排版</label>
    <a href="/api/info" id="raw-json">下載 JSON</a>
    <a href="/">← 爬取中心</a>
  </div>
  <pre id="api-json" class="pretty">{body}</pre>
</div>
<script src="/ui/report-theme-toggle.js"></script>
<script>
(function(){{
  var pre=document.getElementById("api-json");
  var raw={raw_js};
  var cb=document.getElementById("pretty");
  function render(){{ pre.textContent=raw; pre.classList.toggle("pretty",cb.checked); }}
  cb.addEventListener("change",render); render();
}})();
</script>
</body></html>"""
        encoded = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str, *, no_cache: bool = False) -> None:
        if not path.exists():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        if no_cache:
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(data)

    def _send_markdown_html(self, path: Path, *, title: str | None = None) -> None:
        if not path.is_file():
            self.send_error(404)
            return
        from sitespider.markdown_view import markdown_file_page

        html_body = markdown_file_page(path, title=title).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html_body)))
        self.end_headers()
        self.wfile.write(html_body)

    def _send_download(self, path: Path, filename: str, content_type: str) -> None:
        if not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def _auth_header(self) -> str | None:
        return self.headers.get("Authorization")

    def _inject_report_nav_helpers(self, html: str, fp: Path) -> str:
        """舊版報告 HTML：修正爬取中心連結並注入 nav-back.js。"""
        if "report-topbar" not in html:
            return html
        from sitespider.report_theme import console_home_href

        home = console_home_href(fp)
        chunks: list[str] = []
        if "window.__SS_CONSOLE_HOME" not in html:
            chunks.append(f"<script>window.__SS_CONSOLE_HOME={json.dumps(home)};</script>")
        if "nav-back.js" not in html:
            chunks.append('<script src="/ui/nav-back.js"></script>')
        if home != "/":
            h_esc = html_escape(home, quote=True)
            for pattern in (
                r'(<a\b[^>]*\bss-console-home\b[^>]*\bhref=")[^"]*(")',
                r'(<a\b[^>]*\breport-brand-home\b[^>]*\bhref=")[^"]*(")',
            ):
                html = re.sub(pattern, rf"\1{h_esc}\2", html)
        if not chunks:
            return html
        tag = "\n".join(chunks)
        if "</body>" in html:
            return html.replace("</body>", tag + "\n</body>", 1)
        return html + tag

    def _patch_report_html_meta(self, html: str, fp: Path) -> str:
        if fp.suffix != ".html":
            return html
        try:
            from sitespider.ai_meta_display import patch_ai_html_model_line

            return patch_ai_html_model_line(html, fp.parent)
        except Exception:
            return html

    def _serve_report_file(self, fp: Path) -> None:
        """依副檔名回傳報告檔（HTML / MD / CSV …）。"""
        if fp.name == "REPORT-zh.md":
            html_alt = fp.with_suffix(".html")
            if html_alt.is_file():
                return self._send_file(html_alt, "text/html; charset=utf-8", no_cache=True)
        if fp.suffix == ".html":
            try:
                from sitespider.report_theme import (
                    ensure_report_zh_files,
                    locate_report_job_dir,
                    patch_report_html_theme,
                    patch_report_nav,
                )

                job_dir = locate_report_job_dir(fp)
                if job_dir is not None:
                    ensure_report_zh_files(job_dir)
                raw = fp.read_text(encoding="utf-8")
                raw = patch_report_html_theme(raw)
                raw = patch_report_nav(raw, fp)
                html_body = self._patch_report_html_meta(
                    self._inject_report_nav_helpers(raw, fp),
                    fp,
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html_body)))
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                self.wfile.write(html_body)
                return
            except OSError:
                return self._send_file(fp, "text/html; charset=utf-8", no_cache=True)
        if fp.suffix == ".md":
            title = "交付導覽" if fp.name == "REPORT-zh.md" else fp.stem
            return self._send_markdown_html(fp, title=title)
        if fp.suffix == ".json":
            return self._send_file(fp, "application/json; charset=utf-8")
        if fp.suffix == ".csv":
            return self._send_file(fp, "text/csv; charset=utf-8")
        if fp.suffix in (".txt", ".draft"):
            return self._send_file(fp, "text/plain; charset=utf-8")
        return self.send_error(404)

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        console_page = resolve_console_html(path)
        if console_page:
            return self._send_file(
                UI_DIR / console_page, "text/html; charset=utf-8", no_cache=True
            )

        if path.startswith("/ui/"):
            rel = path[4:].lstrip("/")
            if ".." in rel or not rel:
                return self.send_error(403)
            fp = UI_DIR / rel
            if fp.is_file():
                ctype = UI_STATIC_TYPES.get(fp.suffix.lower())
                if ctype:
                    return self._send_file(fp, ctype, no_cache=True)
            return self.send_error(404)

        if path == "/api/site":
            from sitespider.site_info import public_site_info

            return self._send_json(public_site_info())

        if path.startswith("/portal/"):
            from sitespider.report_share import portal_file_path, resolve_share

            parts = [p for p in path.split("/") if p]
            if len(parts) < 2 or parts[0] != "portal":
                return self.send_error(404)
            token = parts[1]
            if len(parts) == 2:
                return self._send_file(UI_DIR / "portal.html", "text/html; charset=utf-8", no_cache=True)
            rec = resolve_share(token)
            if not rec:
                return self.send_error(404)
            report_dir = Path(rec["report_dir"])
            rel = "/".join(parts[2:])
            fp = portal_file_path(report_dir, rel)
            if not fp:
                return self.send_error(404)
            if fp.name == "REPORT-zh.md":
                html_alt = fp.with_suffix(".html")
                if html_alt.is_file():
                    return self._send_file(html_alt, "text/html; charset=utf-8")
            if fp.suffix == ".html":
                return self._send_file(fp, "text/html; charset=utf-8")
            if fp.suffix == ".md":
                title = "交付導覽" if fp.name == "REPORT-zh.md" else fp.stem
                return self._send_markdown_html(fp, title=title)
            return self._send_file(fp, "text/plain; charset=utf-8")

        if path.startswith("/api/portal/"):
            from sitespider.report_share import portal_manifest, resolve_share

            parts = [p for p in path.split("/") if p]
            if len(parts) < 3 or parts[0] != "api" or parts[1] != "portal":
                return self.send_error(404)
            token = parts[2]
            rec = resolve_share(token)
            if not rec:
                return self._send_json({"error": "連結無效或已過期"}, 404)
            if len(parts) >= 4 and parts[3] == "manifest":
                return self._send_json(
                    portal_manifest(
                        Path(rec["report_dir"]),
                        rec.get("label") or rec.get("job_id", ""),
                        expires_at=rec.get("expires_at"),
                    )
                )
            return self.send_error(404)

        if path == "/api/plans":
            from sitespider.plans import plans_public_json

            return self._send_json({"plans": plans_public_json()})

        if path == "/api/usage":
            from sitespider.plans import get_plan
            from sitespider.plan_resolve import resolve_effective_plan_id
            from sitespider.usage import tenant_usage

            qs = parse_qs(urlparse(self.path).query)
            tid = (qs.get("tenant_id") or ["default"])[0]
            try:
                from sitespider.auth import require_tenant

                ctx = require_tenant(self._auth_header(), tid)
                tid = ctx.tenant_id
                plan_id = resolve_effective_plan_id(
                    tid,
                    ctx_plan_id=ctx.plan_id,
                    client_plan_id=(qs.get("plan_id") or [None])[0],
                )
            except PermissionError:
                return self._send_json({"error": "unauthorized"}, 401)
            plan = get_plan(plan_id)
            u = tenant_usage(tid)
            from sitespider.usage import usage_limits_json

            return self._send_json(
                {
                    "tenant_id": tid,
                    "plan_id": plan.id,
                    "usage": u,
                    "limits": usage_limits_json(plan, u),
                    "features": sorted(plan.features),
                }
            )

        if path == "/api/info":
            info = self._api_info_payload()
            accept = (self.headers.get("Accept") or "").lower()
            if "text/html" in accept and accept.strip().startswith("text/html"):
                return self._send_api_info_browser_page(info)
            return self._send_json(info)

        if path == "/api/jobs":
            return self._send_json({"jobs": _enrich_job_history(list_job_history(25))})

        if path == "/api/ai/settings":
            from sitespider.ai_settings_store import get_tenant_ai_settings
            from sitespider.auth import require_tenant

            qs = parse_qs(urlparse(self.path).query)
            tid = (qs.get("tenant_id") or ["default"])[0]
            try:
                ctx = require_tenant(self._auth_header(), tid)
                tid = ctx.tenant_id
            except PermissionError as e:
                return self._send_json({"error": str(e)}, 401)
            return self._send_json({"tenant_id": tid, "settings": get_tenant_ai_settings(tid)})

        if path == "/api/branding":
            from sitespider.auth import require_tenant
            from sitespider.plans import get_plan
            from sitespider.plan_resolve import resolve_effective_plan_id
            from sitespider.tenant_branding import get_tenant_branding

            qs = parse_qs(urlparse(self.path).query)
            tid = (qs.get("tenant_id") or ["default"])[0]
            try:
                ctx = require_tenant(self._auth_header(), tid)
                tid = ctx.tenant_id
            except PermissionError as e:
                return self._send_json({"error": str(e)}, 401)
            plan_id = resolve_effective_plan_id(
                tid, ctx_plan_id=ctx.plan_id, client_plan_id=(qs.get("plan_id") or [None])[0]
            )
            plan = get_plan(plan_id)
            brand = get_tenant_branding(tid)
            return self._send_json(
                {
                    "tenant_id": tid,
                    "plan_id": plan.id,
                    "branding": brand,
                    "can_edit": plan.has("white_label") or plan.has("branding_lite"),
                    "white_label": plan.has("white_label"),
                    "branding_lite": plan.has("branding_lite"),
                }
            )

        if path == "/api/schedule/wizard":
            from sitespider.auth import require_tenant
            from sitespider.plans import get_plan
            from sitespider.plan_resolve import resolve_effective_plan_id
            from sitespider.schedule_wizard import schedule_commands

            qs = parse_qs(urlparse(self.path).query)
            tid = (qs.get("tenant_id") or ["default"])[0]
            try:
                ctx = require_tenant(self._auth_header(), tid)
                tid = ctx.tenant_id
            except PermissionError as e:
                return self._send_json({"error": str(e)}, 401)
            plan_id = resolve_effective_plan_id(
                tid, ctx_plan_id=ctx.plan_id, client_plan_id=(qs.get("plan_id") or [None])[0]
            )
            if not get_plan(plan_id).has("schedule"):
                return self._send_json({"error": "排程爬取需 Pro 或以上方案"}, 403)
            cfg = (qs.get("config") or [""])[0]
            baseline = (qs.get("baseline") or [""])[0]
            root = (qs.get("root") or ["."])[0]
            out = (qs.get("output") or ["reports/scheduled"])[0]
            return self._send_json(
                schedule_commands(
                    config_path=cfg,
                    site_root=root,
                    output_parent=out,
                    baseline=baseline,
                )
            )

        if path == "/api/sites-dashboard":
            from sitespider.auth import require_tenant
            from sitespider.plans import get_plan
            from sitespider.plan_resolve import resolve_effective_plan_id
            from sitespider.sites_dashboard import sites_dashboard_json

            qs = parse_qs(urlparse(self.path).query)
            tid = (qs.get("tenant_id") or ["default"])[0]
            try:
                ctx = require_tenant(self._auth_header(), tid)
                tid = ctx.tenant_id
            except PermissionError as e:
                return self._send_json({"error": str(e)}, 401)
            plan_id = resolve_effective_plan_id(
                tid, ctx_plan_id=ctx.plan_id, client_plan_id=(qs.get("plan_id") or [None])[0]
            )
            plan = get_plan(plan_id)
            all_tenants = (qs.get("all_tenants") or ["0"])[0] in ("1", "true", "yes")
            if all_tenants and not plan.has("multi_tenant"):
                return self._send_json(
                    {"error": "跨租戶檢視需 Agency 方案；取消「顯示全部租戶」可檢視本站紀錄"},
                    403,
                )
            return self._send_json(
                sites_dashboard_json(
                    tenant_filter=None if all_tenants else tid,
                    all_tenants=all_tenants,
                    limit=int((qs.get("limit") or ["40"])[0]),
                )
            )

        if path == "/api/admin/tenants":
            from sitespider.admin_api import list_tenants_dashboard, verify_admin

            if not verify_admin(self._auth_header()):
                return self._send_json({"error": "admin unauthorized"}, 403)
            return self._send_json(list_tenants_dashboard())

        if path == "/api/examples":
            return self._send_json({"examples": list_example_configs()})

        if path.startswith("/api/config"):
            qs = parse_qs(urlparse(self.path).query)
            rel = (qs.get("path") or [""])[0]
            safe = safe_project_path(rel) if rel else None
            if not safe:
                return self._send_json({"error": "invalid or missing path"}, 400)
            try:
                return self._send_json(load_config_form(safe))
            except Exception as e:
                return self._send_json({"error": str(e)}, 400)

        if path.startswith("/api/job/"):
            parts = [p for p in path.split("/") if p]
            # /api/job/{id} or /api/job/{id}/package.zip
            if len(parts) >= 3 and parts[0] == "api" and parts[1] == "job":
                job_id = parts[2]
                job = _resolve_job_by_id(job_id)
                if not job:
                    return self._send_json(
                        {
                            "error": "找不到任務或報告目錄。請確認爬取已完成，且本機 reports/ 內仍有該任務資料夾。",
                            "job_id": job_id,
                        },
                        404,
                    )
                if len(parts) >= 4 and parts[3] == "delivery-checklist":
                    if job.get("status") != "done":
                        return self._send_json({"error": "report not ready"}, 400)
                    from sitespider.delivery_manifest import delivery_checklist

                    return self._send_json(delivery_checklist(_job_report_dir(job)))
                if len(parts) >= 4 and parts[3] == "package.zip":
                    if job.get("status") != "done":
                        return self._send_json({"error": "report not ready"}, 400)
                    from sitespider.package_report import package_report_dir

                    report_dir = _job_report_dir(job)
                    zip_path = report_dir / f"{job_id}-delivery.zip"
                    try:
                        package_report_dir(report_dir, zip_path)
                    except (OSError, ValueError) as e:
                        return self._send_json({"error": str(e)}, 400)
                    return self._send_download(
                        zip_path,
                        f"sitespider-{job_id}-delivery.zip",
                        "application/zip",
                    )
                if len(parts) >= 4 and parts[3] == "images.zip":
                    if job.get("status") != "done":
                        return self._send_json({"error": "report not ready"}, 400)
                    from sitespider.package_report import package_images_dir

                    report_dir = _job_report_dir(job)
                    zip_path = report_dir / f"{job_id}-images.zip"
                    try:
                        package_images_dir(report_dir, zip_path)
                    except (OSError, ValueError) as e:
                        return self._send_json({"error": str(e)}, 400)
                    return self._send_download(
                        zip_path,
                        f"sitespider-{job_id}-images.zip",
                        "application/zip",
                    )
                if len(parts) >= 4 and parts[3] == "client-report.html":
                    if job.get("status") != "done":
                        return self._send_json({"error": "report not ready"}, 400)
                    from sitespider.standalone_client_report import (
                        STANDALONE_FILENAME,
                        export_standalone_client_html,
                    )

                    report_dir = _job_report_dir(job)
                    fp = report_dir / STANDALONE_FILENAME
                    try:
                        if not fp.is_file():
                            export_standalone_client_html(
                                report_dir,
                                site_label=job.get("client_label"),
                            )
                    except (OSError, ValueError, FileNotFoundError) as e:
                        return self._send_json({"error": str(e)}, 400)
                    return self._send_download(
                        fp,
                        f"sitespider-{job_id}-{STANDALONE_FILENAME}",
                        "text/html; charset=utf-8",
                    )
                return self._send_json(_job_public_view(job))

        if path.startswith("/api/validate-url"):
            qs = parse_qs(urlparse(self.path).query)
            from sitespider.url_sanitize import sanitize_start_url, start_url_looks_invalid

            raw = sanitize_start_url((qs.get("url") or [""])[0].strip())
            if not raw:
                return self._send_json({"ok": False, "error": "缺少 url"}, 400)
            bad = start_url_looks_invalid(raw)
            if bad:
                return self._send_json({"ok": False, "error": bad})
            parsed = urlparse(raw)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                return self._send_json({"ok": False, "error": "請使用 http(s):// 完整 URL"})
            import urllib.error
            import urllib.request

            try:
                req = urllib.request.Request(
                    raw,
                    method="HEAD",
                    headers={"User-Agent": f"SiteSpider/{__version__}"},
                )
                with urllib.request.urlopen(req, timeout=12) as resp:
                    return self._send_json(
                        {"ok": True, "status": resp.status, "final_url": resp.geturl()}
                    )
            except urllib.error.HTTPError as e:
                return self._send_json(
                    {
                        "ok": True,
                        "status": e.code,
                        "final_url": e.geturl() if hasattr(e, "geturl") else raw,
                        "note": "伺服器回應錯誤狀態，但仍可嘗試爬取",
                    }
                )
            except Exception as e:
                return self._send_json({"ok": False, "error": str(e)[:240]})

        if path == "/api/demo":
            from sitespider.demo_info import demo_info_json

            return self._send_json(demo_info_json())

        if path.startswith("/reports/"):
            rel = path[len("/reports/") :]
            fp = _resolve_reports_file(rel)
            if not fp:
                return self.send_error(404)
            return self._serve_report_file(fp)

        return self.send_error(404)

    def do_POST(self) -> None:
        api_path = urlparse(self.path).path

        if api_path == "/api/ai/settings":
            from sitespider.ai_settings_store import set_tenant_ai_settings
            from sitespider.auth import require_tenant

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                return self._send_json({"error": "invalid json"}, 400)
            try:
                ctx = require_tenant(self._auth_header(), payload.get("tenant_id"))
            except PermissionError as e:
                return self._send_json({"error": str(e)}, 401)
            data = payload.get("settings") if isinstance(payload.get("settings"), dict) else payload
            saved = set_tenant_ai_settings(ctx.tenant_id, data)
            return self._send_json({"ok": True, "tenant_id": ctx.tenant_id, "settings": saved})

        if api_path == "/api/branding":
            from sitespider.auth import require_tenant
            from sitespider.plans import get_plan
            from sitespider.tenant_branding import set_tenant_branding

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                return self._send_json({"error": "invalid json"}, 400)
            try:
                ctx = require_tenant(self._auth_header(), payload.get("tenant_id"))
            except PermissionError as e:
                return self._send_json({"error": str(e)}, 401)
            plan_id = _resolve_plan_id(ctx, payload)
            plan = get_plan(plan_id)
            if not plan.has("white_label") and not plan.has("branding_lite"):
                return self._send_json(
                    {"error": "報告品牌需 Starter（署名）或 Agency（完整白標）方案"},
                    403,
                )
            data = payload.get("branding") if isinstance(payload.get("branding"), dict) else payload
            brand_in = {
                "consultant_name": data.get("consultant_name", ""),
                "logo_url": data.get("logo_url", "") if plan.has("white_label") else "",
                "accent_color": data.get("accent_color", "#6ec9a0")
                if plan.has("white_label")
                else "#6ec9a0",
            }
            saved = set_tenant_branding(ctx.tenant_id, brand_in)
            return self._send_json({"ok": True, "branding": saved, "plan_id": plan.id})

        if api_path == "/api/compare":
            from sitespider.auth import require_tenant
            from sitespider.compare import compare_files, export_compare_html
            from sitespider.plans import get_plan

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                return self._send_json({"error": "invalid json"}, 400)
            try:
                ctx = require_tenant(self._auth_header(), payload.get("tenant_id"))
            except PermissionError as e:
                return self._send_json({"error": str(e)}, 401)
            plan = get_plan(_resolve_plan_id(ctx, payload))
            if not plan.has("compare"):
                return self._send_json({"error": "報告比對需 Free 或以上方案"}, 403)
            baseline_job = str(payload.get("baseline_job_id") or "").strip()
            current_job = str(payload.get("current_job_id") or "").strip()
            if not baseline_job or not current_job:
                return self._send_json({"error": "baseline_job_id 與 current_job_id 必填"}, 400)
            tid = ctx.tenant_id
            base_dir = Path.cwd() / "reports" / tid
            base_json = base_dir / baseline_job / "crawl-report.json"
            cur_json = base_dir / current_job / "crawl-report.json"
            if not base_json.is_file() or not cur_json.is_file():
                return self._send_json({"error": "找不到 crawl-report.json（請確認 job_id）"}, 404)
            result = compare_files(base_json, cur_json)
            out_html = base_dir / current_job / "compare-report.html"
            export_compare_html(
                result,
                out_html,
                baseline_label=baseline_job,
                current_label=current_job,
            )
            return self._send_json(
                {
                    "ok": True,
                    "compare_path": str(out_html),
                    "compare_url": f"/reports/{tid}/{current_job}/compare-report.html",
                    "has_regressions": result.has_regressions,
                    "summary": result.summary_lines(),
                }
            )

        if api_path in ("/api/jobs/clear", "/api/jobs"):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            if api_path == "/api/jobs/clear":
                action = "clear"
            else:
                try:
                    payload = json.loads(body) if body else {}
                except json.JSONDecodeError:
                    return self._send_json({"error": "invalid json"}, 400)
                action = str(payload.get("action") or "").strip()
            if action == "clear":
                try:
                    n = clear_console_recent_jobs(base=Path.cwd())
                    return self._send_json({"ok": True, "cleared": n})
                except OSError as e:
                    return self._send_json({"error": str(e)[:240]}, 500)
            if api_path == "/api/jobs":
                return self._send_json({"error": "unknown action"}, 400)
            return self._send_json({"error": "invalid json"}, 400)

        if api_path == "/api/usage/reset":
            from sitespider.usage import quota_checks_enabled, reset_tenant_usage

            allow = (
                not quota_checks_enabled()
                or os.environ.get("SITESPIDER_ALLOW_USAGE_RESET", "").strip().lower()
                in ("1", "true", "yes")
            )
            if not allow:
                return self._send_json(
                    {"error": "僅本機開發模式可重設用量（請以 SITESPIDER_SKIP_QUOTA=1 啟動 UI）"},
                    403,
                )
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                payload = {}
            tid = str(payload.get("tenant_id") or "default").strip() or "default"
            reset_tenant_usage(tid)
            return self._send_json({"ok": True, "tenant_id": tid})

        if api_path == "/api/config/upload":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                return self._send_json(parse_uploaded_config(body))
            except Exception as e:
                return self._send_json({"error": str(e)}, 400)

        if api_path == "/api/stripe/webhook":
            import os

            from sitespider.billing_stripe import handle_stripe_event, verify_stripe_signature

            secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            sig = self.headers.get("Stripe-Signature", "")
            if secret and not verify_stripe_signature(raw, sig, secret):
                return self._send_json({"error": "invalid signature"}, 400)
            try:
                event = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return self._send_json({"error": "invalid json"}, 400)
            msg = handle_stripe_event(event)
            return self._send_json({"ok": True, "message": msg})

        if api_path == "/api/billing/checkout":
            import os

            from sitespider.stripe_checkout import create_checkout_session, stripe_configured

            if not stripe_configured():
                return self._send_json({"error": "Stripe not configured"}, 503)
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                return self._send_json({"error": "invalid json"}, 400)
            host = self.headers.get("Host", "127.0.0.1:8765")
            scheme = "https" if os.environ.get("SITESPIDER_PUBLIC_HTTPS") else "http"
            base = f"{scheme}://{host}"
            result = create_checkout_session(
                plan_id=str(payload.get("plan_id") or "pro"),
                tenant_id=str(payload.get("tenant_id") or "").strip() or f"tenant-{uuid.uuid4().hex[:8]}",
                success_url=str(payload.get("success_url") or f"{base}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}"),
                cancel_url=str(payload.get("cancel_url") or f"{base}/pricing"),
                customer_email=str(payload.get("email") or ""),
            )
            status = 200 if result.get("url") else 400
            return self._send_json(result, status)

        if api_path == "/api/billing/ai-bonus-checkout":
            import os

            from sitespider.auth import require_tenant
            from sitespider.plans import get_plan
            from sitespider.stripe_checkout import (
                ai_bonus_checkout_configured,
                create_ai_bonus_checkout_session,
            )

            if not ai_bonus_checkout_configured():
                return self._send_json({"error": "AI 加購未設定（STRIPE_PRICE_AI_BONUS）"}, 503)
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                return self._send_json({"error": "invalid json"}, 400)
            try:
                ctx = require_tenant(self._auth_header(), payload.get("tenant_id"))
            except PermissionError as e:
                return self._send_json({"error": str(e)}, 401)
            plan_id = _resolve_plan_id(ctx, payload)
            if not get_plan(plan_id).allows_ai_bonus_purchase():
                return self._send_json(
                    {"error": "AI 加購僅適用 Pro / Agency 方案"},
                    403,
                )
            host = self.headers.get("Host", "127.0.0.1:8765")
            scheme = "https" if os.environ.get("SITESPIDER_PUBLIC_HTTPS") else "http"
            base = f"{scheme}://{host}"
            result = create_ai_bonus_checkout_session(
                tenant_id=ctx.tenant_id,
                success_url=str(
                    payload.get("success_url")
                    or f"{base}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}&ai_bonus=1"
                ),
                cancel_url=str(payload.get("cancel_url") or f"{base}/pricing"),
                customer_email=str(payload.get("email") or ""),
            )
            status = 200 if result.get("url") else 400
            return self._send_json(result, status)

        if api_path == "/api/billing/portal":
            from sitespider.auth import require_tenant
            from sitespider.billing_onboarding import create_portal_session
            from sitespider.billing_stripe import load_tenants
            from sitespider.stripe_checkout import stripe_configured

            if not stripe_configured():
                return self._send_json({"error": "Stripe not configured"}, 503)
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                return self._send_json({"error": "invalid json"}, 400)
            try:
                ctx = require_tenant(self._auth_header(), payload.get("tenant_id"))
            except PermissionError as e:
                return self._send_json({"error": str(e)}, 401)
            rec = load_tenants().get(ctx.tenant_id) or {}
            customer = str(rec.get("stripe_customer") or "")
            if not customer:
                return self._send_json({"error": "此租戶尚無 Stripe 客戶 ID（請先完成訂閱）"}, 400)
            result = create_portal_session(stripe_customer_id=customer)
            status = 200 if result.get("url") else 400
            return self._send_json(result, status)

        if api_path.startswith("/api/admin/tenant/") and api_path.endswith("/resend-welcome"):
            from sitespider.admin_api import verify_admin
            from sitespider.api_keys import issue_tenant_key
            from sitespider.billing_onboarding import send_welcome_email
            from sitespider.billing_stripe import load_tenants

            if not verify_admin(self._auth_header()):
                return self._send_json({"error": "admin unauthorized"}, 403)
            parts = api_path.strip("/").split("/")
            tenant_id = parts[3] if len(parts) >= 4 else ""
            rec = load_tenants().get(tenant_id) or {}
            email = str(rec.get("email") or "")
            if not tenant_id or not email:
                return self._send_json({"error": "missing tenant or email"}, 400)
            plan_id = str(rec.get("plan_id") or "pro")
            api_key = issue_tenant_key(tenant_id, plan_id, base=None)
            ok = send_welcome_email(
                tenant_id=tenant_id,
                plan_id=plan_id,
                api_key=api_key,
                to_email=email,
            )
            return self._send_json({"ok": ok, "tenant_id": tenant_id, "email": email})

        if api_path.startswith("/api/admin/tenant/") and api_path.endswith("/rotate-key"):
            from sitespider.admin_api import rotate_tenant_api_key, verify_admin

            if not verify_admin(self._auth_header()):
                return self._send_json({"error": "admin unauthorized"}, 403)
            parts = api_path.strip("/").split("/")
            tenant_id = parts[3] if len(parts) >= 4 else ""
            if not tenant_id:
                return self._send_json({"error": "missing tenant_id"}, 400)
            return self._send_json(rotate_tenant_api_key(tenant_id))

        if api_path.startswith("/api/admin/tenant/") and api_path.endswith("/plan"):
            from sitespider.admin_api import set_plan, verify_admin

            if not verify_admin(self._auth_header()):
                return self._send_json({"error": "admin unauthorized"}, 403)
            parts = api_path.strip("/").split("/")
            tenant_id = parts[3] if len(parts) >= 4 else ""
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                return self._send_json({"error": "invalid json"}, 400)
            if not tenant_id:
                return self._send_json({"error": "missing tenant_id"}, 400)
            try:
                return self._send_json(
                    set_plan(tenant_id, str(payload.get("plan_id") or ""))
                )
            except ValueError as e:
                return self._send_json({"error": str(e)}, 400)

        if api_path.startswith("/api/admin/tenant/") and api_path.endswith("/ai-bonus"):
            from sitespider.admin_api import grant_ai_polish_bonus, verify_admin

            if not verify_admin(self._auth_header()):
                return self._send_json({"error": "admin unauthorized"}, 403)
            parts = api_path.strip("/").split("/")
            tenant_id = parts[3] if len(parts) >= 4 else ""
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                return self._send_json({"error": "invalid json"}, 400)
            if not tenant_id:
                return self._send_json({"error": "missing tenant_id"}, 400)
            try:
                extra = int(payload.get("extra") or payload.get("pack_size") or 0)
                return self._send_json(grant_ai_polish_bonus(tenant_id, extra))
            except ValueError as e:
                return self._send_json({"error": str(e)}, 400)

        if api_path.startswith("/api/job/") and api_path.endswith("/ai-polish"):
            parts = [p for p in api_path.split("/") if p]
            if len(parts) < 4:
                return self._send_json({"error": "invalid path"}, 400)
            job_id = parts[2]
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                return self._send_json({"error": "invalid json"}, 400)
            job = _get_job(job_id)
            from sitespider.auth import require_tenant

            try:
                ctx = require_tenant(self._auth_header(), payload.get("tenant_id"))
            except PermissionError as e:
                return self._send_json({"error": str(e)}, 401)
            tenant = ctx.tenant_id
            if job and job.get("report_dir"):
                report_dir = Path(job["report_dir"])
            else:
                candidates = [
                    Path.cwd() / "reports" / tenant / job_id,
                    Path.cwd() / "reports" / job_id,
                    Path.cwd() / "reports" / "123deal-smoke" if job_id == "demo" else Path(""),
                ]
                report_dir = candidates[0]
                for c in candidates:
                    if c and c.is_dir() and (c / "crawl-report.json").is_file():
                        report_dir = c
                        break
            crawl_json = report_dir / "crawl-report.json"
            if not crawl_json.is_file():
                return self._send_json({"error": f"找不到報告：{crawl_json}"}, 404)
            label = (job or {}).get("client_label") or payload.get("client_label") or job_id
            plan_id = _resolve_plan_id(ctx, {**payload, "plan_id": (job or {}).get("plan_id")})
            from sitespider.plans import get_plan

            plan = get_plan(str(plan_id))
            if not plan.has("ai_polish"):
                return self._send_json(
                    {"error": "AI 文案需 Starter（試用 1 次/月）或 Pro 方案", "plan_id": plan.id},
                    403,
                )
            from sitespider.usage import check_ai_polish_quota

            ai_quota = check_ai_polish_quota(tenant, plan)
            if not ai_quota.allowed:
                return self._send_json(
                    {"error": ai_quota.reason, "quota": ai_quota.__dict__},
                    402,
                )
            try:
                from sitespider.ai_settings_store import (
                    get_tenant_ai_settings,
                    merge_ai_into_payload,
                )

                payload = merge_ai_into_payload(payload, get_tenant_ai_settings(tenant))
            except Exception:
                pass
            api_key = (
                str(payload.get("ai_api_key") or payload.get("openai_api_key") or "").strip() or None
            )
            model = (
                str(payload.get("ai_model") or payload.get("ai_model_custom") or payload.get("model") or "")
                .strip()
                or None
            )
            provider_id = str(payload.get("ai_provider") or "").strip() or None
            base_url = str(payload.get("ai_base_url") or "").strip() or None
            if not _acquire_ai_polish_running(job_id):
                return self._send_json(
                    {"error": "AI 文案產生中", "status": "ai_running"},
                    409,
                )
            patch = {
                "report_dir": str(report_dir),
                "client_label": label,
                "tenant_id": tenant,
            }
            if plan_id:
                patch["plan_id"] = plan_id
            _patch_job(job_id, patch)
            threading.Thread(
                target=_run_ai_polish_async,
                args=(job_id, report_dir),
                kwargs={
                    "label": label,
                    "api_key": api_key,
                    "model": model,
                    "provider_id": provider_id,
                    "base_url": base_url,
                    "tenant_id": tenant,
                },
                daemon=True,
            ).start()
            return self._send_json(
                {
                    "ok": True,
                    "status": "ai_running",
                    "ai_quota": {"used": ai_quota.ai_used, "limit": ai_quota.ai_limit},
                },
                202,
            )

        if api_path.startswith("/api/job/") and api_path.endswith("/share"):
            parts = [p for p in api_path.split("/") if p]
            if len(parts) < 4:
                return self._send_json({"error": "invalid path"}, 400)
            job_id = parts[2]
            job = _resolve_job_by_id(job_id)
            if not job or job.get("status") != "done":
                return self._send_json({"error": "報告尚未就緒"}, 400)
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                return self._send_json({"error": "invalid json"}, 400)
            tenant = str(payload.get("tenant_id") or job.get("tenant_id") or "default").strip()
            from sitespider.auth import require_tenant
            from sitespider.plans import get_plan
            from sitespider.billing_stripe import resolve_tenant_plan
            from sitespider.report_share import create_report_share

            try:
                ctx = require_tenant(self._auth_header(), tenant)
                tenant = ctx.tenant_id
            except PermissionError as e:
                return self._send_json({"error": str(e)}, 401)
            plan_id = _resolve_plan_id(ctx, payload)
            plan = get_plan(str(plan_id))
            if not plan.has("portal_share"):
                return self._send_json({"error": "客戶分享需 Free 或以上方案"}, 403)
            ttl = int(payload.get("ttl_days") or 30)
            ttl = max(1, min(ttl, 90))
            try:
                share = create_report_share(
                    tenant_id=tenant,
                    job_id=job_id,
                    report_dir=_job_report_dir(job),
                    label=(job.get("client_label") or payload.get("label") or job_id),
                    ttl_days=ttl,
                )
            except FileNotFoundError as e:
                return self._send_json({"error": str(e)}, 404)
            public = os.environ.get("SITESPIDER_PUBLIC_URL", "").strip().rstrip("/")
            share_url = share["share_path"]
            if public:
                share_url = public + share["share_path"]
            return self._send_json(
                {
                    "ok": True,
                    "token": share["token"],
                    "share_url": share_url,
                    "share_path": share["share_path"],
                    "expires_at": share["expires_at"],
                    "ttl_days": ttl,
                }
            )

        if api_path != "/api/crawl":
            return self.send_error(404)

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return self._send_json({"error": "invalid json"}, 400)

        from sitespider.auth import require_tenant
        from sitespider.plans import get_plan
        from sitespider.usage import check_crawl_quota

        try:
            ctx = require_tenant(self._auth_header(), payload.get("tenant_id"))
        except PermissionError as e:
            return self._send_json({"error": str(e)}, 401)

        from sitespider.url_sanitize import sanitize_start_url, start_url_looks_invalid

        if payload.get("url"):
            payload["url"] = sanitize_start_url(str(payload["url"]))
        bad_url = start_url_looks_invalid(str(payload.get("url") or ""))
        if bad_url:
            return self._send_json({"error": bad_url}, 400)

        plan_id = _resolve_plan_id(ctx, payload)
        plan = get_plan(plan_id)
        # 讀取伺服器端 AI 設定（避免前端欄位未同步導致 auto AI 不觸發）
        try:
            from sitespider.ai_settings_store import (
                get_tenant_ai_settings,
                merge_ai_into_payload,
            )

            ai_saved = get_tenant_ai_settings(ctx.tenant_id)
        except Exception:
            ai_saved = {}
        pages_req = int(payload.get("max_pages", 500))
        quota = check_crawl_quota(ctx.tenant_id, plan, pages_requested=pages_req)
        if not quota.allowed:
            return self._send_json({"error": quota.reason, "quota": quota.__dict__}, 402)

        payload["tenant_id"] = ctx.tenant_id
        payload["plan_id"] = plan.id
        payload = merge_ai_into_payload(payload, ai_saved)
        if pages_req > plan.max_pages_per_crawl:
            payload["max_pages"] = plan.max_pages_per_crawl

        job_id = str(uuid.uuid4())[:8]
        _set_job(
            job_id,
            {
                "status": "running",
                "site_url": payload.get("url", ""),
                "client_label": payload.get("client_label", ""),
                "max_pages": int(payload.get("max_pages", 500)),
                "progress": {"done": 0, "total": 1, "current": "啟動中…"},
            },
        )
        threading.Thread(target=_run_crawl, args=(job_id, payload), daemon=True).start()
        self._send_json({"job_id": job_id, "status": "running"})


def main(argv: list[str] | None = None) -> None:
    import argparse
    import os

    parser = argparse.ArgumentParser(description="SiteSpider Web 控制台")
    parser.add_argument("--port", type=int, default=int(os.environ.get("SITESPIDER_PORT", "8765")))
    parser.add_argument("--host", default=os.environ.get("SITESPIDER_HOST", "127.0.0.1"))
    args = parser.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), CrawlerHandler)
    print(f"SiteSpider 控制台：http://{args.host}:{args.port}/")
    print("  設定檔上傳 / 範例載入 · 無 GSC 亦可交付 · REPORT-zh.md")
    print("  按 Ctrl+C 結束")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
