"""SiteSpider 命令列介面。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sitespider.check import run_audit_check
from sitespider.crawler import CrawlConfig, SeoCrawler, discover_html_files, report_to_dict
from sitespider.lighthouse_runner import lighthouse_available
from sitespider.report import write_all_reports

ISSUE_LABELS = {
    "missing_title": "缺少 title",
    "title_too_long": "title 過長",
    "title_too_short": "title 過短",
    "missing_meta_description": "缺少 meta description",
    "meta_description_too_long": "meta description 過長",
    "missing_h1": "缺少 H1",
    "multiple_h1": "多個 H1",
    "broken_image": "圖片失效",
    "missing_alt": "缺少 alt",
    "http_error": "HTTP 錯誤",
    "orphan_page": "孤立頁",
    "duplicate_title": "重複 title",
    "blocked_by_robots": "robots.txt 封鎖",
    "meta_noindex": "meta robots noindex",
    "missing_og_tags": "缺少 Open Graph",
    "missing_json_ld": "缺少 JSON-LD",
    "lighthouse_seo_low": "Lighthouse SEO 偏低",
    "lighthouse_perf_low": "Lighthouse 效能偏低",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sitespider",
        description="SiteSpider — 專業 SEO 站內爬蟲（連結結構、標題、圖片、robots、sitemap、Lighthouse）",
    )
    parser.add_argument(
        "--mode",
        choices=("file", "http"),
        default="file",
        help="file=讀取本機 HTML；http=透過 URL 爬取",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="網站根目錄（file 模式，預設為目前工作目錄）",
    )
    parser.add_argument("--url", default="http://localhost:8080/", help="起始 URL（http 模式）")
    parser.add_argument("-o", "--output", type=Path, default=Path("reports"), help="報告輸出目錄")
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument("--max-depth", type=int, default=10)
    parser.add_argument("--workers", type=int, default=4, help="並行執行緒數")
    parser.add_argument("--no-robots", action="store_true", help="不遵守 robots.txt")
    parser.add_argument("--no-sitemap", action="store_true", help="不使用 sitemap.xml 種子")
    parser.add_argument("--check-external", action="store_true", help="檢查外部連結狀態")
    parser.add_argument("--lighthouse", action="store_true", help="爬取後執行 Lighthouse（需 http 模式）")
    parser.add_argument("--lighthouse-max", type=int, default=10)
    parser.add_argument("--json", action="store_true", help="僅輸出 JSON 至 stdout")
    parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="若發現 SEO 問題則 exit code 1（適合 CI）",
    )
    parser.add_argument("--ui", action="store_true", help="啟動 Web 控制台")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.ui:
        from sitespider.server import main as server_main

        server_main()
        return 0

    site_root = (args.root or Path.cwd()).resolve()
    if not site_root.exists():
        print(f"錯誤：找不到網站根目錄 {site_root}", file=sys.stderr)
        return 1

    start_url = args.url
    if args.mode == "file":
        index = site_root / "index.html"
        if not index.exists():
            print(f"錯誤：{index} 不存在", file=sys.stderr)
            return 1
        start_url = index.as_uri()

    config = CrawlConfig(
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        workers=args.workers,
        respect_robots=not args.no_robots,
        use_sitemap=not args.no_sitemap,
        check_external=args.check_external,
        run_lighthouse=args.lighthouse,
        lighthouse_max=args.lighthouse_max,
    )

    if args.lighthouse and args.mode != "http":
        print("警告：Lighthouse 僅支援 --mode http", file=sys.stderr)
    if args.lighthouse and not lighthouse_available():
        print("警告：未安裝 lighthouse，請執行: cd sitespider && npm install", file=sys.stderr)

    print(f"SiteSpider v{__import__('sitespider').__version__}")
    print(f"模式: {args.mode} · 並行: {config.workers} · 深度 ≤{config.max_depth}")
    print(f"robots: {'開' if config.respect_robots else '關'} · sitemap: {'開' if config.use_sitemap else '關'}")
    print(f"根目錄: {site_root}")
    print("爬取中…")

    out_dir = args.output.resolve()

    crawler = SeoCrawler(
        start_url,
        mode=args.mode,
        site_root=site_root,
        config=config,
        lighthouse_out=out_dir / "lighthouse",
        on_progress=lambda d, t, u: print(f"  [{d}/{t}] {Path(u).name or u}", end="\r"),
    )
    report = crawler.crawl()
    print()

    if args.json:
        print(json.dumps(report_to_dict(report), ensure_ascii=False, indent=2))
        return 0

    write_all_reports(report, out_dir, site_root=site_root)

    print("=" * 50)
    print(f"完成：{len(report.pages)} 頁 · robots 封鎖 {len(report.blocked_urls)} · {((report.finished_at or 0) - report.started_at):.2f}s")
    print(f"\n報告目錄: {out_dir}/")
    print(f"  index.html · pages.csv · links.csv · images.csv · blocked.csv · lighthouse.csv")
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
