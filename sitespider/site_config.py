"""
專案設定檔 — site_url、sitemap 路徑前綴、爬取與稽核預設值。

搜尋順序（以 site_root 為基準，先找到先用）：
  sitespider.json → .sitespider.json → sitespider.yaml → sitespider.yml
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONFIG_FILENAMES = (
    "sitespider.json",
    ".sitespider.json",
    "sitespider.yaml",
    "sitespider.yml",
    ".sitespider.yaml",
    ".sitespider.yml",
)


@dataclass
class SiteConfig:
    """合併 CLI 前的專案層設定。"""

    site_url: str | None = None
    sitemap_path_prefixes: tuple[str, ...] = ()
    exclude_path_prefixes: tuple[str, ...] = ()
    json_ld_rules: tuple[tuple[str, tuple[str, ...]], ...] = ()
    custom_extractions: tuple = ()
    render_javascript: bool | None = None
    render_wait_until: str | None = None
    strip_query_string: bool | None = None
    save_screenshots: bool | None = None
    mode: str | None = None
    url: str | None = None
    output: str | None = None
    max_pages: int | None = None
    max_depth: int | None = None
    workers: int | None = None
    respect_robots: bool | None = None
    use_sitemap: bool | None = None
    check_external: bool | None = None
    run_lighthouse: bool | None = None
    lighthouse_max: int | None = None
    require_json_ld: bool | None = None
    thin_content_min_words: int | None = None
    export_xlsx: bool | None = None
    client_label: str | None = None
    client_report: bool | None = None
    gsc_site_url: str | None = None
    gsc_inspect_max: int | None = None
    branding: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SiteConfig:
        crawl = data.get("crawl") or {}
        audit = data.get("audit") or {}
        report = data.get("report") or {}
        gsc = data.get("gsc") or {}
        prefixes = data.get("sitemap_path_prefixes") or data.get("path_prefixes") or []
        if isinstance(prefixes, str):
            prefixes = [prefixes]
        norm_prefixes = tuple(
            f"{str(p).strip('/')}/" for p in prefixes if str(p).strip()
        )

        exclude = data.get("exclude_path_prefixes") or crawl.get("exclude_paths") or []
        if isinstance(exclude, str):
            exclude = [exclude]
        norm_exclude = tuple(str(p).strip() for p in exclude if str(p).strip())

        custom_raw = audit.get("custom_extractions") or data.get("custom_extractions") or []

        jl_rules: list[tuple[str, tuple[str, ...]]] = []
        for raw in audit.get("json_ld_rules") or []:
            if not isinstance(raw, dict):
                continue
            path = str(raw.get("path_contains") or raw.get("path") or "").strip()
            types = raw.get("types") or raw.get("type")
            if isinstance(types, str):
                types = [types]
            if not path or not types:
                continue
            jl_rules.append(
                (path, tuple(str(t).strip() for t in types if str(t).strip()))
            )

        return cls(
            site_url=_str_or_none(data.get("site_url")),
            sitemap_path_prefixes=norm_prefixes,
            exclude_path_prefixes=norm_exclude,
            json_ld_rules=tuple(jl_rules),
            custom_extractions=tuple(custom_raw) if isinstance(custom_raw, list) else (),
            render_javascript=_bool_or_none(crawl.get("render_javascript", crawl.get("render_js"))),
            render_wait_until=_str_or_none(crawl.get("render_wait_until", crawl.get("render_wait"))),
            strip_query_string=_bool_or_none(crawl.get("strip_query_string", crawl.get("strip_query"))),
            save_screenshots=_bool_or_none(crawl.get("save_screenshots", crawl.get("screenshots"))),
            mode=_str_or_none(data.get("mode")),
            url=_str_or_none(data.get("url")),
            output=_str_or_none(data.get("output")),
            max_pages=_int_or_none(crawl.get("max_pages", data.get("max_pages"))),
            max_depth=_int_or_none(crawl.get("max_depth", data.get("max_depth"))),
            workers=_int_or_none(crawl.get("workers", data.get("workers"))),
            respect_robots=_bool_or_none(crawl.get("respect_robots")),
            use_sitemap=_bool_or_none(crawl.get("use_sitemap")),
            check_external=_bool_or_none(crawl.get("check_external")),
            run_lighthouse=_bool_or_none(crawl.get("run_lighthouse", data.get("lighthouse"))),
            lighthouse_max=_int_or_none(crawl.get("lighthouse_max")),
            require_json_ld=_bool_or_none(audit.get("require_json_ld")),
            thin_content_min_words=_int_or_none(
                audit.get("thin_content_min_words", audit.get("thin_content_min"))
            ),
            export_xlsx=_bool_or_none(report.get("xlsx", report.get("export_xlsx"))),
            client_label=_str_or_none(data.get("client_label")),
            client_report=_bool_or_none(data.get("client_report", report.get("client_report"))),
            gsc_site_url=_str_or_none(gsc.get("site_url")),
            gsc_inspect_max=_int_or_none(gsc.get("inspect_max")),
            branding=(
                dict(b)
                if isinstance(
                    (b := (data.get("branding") or report.get("branding"))),
                    dict,
                )
                else None
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "site_url": self.site_url,
            "sitemap_path_prefixes": list(self.sitemap_path_prefixes),
            "exclude_path_prefixes": list(self.exclude_path_prefixes),
            "mode": self.mode,
            "url": self.url,
            "output": self.output,
            "crawl": {
                k: v
                for k, v in {
                    "max_pages": self.max_pages,
                    "max_depth": self.max_depth,
                    "workers": self.workers,
                    "respect_robots": self.respect_robots,
                    "use_sitemap": self.use_sitemap,
                    "check_external": self.check_external,
                    "run_lighthouse": self.run_lighthouse,
                    "lighthouse_max": self.lighthouse_max,
                    "exclude_paths": list(self.exclude_path_prefixes) or None,
                    "render_javascript": self.render_javascript,
                    "render_wait_until": self.render_wait_until,
                }.items()
                if v is not None
            },
            "audit": {
                **(
                    {
                        "json_ld_rules": [
                            {"path_contains": p, "types": list(t)}
                            for p, t in self.json_ld_rules
                        ]
                    }
                    if self.json_ld_rules
                    else {}
                ),
                **{
                    k: v
                    for k, v in {
                        "require_json_ld": self.require_json_ld,
                        "thin_content_min_words": self.thin_content_min_words,
                    }.items()
                    if v is not None
                },
            },
            "report": {"xlsx": self.export_xlsx} if self.export_xlsx is not None else {},
        }


def _str_or_none(v: Any) -> str | None:
    if v is None or v == "":
        return None
    return str(v).strip()


def _int_or_none(v: Any) -> int | None:
    if v is None or v == "":
        return None
    return int(v)


def _bool_or_none(v: Any) -> bool | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() in ("1", "true", "yes", "on")
    return bool(v)


def find_config_path(site_root: Path, explicit: Path | None = None) -> Path | None:
    if explicit is not None:
        p = explicit.expanduser().resolve()
        return p if p.is_file() else None
    root = site_root.resolve()
    for name in CONFIG_FILENAMES:
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def _parse_config_text(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as e:
            raise RuntimeError(
                f"讀取 YAML 設定需要 PyYAML：pip install 'sitespider[yaml]'（{path}）"
            ) from e
        data = yaml.safe_load(text)
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise ValueError(f"設定檔根節點須為物件：{path}")
        return data
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"設定檔必須為 JSON 物件：{path}")
    return data


def load_site_config(
    site_root: Path,
    *,
    config_path: Path | None = None,
) -> tuple[SiteConfig | None, Path | None]:
    path = find_config_path(site_root, config_path)
    if path is None:
        return None, None
    return SiteConfig.from_dict(_parse_config_text(path)), path


def write_default_config(
    path: Path,
    *,
    site_url: str = "https://example.com/",
    as_yaml: bool = False,
) -> Path:
    """寫入範本 sitespider.json 或 sitespider.yaml。"""
    template = SiteConfig(
        site_url=site_url.rstrip("/") + "/",
        sitemap_path_prefixes=(),
        mode="file",
        output="reports",
        max_pages=500,
        max_depth=10,
        workers=4,
        respect_robots=True,
        use_sitemap=True,
        require_json_ld=False,
        thin_content_min_words=300,
        export_xlsx=True,
    )
    path = path.resolve()
    payload = template.to_dict()

    if as_yaml or path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as e:
            raise RuntimeError("寫入 YAML 需 pip install 'sitespider[yaml]'") from e
        path.write_text(
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    else:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return path


def merge_cli_with_config(args: Any, cfg: SiteConfig | None) -> None:
    def pick(cli_val, cfg_val, fallback):
        if cli_val is not None:
            return cli_val
        if cfg_val is not None:
            return cfg_val
        return fallback

    if cfg is None:
        args.site_config = None
        args.sitemap_path_prefixes = ()
        args.exclude_path_prefixes = ()
        args.json_ld_rules = ()
        args.mode = pick(args.mode, None, "file")
        args.url = pick(args.url, None, "http://localhost:8080/")
        args.output = Path(pick(args.output, None, Path("reports")))
        args.max_pages = pick(args.max_pages, None, 500)
        args.max_depth = pick(args.max_depth, None, 10)
        args.workers = pick(args.workers, None, 4)
        args.lighthouse_max = pick(args.lighthouse_max, None, 10)
        args.thin_content_min = pick(args.thin_content_min, None, 300)
        return

    args.mode = pick(args.mode, cfg.mode, "file")
    args.url = pick(args.url, cfg.url, "http://localhost:8080/")
    args.output = Path(pick(args.output, Path(cfg.output) if cfg.output else None, Path("reports")))
    args.max_pages = pick(args.max_pages, cfg.max_pages, 500)
    args.max_depth = pick(args.max_depth, cfg.max_depth, 10)
    args.workers = pick(args.workers, cfg.workers, 4)
    args.lighthouse_max = pick(args.lighthouse_max, cfg.lighthouse_max, 10)
    args.thin_content_min = pick(args.thin_content_min, cfg.thin_content_min_words, 300)

    if cfg.require_json_ld:
        args.require_json_ld = args.require_json_ld or True
    if cfg.render_javascript:
        args.render_js = True
    if cfg.render_wait_until:
        args.render_wait = cfg.render_wait_until
    if cfg.strip_query_string:
        args.strip_query = True
    if cfg.save_screenshots:
        args.screenshots = True
    if cfg.custom_extractions:
        args.custom_extractions = cfg.custom_extractions
    if cfg.run_lighthouse:
        args.lighthouse = args.lighthouse or True
    if cfg.check_external:
        args.check_external = args.check_external or True
    if cfg.respect_robots is False:
        args.no_robots = True
    if cfg.use_sitemap is False:
        args.no_sitemap = True
    if cfg.export_xlsx:
        args.xlsx = getattr(args, "xlsx", False) or True
    if cfg.client_report:
        args.client_report = True
    if cfg.client_label:
        args.client_label = cfg.client_label
    if cfg.gsc_inspect_max is not None:
        args.gsc_inspect_max = cfg.gsc_inspect_max
    if cfg.gsc_site_url:
        args.gsc_site_url = cfg.gsc_site_url

    args.site_config = cfg
    args.sitemap_path_prefixes = cfg.sitemap_path_prefixes
    args.exclude_path_prefixes = cfg.exclude_path_prefixes
    args.json_ld_rules = cfg.json_ld_rules
