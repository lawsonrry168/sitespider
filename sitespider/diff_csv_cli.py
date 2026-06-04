"""sitespider diff-csv 命令列。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sitespider.diff_csv import compare_csv_urls, write_diff_exports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sitespider diff-csv",
        description="比對 Screaming Frog Internal CSV 與 SiteSpider internal.csv",
    )
    parser.add_argument(
        "screaming_frog_csv",
        type=Path,
        help="Screaming Frog 匯出的 Internal CSV（需含 Address 欄）",
    )
    parser.add_argument(
        "sitespider_csv",
        type=Path,
        nargs="?",
        default=Path("reports/internal.csv"),
        help="SiteSpider internal.csv（預設 reports/internal.csv）",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="差異報告輸出目錄（預設與 sitespider_csv 同目錄）",
    )
    parser.add_argument(
        "--fail-on-gap",
        action="store_true",
        help="若僅 SF 或僅 SS 的 URL 超過 10% 則 exit 1",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    sf = args.screaming_frog_csv.resolve()
    ours = args.sitespider_csv.resolve()
    if not sf.is_file():
        print(f"找不到：{sf}", file=sys.stderr)
        return 2
    if not ours.is_file():
        print(f"找不到：{ours}", file=sys.stderr)
        return 2

    try:
        diff = compare_csv_urls(sf, ours)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    out_dir = (args.output or ours.parent).resolve()
    files = write_diff_exports(diff, out_dir)

    if args.json:
        print(
            json.dumps(
                {
                    "sf_count": diff.sf_count,
                    "ours_count": diff.ours_count,
                    "in_both": len(diff.in_both),
                    "only_sf": len(diff.only_sf),
                    "only_ours": len(diff.only_ours),
                    "output_dir": str(out_dir),
                    "files": files,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for line in diff.summary_lines():
            print(line)
        print(f"\n已寫入：{out_dir}/")
        print("  " + " · ".join(files))

    if args.fail_on_gap:
        gap = len(diff.only_sf) + len(diff.only_ours)
        total = max(diff.sf_count, diff.ours_count, 1)
        if gap / total > 0.1:
            return 1
    return 0
