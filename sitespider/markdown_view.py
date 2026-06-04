"""將 Markdown 交付檔渲染為可讀 HTML（控制台 / Portal 預覽）。"""

from __future__ import annotations

import html
import re
from pathlib import Path


def _inline_md(text: str) -> str:
    s = html.escape(text, quote=True)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def render_markdown_html(text: str) -> str:
    """輕量 Markdown → HTML（足夠 REPORT-zh / priority_summary）。"""
    lines = text.splitlines()
    parts: list[str] = []
    in_ul = False
    in_ol = False

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            parts.append("</ul>")
            in_ul = False
        if in_ol:
            parts.append("</ol>")
            in_ol = False

    for line in lines:
        stripped = line.strip()
        if stripped == "---":
            close_lists()
            parts.append("<hr>")
            continue
        hm = re.match(r"^(#{1,6})\s+(.*)$", line)
        if hm:
            close_lists()
            level = len(hm.group(1))
            parts.append(f"<h{level}>{_inline_md(hm.group(2))}</h{level}>")
            continue
        om = re.match(r"^(\d+)\.\s+(.*)$", line)
        if om:
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            if not in_ol:
                parts.append("<ol>")
                in_ol = True
            parts.append(f"<li>{_inline_md(om.group(2))}</li>")
            continue
        um = re.match(r"^-\s+(.*)$", line)
        if um:
            if in_ol:
                parts.append("</ol>")
                in_ol = False
            if not in_ul:
                parts.append("<ul>")
                in_ul = True
            parts.append(f"<li>{_inline_md(um.group(1))}</li>")
            continue
        if not stripped:
            close_lists()
            continue
        close_lists()
        parts.append(f"<p>{_inline_md(line)}</p>")

    close_lists()
    return "\n".join(parts)


def markdown_page_html(
    body_md: str,
    *,
    title: str = "交付導覽",
    report_dir: Path | None = None,
) -> str:
    from sitespider.report_theme import (
        REPORT_MAIN_OPEN,
        load_ui_css,
        report_styles_bundle,
        report_topbar,
    )

    content = render_markdown_html(body_md)
    css = report_styles_bundle() + load_ui_css("comfort-display.css")
    safe_title = html.escape(title, quote=True)
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>{css}</style>
</head>
<body>
  {report_topbar(report_dir, safe_title)}
  {REPORT_MAIN_OPEN.replace('class="report-main"', 'class="md-page report-main"')}
    <article class="md-body">{content}</article>
  </main>
</body>
</html>"""


def markdown_file_page(path: Path, *, title: str | None = None) -> str:
    text = path.read_text(encoding="utf-8")
    page_title = title or path.stem.replace("-", " ")
    return markdown_page_html(text, title=page_title, report_dir=path.parent)
