"""由 crawl-report.json 重新匯出 CSV / HTML（無需重爬）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sitespider.report import write_all_reports
from sitespider.report_load import load_report_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sitespider export",
        description="由 crawl-report.json 重新產生報告（CSV、index.html、dashboard 等）",
    )
    parser.add_argument(
        "crawl_json",
        nargs="?",
        type=Path,
        default=Path("reports/crawl-report.json"),
        help="crawl-report.json 路徑",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="輸出目錄（預設與 JSON 同目錄）",
    )
    parser.add_argument("--xlsx", action="store_true", help="另匯出 Excel")
    parser.add_argument("--client-report", action="store_true", help="產生 SEO-AUDIT-zh.md")
    parser.add_argument("--label", default=None, help="客戶報告 / 儀表板標題")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="file 模式網站根目錄（預設為 JSON 所在目錄）",
    )
    args = parser.parse_args(argv)

    crawl = args.crawl_json.resolve()
    if not crawl.is_file():
        print(f"找不到：{crawl}", file=sys.stderr)
        return 2

    out_dir = (args.output or crawl.parent).resolve()
    site_root = (args.root or crawl.parent).resolve()

    try:
        report = load_report_json(crawl)
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        print(f"無法讀取報告：{e}", file=sys.stderr)
        return 2

    label = args.label or report.start_url
    written = write_all_reports(
        report,
        out_dir,
        site_root=site_root,
        export_xlsx=args.xlsx,
        client_report=args.client_report,
        client_report_label=label,
    )
    print(f"已匯出 {len(report.pages)} 頁 → {out_dir}/")
    print("  " + " · ".join(written))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
