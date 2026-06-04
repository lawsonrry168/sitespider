"""sitespider compare 命令列。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sitespider.compare import compare_files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sitespider compare",
        description="比對兩份 crawl-report.json，找出新增／已修復的 SEO 問題",
    )
    parser.add_argument(
        "baseline",
        type=Path,
        help="基準報告（例如 reports/main/crawl-report.json）",
    )
    parser.add_argument(
        "current",
        type=Path,
        nargs="?",
        default=Path("reports/crawl-report.json"),
        help="目前報告（預設 reports/crawl-report.json）",
    )
    parser.add_argument(
        "--fail-on-new",
        action="store_true",
        help="若有新增問題則 exit 1（適合 CI 回歸）",
    )
    parser.add_argument("--json", action="store_true", help="輸出 JSON 差異")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="寫入 Markdown 比對報告",
    )
    parser.add_argument(
        "--fail-on-removed",
        action="store_true",
        help="若有 URL 從基準消失則 exit 1",
    )
    parser.add_argument(
        "--changed-urls-only",
        action="store_true",
        help="增量比對：僅對有變更的 URL 計算新增／修復問題（仍列出新增／消失 URL）",
    )
    args = parser.parse_args(argv)

    try:
        result = compare_files(
            args.baseline.resolve(),
            args.current.resolve(),
            changed_urls_only=args.changed_urls_only,
        )
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2

    if args.json:
        payload = {
            "baseline_pages": result.baseline_pages,
            "current_pages": result.current_pages,
            "new_issues": result.new_issues,
            "fixed_issues": result.fixed_issues,
            "urls_added": result.urls_added,
            "urls_removed": result.urls_removed,
            "changed_urls": result.changed_urls,
            "changed_urls_only": result.changed_urls_only,
            "status_changes": {
                u: {"before": old, "after": new}
                for u, (old, new) in result.status_changes.items()
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for line in result.summary_lines():
            print(line)

    if args.output:
        args.output.write_text(result.to_markdown(), encoding="utf-8")
        print(f"已寫入：{args.output}")

    code = 0
    if args.fail_on_new and result.new_issues:
        code = 1
    if args.fail_on_removed and result.urls_removed:
        code = 1
    return code
