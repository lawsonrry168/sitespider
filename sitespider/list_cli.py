"""sitespider list — 依 URL 清單爬取（SF List Mode）。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sitespider.check import run_audit_check
from sitespider.crawler import CrawlConfig, SeoCrawler
from sitespider.issues import ISSUE_LABELS
from sitespider.list_crawl import filter_same_host, load_url_list
from sitespider.report import write_all_reports
from sitespider.site_config import load_site_config, merge_cli_with_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sitespider list",
        description="依 URL 清單爬取（不從首頁 BFS；對應 Screaming Frog List Mode）",
    )
    parser.add_argument("urls_file", type=Path, help="每行一個 URL 的文字檔")
    parser.add_argument("--url", default=None, help="網站根 URL（解析相對路徑）")
    parser.add_argument("-o", "--output", type=Path, default=Path("reports/list"))
    parser.add_argument("--config", "-c", type=Path, default=None)
    parser.add_argument("--allow-off-domain", action="store_true")
    parser.add_argument("--follow-links", action="store_true", help="仍跟隨內鏈擴展（預設僅清單內 URL）")
    parser.add_argument("--fail-on-issues", action="store_true")
    parser.add_argument("--render-js", action="store_true")
    parser.add_argument("--xlsx", action="store_true")
    parser.add_argument("--client-report", action="store_true")
    args = parser.parse_args(argv)

    site_root = Path.cwd().resolve()
    site_cfg, cfg_path = load_site_config(site_root, config_path=args.config)
    merge_cli_with_config(args, site_cfg)

    start = args.url or (site_cfg.site_url if site_cfg else None)
    if not start:
        print("請提供 --url 或設定檔 site_url", file=sys.stderr)
        return 2

    try:
        seeds = load_url_list(args.urls_file.resolve(), base_url=start)
    except (OSError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2

    if not args.allow_off_domain:
        seeds = filter_same_host(seeds, start)
    if not seeds:
        print("URL 清單為空", file=sys.stderr)
        return 2

    follow = args.follow_links
    config = CrawlConfig(
        max_pages=(args.max_pages or 500) if follow else len(seeds),
        max_depth=(args.max_depth or 3) if follow else 0,
        workers=getattr(args, "workers", None) or 4,
        list_mode=True,
        crawl_list_only=not follow,
        seed_urls=tuple(seeds),
        render_javascript=args.render_js,
        use_sitemap=False,
    )

    print(f"List 模式：{len(seeds)} 個種子 URL")
    crawler = SeoCrawler(start, mode="http", site_root=site_root, config=config)
    report = crawler.crawl()
    out = args.output.resolve()
    written = write_all_reports(report, out, client_report=args.client_report)

    print(f"完成 {len(report.pages)} 頁 → {out}/")
    print("  " + " · ".join(written[:8]) + (" …" if len(written) > 8 else ""))

    if args.fail_on_issues:
        return run_audit_check(out / "crawl-report.json")

    issues = report.summary_issues()
    if issues:
        for key, urls in sorted(issues.items(), key=lambda x: -len(x[1]))[:5]:
            print(f"  · {ISSUE_LABELS.get(key, key)}: {len(set(urls))}")

    return 0
