"""sitespider urls — 列出爬取報告內所有 URL。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sitespider urls",
        description="從 crawl-report.json 列出 URL（可匯出文字檔）",
    )
    parser.add_argument(
        "report",
        nargs="?",
        type=Path,
        default=Path("reports/crawl-report.json"),
    )
    parser.add_argument("-o", "--output", type=Path, help="寫入純文字 URL 列表")
    parser.add_argument(
        "--indexable-only",
        action="store_true",
        help="僅列出 Indexable",
    )
    args = parser.parse_args(argv)
    path = args.report.resolve()
    if not path.is_file():
        print(f"找不到：{path}", file=sys.stderr)
        return 2

    data = json.loads(path.read_text(encoding="utf-8"))
    urls = sorted(data.get("pages") or {})
    if args.indexable_only:
        urls = [
            u
            for u in urls
            if (data["pages"][u].get("indexability") or "") == "Indexable"
        ]

    lines = [u + "\n" for u in urls]
    if args.output:
        args.output.write_text("".join(lines), encoding="utf-8")
        print(f"已寫入 {len(urls)} 個 URL：{args.output}")
    else:
        for u in urls:
            print(u)
    return 0
