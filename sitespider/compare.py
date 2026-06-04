"""
比對兩次爬取報告 — 適合 CI 回歸或部署前後差異檢查。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

from sitespider.issues import ISSUE_LABELS


@dataclass
class CompareResult:
    baseline_pages: int
    current_pages: int
    new_issues: dict[str, list[str]] = field(default_factory=dict)
    fixed_issues: dict[str, list[str]] = field(default_factory=dict)
    persistent_issues: dict[str, list[str]] = field(default_factory=dict)
    urls_added: list[str] = field(default_factory=list)
    urls_removed: list[str] = field(default_factory=list)
    status_changes: dict[str, tuple[int, int]] = field(default_factory=dict)
    changed_urls: list[str] = field(default_factory=list)
    changed_urls_only: bool = False

    @property
    def has_regressions(self) -> bool:
        return bool(self.new_issues) or bool(self.urls_removed)

    def summary_lines(self) -> list[str]:
        lines = [
            f"基準 {self.baseline_pages} 頁 → 目前 {self.current_pages} 頁",
        ]
        if self.changed_urls_only:
            lines.append(f"增量模式：僅比對 {len(self.changed_urls)} 個有變更的 URL")
        if self.urls_added:
            lines.append(f"新增 URL：{len(self.urls_added)}")
        if self.urls_removed:
            lines.append(f"消失 URL：{len(self.urls_removed)}")
        if self.status_changes:
            lines.append(f"狀態碼變更：{len(self.status_changes)}")
        if self.new_issues:
            lines.append("新增問題：")
            for key, urls in sorted(self.new_issues.items(), key=lambda x: -len(x[1])):
                label = ISSUE_LABELS.get(key, key)
                lines.append(f"  + {label}: {len(urls)} 頁")
        if self.fixed_issues:
            lines.append("已修復：")
            for key, urls in sorted(self.fixed_issues.items(), key=lambda x: -len(x[1])):
                label = ISSUE_LABELS.get(key, key)
                lines.append(f"  - {label}: {len(urls)} 頁")
        if (
            not self.new_issues
            and not self.fixed_issues
            and not self.urls_added
            and not self.urls_removed
            and not self.status_changes
        ):
            lines.append("與基準相同（URL、狀態碼、問題集合均無變化）。")
        elif not self.new_issues and not self.fixed_issues:
            lines.append("問題類型無新增／修復（僅 URL 或狀態碼有變）。")
        return lines

    def to_markdown(self) -> str:
        lines = ["# SiteSpider 報告比對", ""]
        lines.extend(f"- {row}" for row in self.summary_lines())
        if self.urls_added:
            lines.extend(["", "## 新增 URL", ""])
            for u in self.urls_added[:50]:
                lines.append(f"- {u}")
            if len(self.urls_added) > 50:
                lines.append(f"- … 另有 {len(self.urls_added) - 50} 筆")
        if self.urls_removed:
            lines.extend(["", "## 消失 URL", ""])
            for u in self.urls_removed[:50]:
                lines.append(f"- {u}")
            if len(self.urls_removed) > 50:
                lines.append(f"- … 另有 {len(self.urls_removed) - 50} 筆")
        if self.status_changes:
            lines.extend(["", "## 狀態碼變更", "", "| URL | 基準 | 目前 |", "|-----|------|------|"])
            for u, (old, new) in list(self.status_changes.items())[:30]:
                lines.append(f"| {u} | {old} | {new} |")
        if self.new_issues:
            lines.extend(["", "## 新增問題", ""])
            for key, urls in sorted(self.new_issues.items(), key=lambda x: -len(x[1])):
                label = ISSUE_LABELS.get(key, key)
                lines.append(f"### {label} ({len(urls)})")
                for u in urls[:10]:
                    lines.append(f"- {u}")
        if self.fixed_issues:
            lines.extend(["", "## 已修復", ""])
            for key, urls in sorted(self.fixed_issues.items(), key=lambda x: -len(x[1])):
                label = ISSUE_LABELS.get(key, key)
                lines.append(f"### {label} ({len(urls)})")
                for u in urls[:10]:
                    lines.append(f"- {u}")
        return "\n".join(lines) + "\n"


def _issue_map(report: dict) -> dict[str, set[str]]:
    """url -> set(issue) 與 summary_issues 合併。"""
    per_url: dict[str, set[str]] = {}
    pages = report.get("pages") or {}
    for url, pdata in pages.items():
        issues = set(pdata.get("issues") or [])
        per_url[url] = issues
    summary = report.get("summary_issues") or {}
    for issue, urls in summary.items():
        for u in urls:
            per_url.setdefault(u, set()).add(issue)
    return per_url


def _page_status_map(report: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for url, pdata in (report.get("pages") or {}).items():
        if isinstance(pdata, dict):
            out[url] = int(pdata.get("status") or 0)
    return out


def urls_with_changes(baseline: dict, current: dict) -> list[str]:
    """URL 集合、狀態碼或問題集合有差異的網址。"""
    base_map = _issue_map(baseline)
    cur_map = _issue_map(current)
    base_status = _page_status_map(baseline)
    cur_status = _page_status_map(current)
    changed: set[str] = set()
    for url in set(base_map) | set(cur_map):
        if base_map.get(url, set()) != cur_map.get(url, set()):
            changed.add(url)
    for url in set(base_status) | set(cur_status):
        if base_status.get(url) != cur_status.get(url):
            changed.add(url)
    changed |= set(base_status) ^ set(cur_status)
    return sorted(changed)


def compare_reports(
    baseline: dict,
    current: dict,
    *,
    changed_urls_only: bool = False,
) -> CompareResult:
    base_map = _issue_map(baseline)
    cur_map = _issue_map(current)
    changed_list = urls_with_changes(baseline, current)
    changed_set = set(changed_list)
    all_urls = set(base_map) | set(cur_map)
    if changed_urls_only:
        all_urls = changed_set

    new_issues: dict[str, list[str]] = {}
    fixed_issues: dict[str, list[str]] = {}
    persistent: dict[str, list[str]] = {}

    for url in sorted(all_urls):
        before = base_map.get(url, set())
        after = cur_map.get(url, set())
        for issue in after - before:
            new_issues.setdefault(issue, []).append(url)
        for issue in before - after:
            fixed_issues.setdefault(issue, []).append(url)
        for issue in before & after:
            persistent.setdefault(issue, []).append(url)

    base_status = _page_status_map(baseline)
    cur_status = _page_status_map(current)
    base_urls = set(base_status)
    cur_urls = set(cur_status)
    status_changes: dict[str, tuple[int, int]] = {}
    for url in sorted(base_urls & cur_urls):
        old, new = base_status[url], cur_status[url]
        if old != new:
            status_changes[url] = (old, new)

    return CompareResult(
        baseline_pages=baseline.get("page_count") or len(baseline.get("pages") or {}),
        current_pages=current.get("page_count") or len(current.get("pages") or {}),
        new_issues=new_issues,
        fixed_issues=fixed_issues,
        persistent_issues=persistent,
        urls_added=sorted(cur_urls - base_urls),
        urls_removed=sorted(base_urls - cur_urls),
        status_changes=status_changes,
        changed_urls=changed_list,
        changed_urls_only=changed_urls_only,
    )


def load_report(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"找不到報告：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def compare_files(
    baseline_path: Path,
    current_path: Path,
    *,
    changed_urls_only: bool = False,
) -> CompareResult:
    return compare_reports(
        load_report(baseline_path),
        load_report(current_path),
        changed_urls_only=changed_urls_only,
    )


def export_compare_html(
    result: CompareResult,
    path: Path,
    *,
    title: str = "報告比對",
    baseline_label: str = "基準",
    current_label: str = "目前",
) -> Path:
    from sitespider.report_theme import REPORT_MAIN_OPEN, report_skip_link, report_styles_bundle

    def section_issues(heading: str, issues: dict[str, list[str]]) -> str:
        if not issues:
            return ""
        parts = [f"<h2>{escape(heading)}</h2>"]
        for key, urls in sorted(issues.items(), key=lambda x: -len(x[1])):
            label = ISSUE_LABELS.get(key, key)
            parts.append(f"<h3>{escape(label)} ({len(urls)})</h3><ul>")
            for u in urls[:20]:
                parts.append(f"<li><code>{escape(u)}</code></li>")
            if len(urls) > 20:
                parts.append(f"<li>… 另有 {len(urls) - 20} 筆</li>")
            parts.append("</ul>")
        return "\n".join(parts)

    summary_html = "".join(f"<li>{escape(line)}</li>" for line in result.summary_lines())
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>{report_styles_bundle()}</style>
</head>
<body class="report-page">
{report_skip_link()}
<header class="report-topbar"><strong>{escape(title)}</strong></header>
{REPORT_MAIN_OPEN}
<p class="status">{escape(baseline_label)} → {escape(current_label)}</p>
<ul class="compare-summary">{summary_html}</ul>
{section_issues("新增問題", result.new_issues)}
{section_issues("已修復", result.fixed_issues)}
</main>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path
