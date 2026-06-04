"""CLI：對既有報告目錄執行 AI 潤飾。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _print_providers() -> None:
    from sitespider.ai_providers import providers_public_json

    for p in providers_public_json():
        if p["id"] == "custom":
            continue
        print(f"{p['id']}\t{p['name']}\tdefault={p['default_model']}")
        for m in p["models"]:
            print(f"  · {m}")
        print()


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(
        prog="sitespider ai-polish",
        description="對 crawl 報告目錄執行 AI 文案（Title/Meta、FAQ、llms.txt）",
    )
    parser.add_argument(
        "report_dir",
        type=Path,
        nargs="?",
        help="含 crawl-report.json 的報告目錄",
    )
    parser.add_argument("--label", default=None, help="站點顯示名稱")
    parser.add_argument(
        "--model",
        default=None,
        help="模型 ID（預設依平台）",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="AI 平台 ID（openai、anthropic、deepseek、openrouter…）",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="自訂 OpenAI 相容 API Base URL",
    )
    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="列出所有 AI 平台與模型後結束",
    )
    args = parser.parse_args(argv)

    if args.list_providers:
        _print_providers()
        return 0

    if not args.report_dir:
        parser.error("請指定 report_dir，或使用 --list-providers")

    report_dir = args.report_dir.resolve()
    crawl_json = report_dir / "crawl-report.json"
    if not crawl_json.is_file():
        print(f"找不到 {crawl_json}", file=sys.stderr)
        return 1

    from sitespider.ai_exports import run_ai_polish
    from sitespider.report_load import load_report_json

    report = load_report_json(crawl_json)
    label = args.label or report.start_url
    result = run_ai_polish(
        report,
        report_dir,
        site_label=label,
        model=args.model,
        provider_id=args.provider,
        base_url=args.base_url,
    )
    if result.get("error"):
        print(result["error"], file=sys.stderr)
    prov = result.get("provider_name") or result.get("provider_id") or "AI"
    model = result.get("model") or "—"
    print(f"平台：{prov} · 模型：{model}")
    for f in result.get("written") or []:
        print(f"  · {f}")
    for err in result.get("errors") or []:
        print(f"  ! {err}", file=sys.stderr)
    if result.get("ok"):
        print(f"\n完成 → {report_dir / 'ai-hub.html'}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
