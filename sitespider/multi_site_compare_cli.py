"""sitespider multi-compare — 多站比較儀表板。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sitespider.multi_site_compare import export_multi_site_compare_html


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sitespider multi-compare",
        description="比較多份 crawl-report.json，產生多站比較 HTML",
    )
    parser.add_argument(
        "reports",
        nargs="+",
        type=Path,
        help="各站報告目錄下的 crawl-report.json 路徑（至少 2 個）",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("multi_site_compare.html"),
        help="輸出 HTML（預設 multi_site_compare.html）",
    )
    parser.add_argument("--title", default="多站 SEO 比較", help="頁面標題")
    args = parser.parse_args(argv)

    paths = [p.resolve() for p in args.reports]
    for p in paths:
        if not p.is_file():
            print(f"找不到：{p}", file=sys.stderr)
            return 2

    try:
        out = export_multi_site_compare_html(paths, args.output.resolve(), title=args.title)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    print(out)
    return 0
