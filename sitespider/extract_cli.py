#!/usr/bin/env python3
"""sitespider extract — 單頁快速擷取（借鑑 scrapling extract CLI）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

from sitespider.custom_extract import ExtractionRule, apply_extractions
from sitespider.adaptive_extract import apply_extractions_adaptive
from sitespider.fetch_policy import resolve_fetch_mode
from sitespider.optional_scrapling import fetch_html, scrapling_available


def _fetch_body(
    url: str,
    *,
    mode: str,
    use_scrapling: bool,
    stealth: bool,
    render_js: bool,
    timeout: float,
) -> tuple[str, str, int]:
    if use_scrapling or stealth:
        res = fetch_html(url, stealth=stealth or use_scrapling, timeout=timeout)
        if res.error and not res.html:
            print(res.error, file=sys.stderr)
            raise SystemExit(2)
        return res.html, res.final_url, res.status or 200

    fetch_mode = resolve_fetch_mode(
        url,
        policy="js" if render_js else mode,
        render_javascript=render_js,
    )
    if fetch_mode == "js":
        from sitespider.js_render import PlaywrightRenderer, playwright_available

        if not playwright_available():
            print("需要 Playwright：pip install 'sitespider[browser]' && playwright install chromium", file=sys.stderr)
            raise SystemExit(2)
        renderer = PlaywrightRenderer(user_agent="SiteSpider-Extract/1.0")
        try:
            page = renderer.fetch(url)
            if page.error or not page.html:
                print(page.error or "empty render", file=sys.stderr)
                raise SystemExit(2)
            return page.html, page.final_url, page.status or 200
        finally:
            renderer.close()

    resp = requests.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; SiteSpider-Extract/1.0)",
            "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
        },
    )
    resp.raise_for_status()
    return resp.text, resp.url, resp.status_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sitespider extract",
        description="抓取單一 URL 並擷取欄位（CSS / regex / JSON-LD）",
    )
    parser.add_argument("url", help="目標 URL")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="寫入檔案（.json / .txt / .md）；省略則 stdout",
    )
    parser.add_argument("--css", action="append", default=[], help="CSS 選擇器（可重複）")
    parser.add_argument("--regex", action="append", default=[], help="正則（可重複）")
    parser.add_argument(
        "--rules",
        type=Path,
        help="擷取規則 JSON（同 custom-extractions.example.json）",
    )
    parser.add_argument("--adaptive", action="store_true", help="啟用 JSON-LD / fallback 鏈")
    parser.add_argument(
        "--fetch-policy",
        choices=("http", "js", "auto"),
        default="http",
        help="http=requests；js=Playwright；auto=依路徑",
    )
    parser.add_argument("--render-js", action="store_true", help="等同 --fetch-policy js")
    parser.add_argument("--scrapling", action="store_true", help="使用 Scrapling fetcher（若已安裝）")
    parser.add_argument("--stealth", action="store_true", help="Scrapling StealthyFetcher")
    parser.add_argument("--body", action="store_true", help="僅輸出 body 文字")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(argv)

    rules: list[ExtractionRule] = []
    if args.rules and args.rules.is_file():
        raw = json.loads(args.rules.read_text(encoding="utf-8"))
        for item in raw if isinstance(raw, list) else []:
            if isinstance(item, dict):
                r = ExtractionRule.from_dict(item)
                if r:
                    rules.append(r)
    for i, css in enumerate(args.css):
        rules.append(ExtractionRule(name=f"css_{i + 1}", css=css))
    for i, rx in enumerate(args.regex):
        rules.append(ExtractionRule(name=f"regex_{i + 1}", regex=rx))

    html, final_url, status = _fetch_body(
        args.url,
        mode=args.fetch_policy,
        use_scrapling=args.scrapling,
        stealth=args.stealth,
        render_js=args.render_js,
        timeout=args.timeout,
    )

    if args.body and not rules:
        text = html
        if args.output:
            args.output.write_text(text, encoding="utf-8")
            print(f"已寫入 {args.output}", file=sys.stderr)
        else:
            print(text)
        return 0

    if rules:
        apply_fn = apply_extractions_adaptive if args.adaptive else apply_extractions
        fields = apply_fn(html, tuple(rules))
    else:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        body = soup.body.get_text("\n", strip=True) if soup.body else ""
        fields = {"body_text": body[:50000]}

    payload = {
        "url": args.url,
        "final_url": final_url,
        "status": status,
        "scrapling": scrapling_available(),
        "fields": fields,
    }

    if args.output:
        suffix = args.output.suffix.lower()
        if suffix == ".json":
            args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        elif suffix in (".txt", ".md"):
            lines = [f"# {final_url}", f"status: {status}", ""]
            for k, v in fields.items():
                lines.append(f"## {k}\n{v}\n")
            args.output.write_text("\n".join(lines), encoding="utf-8")
        else:
            args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已寫入 {args.output}", file=sys.stderr)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
