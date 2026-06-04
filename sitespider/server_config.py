"""Web 控制台：設定檔載入與表單欄位對應。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sitespider.site_config import SiteConfig, load_site_config


def safe_project_path(rel: str, *, base: Path | None = None) -> Path | None:
    if not rel or ".." in rel:
        return None
    root = (base or Path.cwd()).resolve()
    path = (root / rel).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    if not path.is_file():
        return None
    return path


def list_example_configs(base: Path | None = None) -> list[dict[str, str]]:
    root = (base or Path.cwd()).resolve()
    ex = root / "examples"
    if not ex.is_dir():
        return []
    return [
        {"id": p.name, "path": str(p.relative_to(root))}
        for p in sorted(ex.glob("*-sitespider.json"))
    ]


def _config_to_form(cfg: SiteConfig, raw: dict[str, Any], *, path_label: str = "") -> dict[str, Any]:
    crawl = raw.get("crawl") or {}
    gsc = raw.get("gsc") or {}
    exclude = list(cfg.exclude_path_prefixes) if cfg.exclude_path_prefixes else crawl.get("exclude_paths") or []
    if isinstance(exclude, str):
        exclude = [exclude]
    return {
        "config_path": path_label,
        "site_url": cfg.site_url or "",
        "mode": cfg.mode or "http",
        "max_pages": cfg.max_pages if cfg.max_pages is not None else 500,
        "max_depth": cfg.max_depth if cfg.max_depth is not None else 10,
        "workers": cfg.workers if cfg.workers is not None else 4,
        "respect_robots": cfg.respect_robots if cfg.respect_robots is not None else True,
        "use_sitemap": cfg.use_sitemap if cfg.use_sitemap is not None else True,
        "check_external": bool(cfg.check_external),
        "render_js": bool(cfg.render_javascript),
        "render_wait": cfg.render_wait_until or "domcontentloaded",
        "strip_query": bool(cfg.strip_query_string),
        "thin_content_min": cfg.thin_content_min_words
        if cfg.thin_content_min_words is not None
        else 300,
        "lighthouse": bool(cfg.run_lighthouse),
        "lighthouse_max": cfg.lighthouse_max if cfg.lighthouse_max is not None else 5,
        "require_json_ld": bool(cfg.require_json_ld),
        "xlsx": bool(cfg.export_xlsx),
        "client_report": bool(cfg.client_report),
        "client_label": cfg.client_label or "",
        "exclude_paths": exclude,
        "gsc_site_url": cfg.gsc_site_url or gsc.get("site_url") or cfg.site_url or "",
        "gsc_inspect_max": int(
            cfg.gsc_inspect_max
            if cfg.gsc_inspect_max is not None
            else gsc.get("inspect_max")
            or 0
        ),
        "output": cfg.output or "reports",
        "consultant_name": (cfg.branding or {}).get("consultant_name", ""),
        "logo_url": (cfg.branding or {}).get("logo_url", ""),
        "accent_color": (cfg.branding or {}).get("accent_color", "#3dd6a0"),
    }


def load_config_form(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cfg, _ = load_site_config(path.parent, config_path=path)
    if cfg is None:
        cfg = SiteConfig.from_dict(raw)
    rel = str(path.resolve().relative_to(Path.cwd().resolve()))
    return _config_to_form(cfg, raw, path_label=rel)


def parse_uploaded_config(text: str) -> dict[str, Any]:
    raw = json.loads(text)
    cfg = SiteConfig.from_dict(raw)
    return _config_to_form(cfg, raw, path_label="（已上傳）")
