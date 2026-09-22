"""
由 report.pages URL 建構可折疊目錄樹（HTML details/summary）。
"""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport


def _insert_path(tree: dict[str, Any], parts: list[str], url: str, status: int) -> None:
    if not parts:
        tree.setdefault("_urls", []).append({"url": url, "status": status})
        return
    head, *tail = parts
    children = tree.setdefault("_children", {})
    node = children.setdefault(head, {})
    _insert_path(node, tail, url, status)


def build_path_tree(report: CrawlReport) -> dict[str, Any]:
    root: dict[str, Any] = {"_children": {}, "_urls": []}
    for url, page in sorted(report.pages.items()):
        parsed = urlparse(url)
        path = parsed.path or "/"
        parts = [p for p in path.strip("/").split("/") if p]
        if not parts:
            parts = ["/"]
        _insert_path(root, parts, url, page.status)
    return root


def _render_node(name: str, node: dict[str, Any], *, depth: int = 0) -> str:
    urls = node.get("_urls") or []
    children = node.get("_children") or {}
    label = escape(name)
    count = len(urls) + sum(len(v.get("_urls") or []) for v in _walk_counts(children))
    lines: list[str] = []

    if urls:
        for item in urls:
            u = escape(item["url"])
            st = item.get("status", "")
            lines.append(f'<li class="leaf"><a href="{u}">{u}</a> <span class="st">{st}</span></li>')

    for child_name in sorted(children.keys(), key=lambda x: (x != "/", x.lower())):
        child = children[child_name]
        inner = _render_node(child_name, child, depth=depth + 1)
        lines.append(
            f"<details><summary>{escape(child_name)}</summary><ul>{inner}</ul></details>"
        )

    if depth == 0 and not children and not urls:
        return ""
    return "\n".join(lines)


def _walk_counts(children: dict[str, Any]) -> list[dict]:
    out: list[dict] = []
    for node in children.values():
        out.extend(node.get("_urls") or [])
        out.extend(_walk_counts(node.get("_children") or {}))
    return out


def export_html_tree(report: CrawlReport, path) -> None:
    from pathlib import Path

    out = Path(path)
    tree = build_path_tree(report)
    host = escape(urlparse(report.start_url).netloc or report.start_url)
    body = _render_node("/", tree) or "<p>（無 URL）</p>"
    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8"/>
<title>SiteSpider 目錄樹 — {host}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 1.5rem; }}
details {{ margin: 0.25rem 0 0.25rem 1rem; }}
summary {{ cursor: pointer; font-weight: 600; }}
ul {{ list-style: none; padding-left: 1rem; }}
.st {{ color: #666; font-size: 0.85em; }}
a {{ word-break: break-all; }}
</style>
</head>
<body>
<h1>目錄樹 — {host}</h1>
<p>{len(report.pages)} URLs</p>
<div class="tree">{body}</div>
</body>
</html>"""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
