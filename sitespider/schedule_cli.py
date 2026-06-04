"""sitespider schedule — 排程爬取 + 增量比對（適合 cron）。"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from sitespider.compare import compare_files
from sitespider.crawler import CrawlConfig, SeoCrawler
from sitespider.branding import Branding
from sitespider.report import write_all_reports
from sitespider.site_config import load_site_config


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")


def run_scheduled_crawl(
    *,
    config_path: Path | None,
    site_root: Path,
    output_parent: Path,
    baseline: Path | None,
    max_pages: int | None,
    compare_changed_only: bool,
    markdown_out: Path | None,
) -> int:
    site_cfg, cfg_file = load_site_config(site_root, config_path=config_path)
    if not site_cfg or not site_cfg.site_url:
        print("錯誤：需要 site_url（設定檔或 --url）", file=sys.stderr)
        return 2

    label = (site_cfg.client_label or "site").replace("/", "-")
    out_dir = (output_parent / f"{label}-{_stamp()}").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    config = CrawlConfig(
        max_pages=max_pages or site_cfg.max_pages or 500,
        max_depth=site_cfg.max_depth or 10,
        workers=site_cfg.workers or 4,
        exclude_path_prefixes=site_cfg.exclude_path_prefixes,
        gsc_inspect_max=site_cfg.gsc_inspect_max or 0,
        gsc_site_url=site_cfg.gsc_site_url,
    )
    crawler = SeoCrawler(
        site_cfg.site_url,
        mode=site_cfg.mode or "http",
        site_root=site_root,
        config=config,
    )
    report = crawler.crawl()
    write_all_reports(
        report,
        out_dir,
        site_root=site_root,
        client_report=bool(site_cfg.client_report),
        client_report_label=site_cfg.client_label,
        branding=Branding.from_dict(site_cfg.branding),
    )
    current_json = out_dir / "crawl-report.json"
    print(f"爬取完成：{len(report.pages)} 頁 → {out_dir}")

    latest_link = output_parent / f"{label}-latest"
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    try:
        latest_link.symlink_to(out_dir.name, target_is_directory=True)
    except OSError:
        shutil.copytree(out_dir, output_parent / f"{label}-latest", dirs_exist_ok=True)

    if baseline and baseline.is_file():
        result = compare_files(
            baseline.resolve(),
            current_json,
            changed_urls_only=compare_changed_only,
        )
        md = result.to_markdown()
        diff_path = out_dir / "schedule-compare.md"
        diff_path.write_text(md, encoding="utf-8")
        print(f"比對報告：{diff_path}")
        if markdown_out:
            markdown_out.write_text(md, encoding="utf-8")
        if result.has_regressions:
            print("警告：發現回歸（新增問題或 URL 消失）", file=sys.stderr)
            return 1
    elif baseline:
        print(f"略過比對：找不到基準 {baseline}", file=sys.stderr)

    pointer = output_parent / f"{label}-baseline.json"
    shutil.copy2(current_json, pointer)
    meta = {
        "last_run": out_dir.name,
        "baseline": str(pointer),
        "pages": len(report.pages),
    }
    (output_parent / f"{label}-schedule-meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sitespider schedule",
        description="排程用：爬取 → 寫報告 → 與基準比對 → 更新 baseline 指標",
    )
    parser.add_argument("-c", "--config", type=Path, help="sitespider.json 路徑")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="專案根目錄")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("reports/scheduled"),
        help="排程報告父目錄",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="基準 crawl-report.json（預設用 output-dir 內 *-baseline.json）",
    )
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument(
        "--changed-urls-only",
        action="store_true",
        help="比對時僅計算有變更的 URL",
    )
    parser.add_argument(
        "--compare-output",
        type=Path,
        default=None,
        help="另存比對 Markdown 路徑",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    out_parent = args.output_dir.resolve()
    out_parent.mkdir(parents=True, exist_ok=True)

    baseline = args.baseline
    if baseline is None and args.config:
        cfg, _ = load_site_config(root, config_path=args.config)
        if cfg and cfg.client_label:
            label = cfg.client_label.replace("/", "-")
            cand = out_parent / f"{label}-baseline.json"
            if cand.is_file():
                baseline = cand

    return run_scheduled_crawl(
        config_path=args.config.resolve() if args.config else None,
        site_root=root,
        output_parent=out_parent,
        baseline=baseline,
        max_pages=args.max_pages,
        compare_changed_only=args.changed_urls_only,
        markdown_out=args.compare_output,
    )
