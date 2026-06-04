"""
多站 crawl-report.json 比較儀表板（靜態 HTML）。
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from sitespider.issues import ISSUE_LABELS


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _site_label(report: dict, path: Path) -> str:
    return report.get("client_label") or report.get("start_url") or path.parent.name


def _issue_totals(report: dict) -> dict[str, int]:
    summary = report.get("summary_issues") or {}
    return {k: len(v) if isinstance(v, list) else 0 for k, v in summary.items()}


def build_multi_site_compare_html(
    report_paths: list[Path],
    *,
    title: str = "多站 SEO 比較",
) -> str:
    sites: list[dict] = []
    all_issue_keys: set[str] = set()

    for p in report_paths:
        data = _load(p.resolve())
        issues = _issue_totals(data)
        all_issue_keys |= set(issues.keys())
        pages = data.get("page_count") or len(data.get("pages") or {})
        sites.append(
            {
                "label": _site_label(data, p),
                "path": str(p.parent),
                "pages": pages,
                "issues": issues,
                "blocked": len(data.get("blocked_urls") or []),
            }
        )

    issue_rows = sorted(all_issue_keys, key=lambda k: -sum(s["issues"].get(k, 0) for s in sites))

    def th_cells() -> str:
        return "".join(f"<th>{escape(s['label'])}</th>" for s in sites)

    def td_issue(key: str) -> str:
        cells = []
        for s in sites:
            n = s["issues"].get(key, 0)
            cells.append(f"<td>{n if n else '—'}</td>")
        return "".join(cells)

    overview_rows = ""
    for metric, getter in [
        ("頁面數", lambda s: s["pages"]),
        ("robots 封鎖", lambda s: s["blocked"]),
    ]:
        tds = "".join(f"<td>{getter(s)}</td>" for s in sites)
        overview_rows += f"<tr><td>{metric}</td>{tds}</tr>\n"

    issue_table = ""
    for key in issue_rows[:40]:
        label = ISSUE_LABELS.get(key, key)
        issue_table += f"<tr><td>{escape(label)}</td>{td_issue(key)}</tr>\n"

    site_list = "".join(
        f"<li><strong>{escape(s['label'])}</strong> — {s['pages']} 頁<br>"
        f"<code>{escape(s['path'])}</code></li>"
        for s in sites
    )

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    body {{ font: 14px system-ui, sans-serif; margin: 1rem 2rem; background: #f6f6f6; color: #222; }}
    h1 {{ font-size: 1.35rem; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 1200px; background: #fff; margin: 1rem 0; }}
    th, td {{ border: 1px solid #ddd; padding: 0.45rem 0.6rem; text-align: left; }}
    th {{ background: #333; color: #fff; }}
    tr:nth-child(even) {{ background: #fafafa; }}
    code {{ font-size: 12px; }}
    ul {{ line-height: 1.6; }}
  </style>
</head>
<body>
  <h1>{escape(title)}</h1>
  <p>比較 {len(sites)} 份爬取報告（crawl-report.json）。僅供顧問內部或客戶簡報使用。</p>
  <h2>資料來源</h2>
  <ul>{site_list}</ul>
  <h2>總覽</h2>
  <table>
    <tr><th>指標</th>{th_cells()}</tr>
    {overview_rows}
  </table>
  <h2>問題類型（各站筆數）</h2>
  <table>
    <tr><th>問題</th>{th_cells()}</tr>
    {issue_table}
  </table>
</body>
</html>
"""


def export_multi_site_compare_html(
    report_paths: list[Path],
    output: Path,
    *,
    title: str = "多站 SEO 比較",
) -> Path:
    if len(report_paths) < 2:
        raise ValueError("至少需要 2 份 crawl-report.json")
    html = build_multi_site_compare_html(report_paths, title=title)
    output.write_text(html, encoding="utf-8")
    return output.resolve()
