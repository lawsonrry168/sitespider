"""CLI：建立客戶 Portal 分享連結。"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(
        prog="sitespider share-report",
        description="為報告目錄建立客戶只讀 Portal 連結",
    )
    parser.add_argument(
        "report_dir",
        type=Path,
        help="含 crawl-report.json 的報告目錄",
    )
    parser.add_argument("--tenant", default="default", help="租戶 ID")
    parser.add_argument("--job-id", default=None, help="任務 ID（預設目錄名）")
    parser.add_argument("--label", default=None, help="客戶顯示名稱")
    parser.add_argument("--ttl-days", type=int, default=30, help="連結有效天數（1–90）")
    args = parser.parse_args(argv)

    report_dir = args.report_dir.resolve()
    job_id = args.job_id or report_dir.name
    label = args.label or job_id
    ttl = max(1, min(int(args.ttl_days), 90))

    from sitespider.report_share import create_report_share

    try:
        share = create_report_share(
            tenant_id=args.tenant,
            job_id=job_id,
            report_dir=report_dir,
            label=label,
            ttl_days=ttl,
        )
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1

    public = os.environ.get("SITESPIDER_PUBLIC_URL", "").strip().rstrip("/")
    url = public + share["share_path"] if public else share["share_path"]
    print(f"客戶 Portal（{ttl} 天有效）：")
    print(f"  {url}")
    print(f"token: {share['token']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
