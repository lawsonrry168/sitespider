"""SiteSpider 命令列介面。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sitespider.check import run_audit_check
from sitespider.crawler import CrawlConfig, SeoCrawler, discover_html_files, report_to_dict
from sitespider.init_ci import write_github_workflow
from sitespider.issues import ISSUE_LABELS
from sitespider.lighthouse_runner import lighthouse_available
from sitespider.report import write_all_reports
from sitespider.report_xlsx import xlsx_available
from sitespider.site_config import (
    load_site_config,
    merge_cli_with_config,
    write_default_config,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sitespider",
        description="SiteSpider — 專業 SEO 站內爬蟲（連結結構、標題、圖片、robots、sitemap、Lighthouse）",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=None,
        help="設定檔路徑（預設搜尋 sitespider.json）",
    )
    parser.add_argument(
        "--mode",
        choices=("file", "http"),
        default=None,
        help="file=讀取本機 HTML；http=透過 URL 爬取",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="網站根目錄（file 模式，預設為目前工作目錄）",
    )
    parser.add_argument("--url", default=None, help="起始 URL（http 模式）")
    parser.add_argument("-o", "--output", type=Path, default=None, help="報告輸出目錄")
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--max-depth", type=int, default=None)
    parser.add_argument("--workers", type=int, default=None, help="並行執行緒數")
    parser.add_argument("--no-robots", action="store_true", help="不遵守 robots.txt")
    parser.add_argument("--no-sitemap", action="store_true", help="不使用 sitemap.xml 種子")
    parser.add_argument(
        "--exclude-path",
        action="append",
        default=None,
        metavar="PREFIX",
        help="不爬取的路徑前綴（可重複，例如 /api/）",
    )
    parser.add_argument("--check-external", action="store_true", help="檢查外部連結狀態")
    parser.add_argument(
        "--eager-link-check",
        action="store_true",
        help="爬取每頁時即時 HEAD 內鏈（較慢；預設爬完後批次檢查）",
    )
    parser.add_argument(
        "--check-images-on-fetch",
        action="store_true",
        help="爬取每頁時即時檢查圖片（較慢；預設爬完後批次檢查）",
    )
    parser.add_argument(
        "--no-hreflang-audit",
        action="store_true",
        help="關閉 hreflang 互指稽核",
    )
    parser.add_argument(
        "--render-js",
        action="store_true",
        help="以 Playwright 渲染 JavaScript 後再解析（需 sitespider[browser]）",
    )
    parser.add_argument(
        "--render-wait",
        default=None,
        choices=("commit", "domcontentloaded", "load", "networkidle"),
        help="Playwright 等待策略（預設 domcontentloaded）",
    )
    parser.add_argument(
        "--urls-file",
        type=Path,
        default=None,
        help="URL 清單檔（種子，仍可 BFS；純清單請用 sitespider list）",
    )
    parser.add_argument(
        "--strip-query",
        action="store_true",
        help="正規化 URL 時移除查詢字串",
    )
    parser.add_argument(
        "--screenshots",
        action="store_true",
        help="--render-js 時儲存全頁截圖至 reports/.../screenshots/",
    )
    parser.add_argument(
        "--custom-config",
        type=Path,
        default=None,
        help="自訂擷取規則 JSON（陣列：name, css, regex）",
    )
    parser.add_argument("--lighthouse", action="store_true", help="爬取後執行 Lighthouse（需 http 模式）")
    parser.add_argument("--lighthouse-max", type=int, default=None)
    parser.add_argument(
        "--require-json-ld",
        action="store_true",
        help="可索引頁面必須含 JSON-LD",
    )
    parser.add_argument(
        "--thin-content-min",
        type=int,
        default=None,
        metavar="N",
        help="字數低於 N 標記為內容過薄（0=關閉，預設 300）",
    )
    parser.add_argument(
        "--xlsx",
        action="store_true",
        help="另匯出 Excel（需 pip install sitespider[excel]）",
    )
    parser.add_argument(
        "--client-report",
        action="store_true",
        help="產生繁中客戶交付 Markdown（SEO-AUDIT-zh.md）",
    )
    parser.add_argument(
        "--client-label",
        default=None,
        help="客戶報告標題（例如網站名稱）",
    )
    parser.add_argument(
        "--download-images",
        action="store_true",
        help="下載站內圖片至 reports/.../images/（並產生 images-gallery.html）",
    )
    parser.add_argument(
        "--max-images-download",
        type=int,
        default=None,
        metavar="N",
        help="最多下載圖片數（預設 300，僅同站）",
    )
    parser.add_argument("--json", action="store_true", help="僅輸出 JSON 至 stdout")
    parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="若發現 SEO 問題則 exit code 1（適合 CI）",
    )
    parser.add_argument("--ui", action="store_true", help="啟動 Web 控制台")
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Web 控制台埠（僅搭配 --ui）",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Web 控制台位址（僅搭配 --ui）",
    )
    parser.add_argument(
        "--gsc-inspect-max",
        type=int,
        default=None,
        metavar="N",
        help="以 Search Console API 檢查 Rich Results（最多 N 個 URL，需 sitespider[gsc] 與憑證）",
    )
    parser.add_argument(
        "--gsc-site-url",
        default=None,
        help="GSC 資源 URL（例 https://www.example.com/ 或 sc-domain:example.com）",
    )
    parser.add_argument(
        "--fetch-policy",
        choices=("http", "js", "auto"),
        default=None,
        help="抓取策略：http=純 HTTP；js=全站 Playwright；auto=產品頁等走 JS",
    )
    parser.add_argument(
        "--cache-responses",
        action="store_true",
        help="快取 HTTP 回應至磁碟（開發／重跑 parser 時不重打站）",
    )
    parser.add_argument("--cache-dir", type=Path, default=None, help="回應快取目錄")
    parser.add_argument(
        "--crawldir",
        type=Path,
        default=None,
        help="checkpoint 目錄（中斷後可 --resume 續跑）",
    )
    parser.add_argument("--resume", action="store_true", help="從 crawldir checkpoint 恢復")
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=None,
        metavar="N",
        help="每 N 頁寫入 checkpoint（預設 25）",
    )
    parser.add_argument(
        "--adaptive-extract",
        action="store_true",
        help="自訂擷取啟用 JSON-LD / regex fallback 鏈",
    )
    parser.add_argument(
        "--stealth-headers",
        action="store_true",
        help="HTTP 請求附加瀏覽器風格標頭",
    )
    parser.add_argument(
        "--scrapling",
        action="store_true",
        help="使用 Scrapling fetcher（需 pip install 'sitespider[scrapling]'）",
    )
    return parser


def run_client_report(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="sitespider report",
        description="由 crawl-report.json 產生繁中客戶 Markdown 報告",
    )
    parser.add_argument(
        "crawl_json",
        nargs="?",
        type=Path,
        default=Path("reports/crawl-report.json"),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="輸出路徑（預設與 JSON 同目錄 SEO-AUDIT-zh.md）",
    )
    parser.add_argument("--label", default=None, help="報告標題")
    args = parser.parse_args(argv)
    crawl = args.crawl_json.resolve()
    out = args.output or crawl.parent / "SEO-AUDIT-zh.md"
    from sitespider.client_report import write_client_report

    path = write_client_report(crawl, out, site_label=args.label)
    print(f"已產生客戶報告：{path}")
    return 0


def run_init(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="sitespider init",
        description="在專案中產生 GitHub Actions 與 sitespider.json 範本",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(".github/workflows/sitespider.yml"),
        help="GitHub Actions YAML 路徑",
    )
    parser.add_argument(
        "--site-root",
        default=".",
        help="workflow 內 sitespider --root 的值",
    )
    parser.add_argument(
        "--with-config",
        action="store_true",
        help="一併建立 sitespider.json 或 sitespider.yaml",
    )
    parser.add_argument(
        "--yaml",
        action="store_true",
        help="與 --with-config 搭配，產生 YAML 設定檔",
    )
    parser.add_argument(
        "--site-url",
        default="https://example.com/",
        help="寫入設定檔的 site_url",
    )
    parser.add_argument(
        "--config-path",
        type=Path,
        default=Path("sitespider.json"),
        help="設定檔輸出路徑",
    )
    args = parser.parse_args(argv)
    path = write_github_workflow(args.output, site_root=args.site_root)
    print(f"已建立 GitHub Actions：{path}")
    if args.with_config:
        cfg_path = args.config_path
        if args.yaml and cfg_path.suffix.lower() == ".json":
            cfg_path = cfg_path.with_suffix(".yaml")
        cfg_path = write_default_config(
            cfg_path, site_url=args.site_url, as_yaml=args.yaml
        )
        print(f"已建立設定檔：{cfg_path}")
    print("推送後將在 push/PR 時自動執行 sitespider --fail-on-issues")
    return 0


def _resolve_start_url(args, site_root: Path) -> str:
    if args.mode == "file":
        index = site_root / "index.html"
        if not index.exists():
            print(f"錯誤：{index} 不存在", file=sys.stderr)
            raise SystemExit(1)
        return index.as_uri()
    url = args.url
    cfg = getattr(args, "site_config", None)
    if cfg and cfg.site_url and url == "http://localhost:8080/":
        return cfg.site_url.rstrip("/") + "/"
    return url


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "init":
        return run_init(argv[1:])
    if argv and argv[0] == "compare":
        from sitespider.compare_cli import main as compare_main

        return compare_main(argv[1:])

    if argv and argv[0] == "report":
        return run_client_report(argv[1:])

    if argv and argv[0] == "diff-csv":
        from sitespider.diff_csv_cli import main as diff_csv_main

        return diff_csv_main(argv[1:])

    if argv and argv[0] == "urls":
        from sitespider.urls_cli import main as urls_main

        return urls_main(argv[1:])

    if argv and argv[0] == "package":
        from sitespider.package_report import main as package_main

        return package_main(argv[1:])

    if argv and argv[0] == "list":
        from sitespider.list_cli import main as list_main

        return list_main(argv[1:])

    if argv and argv[0] == "export":
        from sitespider.export_cli import main as export_main

        return export_main(argv[1:])

    if argv and argv[0] == "schedule":
        from sitespider.schedule_cli import main as schedule_main

        return schedule_main(argv[1:])

    if argv and argv[0] == "ai-polish":
        from sitespider.ai_polish_cli import main as ai_polish_main

        return ai_polish_main(argv[1:])

    if argv and argv[0] == "share-report":
        from sitespider.share_report_cli import main as share_main

        return share_main(argv[1:])

    if argv and argv[0] == "multi-compare":
        from sitespider.multi_site_compare_cli import main as multi_main

        return multi_main(argv[1:])

    if argv and argv[0] == "extract":
        from sitespider.extract_cli import main as extract_main

        return extract_main(argv[1:])

    args = build_parser().parse_args(argv)

    if args.ui:
        from sitespider.server import main as server_main

        server_main(["--host", args.host, "--port", str(args.port)])
        return 0

    site_root = (args.root or Path.cwd()).resolve()
    if not site_root.exists():
        print(f"錯誤：找不到網站根目錄 {site_root}", file=sys.stderr)
        return 1

    site_cfg, cfg_path = load_site_config(site_root, config_path=args.config)
    merge_cli_with_config(args, site_cfg)

    if cfg_path:
        print(f"設定檔: {cfg_path}")

    start_url = _resolve_start_url(args, site_root)

    seed_urls: tuple[str, ...] = ()
    if args.urls_file:
        from sitespider.list_crawl import filter_same_host, load_url_list

        seed_urls = tuple(load_url_list(args.urls_file.resolve(), base_url=start_url))
        seed_urls = tuple(filter_same_host(list(seed_urls), start_url))
        print(f"URL 清單種子：{len(seed_urls)} 個")

    custom_rules: tuple = ()
    if args.custom_config and args.custom_config.is_file():
        import json

        raw = json.loads(args.custom_config.read_text(encoding="utf-8"))
        custom_rules = tuple(raw if isinstance(raw, list) else raw.get("extractions", []))

    prefixes = getattr(args, "sitemap_path_prefixes", ())
    exclude = tuple(args.exclude_path or ()) or getattr(args, "exclude_path_prefixes", ())
    config = CrawlConfig(
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        workers=args.workers,
        respect_robots=not args.no_robots,
        use_sitemap=not args.no_sitemap,
        check_external=args.check_external,
        run_lighthouse=args.lighthouse,
        lighthouse_max=args.lighthouse_max if args.lighthouse_max is not None else 10,
        require_json_ld=args.require_json_ld,
        thin_content_min_words=args.thin_content_min if args.thin_content_min is not None else 300,
        sitemap_path_prefixes=prefixes,
        exclude_path_prefixes=exclude,
        defer_link_checks=not args.eager_link_check,
        check_images_on_fetch=args.check_images_on_fetch,
        audit_hreflang=not args.no_hreflang_audit,
        json_ld_rules=getattr(args, "json_ld_rules", ()),
        render_javascript=args.render_js or getattr(args, "render_javascript", False),
        render_wait_until=args.render_wait or getattr(args, "render_wait_until", "domcontentloaded"),
        strip_query_string=args.strip_query,
        save_screenshots=args.screenshots,
        custom_extractions=custom_rules or tuple(getattr(args, "custom_extractions", ()) or ()),
        seed_urls=seed_urls,
        gsc_site_url=getattr(args, "gsc_site_url", None),
        gsc_inspect_max=args.gsc_inspect_max if getattr(args, "gsc_inspect_max", None) else 0,
        download_images=bool(getattr(args, "download_images", False)),
        max_images_download=(
            args.max_images_download if getattr(args, "max_images_download", None) is not None else 300
        ),
        fetch_policy=args.fetch_policy or "http",
        cache_responses=bool(getattr(args, "cache_responses", False)),
        cache_dir=str(args.cache_dir.resolve()) if getattr(args, "cache_dir", None) else None,
        resume_crawl=bool(getattr(args, "resume", False)),
        checkpoint_interval=(
            args.checkpoint_interval if getattr(args, "checkpoint_interval", None) is not None else 25
        ),
        adaptive_extractions=bool(getattr(args, "adaptive_extract", False)),
        stealth_headers=bool(getattr(args, "stealth_headers", False)),
        use_scrapling=bool(getattr(args, "scrapling", False)),
    )

    if getattr(args, "gsc_inspect_max", None):
        from sitespider.gsc_inspection import gsc_available

        if not gsc_available():
            print(
                '警告：--gsc-inspect-max 需要 pip install "sitespider[gsc]" 與 GSC 憑證',
                file=sys.stderr,
            )
        else:
            print(f"GSC Rich Results 檢查：最多 {args.gsc_inspect_max} 個 URL")

    if args.render_js:
        from sitespider.js_render import playwright_available

        if not playwright_available():
            print(
                '錯誤：--render-js 需要 pip install "sitespider[browser]" 與 playwright install chromium',
                file=sys.stderr,
            )
            return 1
        if args.mode != "http":
            print("警告：--render-js 僅支援 --mode http", file=sys.stderr)
        if config.workers > 2:
            print("提示：JS 渲染模式建議 --workers 1–2（已自動上限為 2）", file=sys.stderr)

    if args.lighthouse and args.mode != "http":
        print("警告：Lighthouse 僅支援 --mode http", file=sys.stderr)
    if args.lighthouse and not lighthouse_available():
        print("警告：未安裝 lighthouse，請執行: npm install", file=sys.stderr)
    if args.xlsx and not xlsx_available():
        print("警告：未安裝 openpyxl，請執行: pip install 'sitespider[excel]'", file=sys.stderr)
        args.xlsx = False

    out_dir = args.output.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    ck_dir = None
    if getattr(args, "crawldir", None) or getattr(args, "resume", False):
        ck_dir = (args.crawldir or out_dir / ".crawl").resolve()
        config.crawldir = str(ck_dir)
    if getattr(args, "cache_responses", False) and not config.cache_dir:
        config.cache_dir = str((args.cache_dir or out_dir / ".cache").resolve())
    if getattr(args, "resume", False) and ck_dir and not ck_dir.is_dir():
        print(f"警告：找不到 checkpoint 目錄 {ck_dir}，將全新爬取", file=sys.stderr)

    print(f"SiteSpider v{__import__('sitespider').__version__}")
    uses_js = config.render_javascript or config.fetch_policy in ("js", "auto")
    eff_workers = min(config.workers, 2) if uses_js else config.workers
    js_note = ""
    if config.render_javascript:
        js_note = " · JS 渲染"
    elif config.fetch_policy == "auto":
        js_note = " · fetch=auto"
    elif config.fetch_policy == "js":
        js_note = " · fetch=js"
    print(f"模式: {args.mode} · 並行: {eff_workers}{js_note} · 深度 ≤{config.max_depth}")
    print(f"robots: {'開' if config.respect_robots else '關'} · sitemap: {'開' if config.use_sitemap else '關'}")
    if prefixes:
        print(f"sitemap 路徑前綴: {', '.join(prefixes)}")
    if exclude:
        print(f"排除路徑: {', '.join(exclude)}")
    if config.require_json_ld:
        print("JSON-LD: 必填")
    if config.thin_content_min_words:
        print(f"內容過薄門檻: <{config.thin_content_min_words} 字")
    print(f"根目錄: {site_root}")
    if config.cache_responses:
        print("回應快取: 開")
    if ck_dir:
        print(f"checkpoint: {ck_dir}" + (" · 恢復" if config.resume_crawl else ""))
    print("爬取中…")

    crawler = SeoCrawler(
        start_url,
        mode=args.mode,
        site_root=site_root,
        config=config,
        lighthouse_out=out_dir / "lighthouse",
        crawldir=ck_dir,
        on_progress=lambda d, t, u: print(f"  [{d}/{t}] {Path(u).name or u}", end="\r"),
    )
    report = crawler.crawl()
    print()

    if args.json:
        print(json.dumps(report_to_dict(report), ensure_ascii=False, indent=2))
        return 0

    client_label = args.client_label
    if not client_label and getattr(args, "site_config", None):
        pass  # use site_url only if no explicit label
    written = write_all_reports(
        report,
        out_dir,
        site_root=site_root,
        export_xlsx=args.xlsx,
        client_report=args.client_report,
        client_report_label=client_label,
    )

    print("=" * 50)
    print(f"完成：{len(report.pages)} 頁 · robots 封鎖 {len(report.blocked_urls)} · {((report.finished_at or 0) - report.started_at):.2f}s")
    print(f"\n報告目錄: {out_dir}/")
    print("  " + " · ".join(written))

    html_files = discover_html_files(site_root)
    if html_files:
        print(f"\n根目錄 HTML: {', '.join(html_files)}")

    issues = report.summary_issues()
    if issues:
        print("\n問題摘要:")
        for key, urls in sorted(issues.items(), key=lambda x: -len(set(x[1]))):
            print(f"  · {ISSUE_LABELS.get(key, key)}: {len(set(urls))} 頁")

    if args.fail_on_issues:
        return run_audit_check(out_dir / "crawl-report.json")

    return 0
