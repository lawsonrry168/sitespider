"""稽核報告檢查（CI / 命令列）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ISSUE_LABELS = {
    "missing_title": "缺少 title",
    "missing_meta_description": "缺少 meta description",
    "missing_h1": "缺少 H1",
    "multiple_h1": "多個 H1",
    "duplicate_title": "重複 title",
    "http_error": "HTTP 錯誤",
    "orphan_page": "孤立頁",
    "blocked_by_robots": "robots 封鎖",
    "meta_noindex": "noindex（允許）",
    "missing_og_tags": "缺少 Open Graph",
    "missing_json_ld": "缺少 JSON-LD",
}

LIGHTHOUSE_MIN = {
    "performance": 50,
    "accessibility": 85,
    "best_practices": 85,
    "seo": 90,
}


def run_audit_check(report_path: Path, *, allow_noindex: bool = True) -> int:
    if not report_path.exists():
        print(f"找不到報告：{report_path}", file=sys.stderr)
        return 2

    report = json.loads(report_path.read_text(encoding="utf-8"))
    issues = report.get("summary_issues", {})
    allowed = {"meta_noindex"} if allow_noindex else set()
    failed = {k: v for k, v in issues.items() if k not in allowed}

    if failed:
        print("SEO 稽核未通過：", file=sys.stderr)
        for key, urls in sorted(failed.items(), key=lambda x: -len(set(x[1]))):
            label = ISSUE_LABELS.get(key, key)
            print(f"  · {label}: {len(set(urls))} 頁", file=sys.stderr)
        return 1

    n = report.get("page_count", 0)
    print(f"SEO 稽核通過：{n} 頁")
    return 0


def run_lighthouse_check(report_dir: Path) -> int:
    crawl_json = report_dir / "crawl-report.json"
    if not crawl_json.exists():
        print("略過 Lighthouse 門檻（無 crawl-report.json）")
        return 0

    data = json.loads(crawl_json.read_text(encoding="utf-8"))
    lh = data.get("lighthouse") or {}
    if not lh:
        print("略過 Lighthouse 門檻（無 Lighthouse 資料）")
        return 0

    failed = []
    for url, scores in lh.items():
        name = urlparse_tail(url)
        for key, minimum in LIGHTHOUSE_MIN.items():
            val = scores.get(key)
            if val is None:
                if scores.get("error"):
                    failed.append(f"{name}: {str(scores['error'])[:80]}")
                continue
            if val < minimum:
                failed.append(f"{name} {key}={val} < {minimum}")

    if failed:
        print("Lighthouse 未達門檻：", file=sys.stderr)
        for line in failed:
            print(f"  · {line}", file=sys.stderr)
        return 1

    print(f"Lighthouse 通過：{len(lh)} URL")
    return 0


def urlparse_tail(url: str) -> str:
    return url.rstrip("/").split("/")[-1] or url


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="檢查 SiteSpider 爬取報告")
    parser.add_argument("report", nargs="?", type=Path, default=Path("reports/crawl-report.json"))
    parser.add_argument("--lighthouse", action="store_true", help="一併檢查 Lighthouse 分數")
    args = parser.parse_args(argv)

    code = run_audit_check(args.report.resolve())
    if code != 0:
        return code
    if args.lighthouse:
        return run_lighthouse_check(args.report.resolve().parent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
