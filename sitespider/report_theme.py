"""Shared Washi Indigo styles and HTML fragments for exported reports."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from urllib.parse import quote, urlparse

_UI = Path(__file__).resolve().parent / "ui"

# Default consultant report accent (matches tokens.css --color-accent)
DEFAULT_BRAND_ACCENT = "#6ec9a0"

# (href, label, requires_ai) — requires_ai 僅在 out_dir 有對應檔案時可點
REPORT_NAV_ITEMS: tuple[tuple[str, str, bool], ...] = (
    ("REPORT-zh.html", "交付導覽", False),
    ("dashboard.html", "分析圖表", False),
    ("index.html", "站內技術報告", False),
    ("delivery-summary.html", "一頁摘要", False),
    ("seo-briefs.html", "SEO Brief", False),
    ("ai-hub.html", "AI 交付", True),
    ("ai-faq-cms.html", "FAQ 貼上", True),
    ("issue_heatmap.html", "熱力圖", False),
    ("link_graph.html", "內鏈圖", False),
    ("images-gallery.html", "圖片稽核", False),
    ("inspector.html", "URL 檢視", False),
)


def load_ui_css(name: str) -> str:
    path = _UI / name
    return path.read_text(encoding="utf-8")


def report_styles_bundle() -> str:
    """報告頁內嵌樣式（含返回按鈕 + 交付潤飾）。"""
    return (
        load_ui_css("report-pages.css")
        + "\n"
        + load_ui_css("report-polish.css")
        + "\n"
        + load_ui_css("report-layout.css")
        + "\n"
        + load_ui_css("ux-friendly.css")
        + "\n"
        + load_ui_css("site-reset.css")
        + "\n"
        + load_ui_css("nav-back.css")
    )


REPORT_MAIN_OPEN = '<main class="report-main" id="main-content" tabindex="-1">'


def report_skip_link() -> str:
    return '<a class="skip-link report-skip" href="#main-content">跳至主要內容</a>'


def _back_fallback(active: str | None, out_dir: Path | None) -> str:
    if active == "REPORT-zh.html":
        if out_dir and (out_dir / "index.html").is_file():
            return "index.html"
        if out_dir and (out_dir / "dashboard.html").is_file():
            return "dashboard.html"
        return "REPORT-zh.html"
    return "REPORT-zh.html"


def report_back_button(*, fallback: str = "REPORT-zh.html") -> str:
    """報告內返回（不走 history.back，避免回到空白爬取中心）。"""
    fb = escape(fallback, quote=True)
    return (
        f'<button type="button" class="ss-back" title="返回上一頁" aria-label="返回上一頁" '
        f"onclick=\"location.href='{fb}'\">← 返回</button>"
    )


def locate_report_job_dir(path: Path) -> Path | None:
    """由報告檔或目錄向上找到含 crawl-report.json 的任務目錄。"""
    p = path.resolve()
    if p.is_file():
        p = p.parent
    found: Path | None = None
    for _ in range(12):
        if (p / "crawl-report.json").is_file():
            found = p
        if p.parent == p:
            break
        p = p.parent
    if found is None or "reports" not in found.parts:
        return None
    return found


def _console_home_url(tenant: str, job_id: str) -> str:
    return f"/?tenant={quote(tenant, safe='')}&job={quote(job_id, safe='')}&step=3"


def _tenant_job_from_report_dir(job_dir: Path) -> tuple[str, str] | None:
    parts = job_dir.resolve().parts
    if "reports" not in parts:
        return None
    segs = parts[parts.index("reports") + 1 :]
    if len(segs) == 1:
        return "default", segs[0]
    if len(segs) >= 2:
        return segs[0], segs[1]
    return None


def console_home_href(out_dir: Path | None = None) -> str:
    """帶 job 參數回到爬取中心步驟 3，避免交付畫面消失。

    支援多租戶 ``reports/{tenant}/{job_id}/`` 與扁平 ``reports/{job_id}/``（如 123deal-smoke）。
    """
    if out_dir is None:
        return "/"
    try:
        job_dir = locate_report_job_dir(out_dir)
        if job_dir is not None:
            pair = _tenant_job_from_report_dir(job_dir)
            if pair:
                return _console_home_url(*pair)
        parts = out_dir.resolve().parts
        if "reports" not in parts:
            return "/"
        rest = parts[parts.index("reports") + 1 :]
        if len(rest) == 1:
            return _console_home_url("default", rest[0])
        if len(rest) == 2 and "." in rest[1]:
            return _console_home_url("default", rest[0])
        if len(rest) >= 2:
            return _console_home_url(rest[0], rest[1])
    except (OSError, ValueError):
        pass
    return "/"


def report_console_button(*, href: str | None = None, out_dir: Path | None = None) -> str:
    """返回 SiteSpider 爬取中心（透過 Web 控制台開啟報告時）。"""
    h = escape(href if href is not None else console_home_href(out_dir), quote=True)
    return (
        f'<a class="ss-back ss-console-home" href="{h}" '
        f'title="返回爬取中心" aria-label="返回爬取中心">⌂ 爬取中心</a>'
    )


def brand_mark_inline(*, width: int = 40, height: int = 40) -> str:
    """Inline SiteSpider mark for exported HTML (offline-safe)."""
    raw = (_UI / "brand-mark.svg").read_text(encoding="utf-8")
    return raw.replace("<svg ", f'<svg width="{width}" height="{height}" ', 1)


def favicon_link_tags() -> str:
    """Favicon + PWA tint for server-rendered HTML pages."""
    return (
        '<link rel="icon" href="/ui/brand-mark.svg" type="image/svg+xml">\n'
        '  <link rel="apple-touch-icon" href="/ui/apple-touch-icon.svg">\n'
        '  <meta name="theme-color" content="#0b0d12">'
    )


def console_stylesheet_tags(*extra: str) -> str:
    """Standard console CSS stack (paths only)."""
    names = ("tokens.css", "shell.css", "theme.css", "comfort-display.css", "nav-back.css", *extra)
    return "\n".join(f'  <link rel="stylesheet" href="/ui/{n}">' for n in names)


def _nav_file_exists(out_dir: Path, href: str) -> bool:
    return (out_dir / href).is_file()


def report_nav_links(
    out_dir: Path | None = None,
    *,
    active: str | None = None,
) -> str:
    """交付報告共用頂欄連結；out_dir 存在時略過未產生的檔案，AI 項改為鎖定提示。"""
    parts: list[str] = []
    ai_hint = "請在爬取中心 → AI 文案 → 產生 AI 文案後再開啟"
    for href, label, requires_ai in REPORT_NAV_ITEMS:
        if out_dir is not None:
            exists = _nav_file_exists(out_dir, href)
            if not exists:
                if requires_ai:
                    parts.append(
                        f'<span class="nav-locked" title="{escape(ai_hint)}">{escape(label)}</span>'
                    )
                continue
        cls = ' class="nav-active"' if active and active == href else ""
        parts.append(f'<a href="{escape(href)}"{cls}>{escape(label)}</a>')
    return '<nav class="report-nav" aria-label="報告頁面">' + "".join(parts) + "</nav>"


def report_topbar(
    out_dir: Path | None,
    page_title: str,
    *,
    active: str | None = None,
    site_url: str | None = None,
    meta_line: str | None = None,
) -> str:
    """統一報告頁頂欄：第一行情境（返回／爬取中心／標題），第二行文件導覽。"""
    mark = brand_mark_inline(width=32, height=32)
    sub = ""
    if meta_line:
        sub = f'<p class="report-topbar-meta">{escape(meta_line)}</p>'
    elif site_url:
        host = urlparse(site_url).netloc or site_url
        sub = f'<p class="report-topbar-meta"><span class="report-host">{escape(host)}</span></p>'

    view_site = ""
    if site_url and not meta_line:
        host = urlparse(site_url).netloc or site_url
        view_site = (
            f'<a class="report-view-site-btn" href="{escape(site_url)}" target="_blank" '
            f'rel="noopener noreferrer" title="{escape(site_url)}">↗ 檢視網站</a>'
            f'<span class="sr-only-report">（{escape(host)}）</span>'
        )

    fb = _back_fallback(active, out_dir)
    nav = report_nav_links(out_dir, active=active)
    return (
        f"{report_skip_link()}"
        f'<header class="report-topbar">'
        f'<div class="report-topbar-row report-topbar-context">'
        f'<div class="report-topbar-actions">'
        f"{report_back_button(fallback=fb)}"
        f"{report_console_button(out_dir=out_dir)}"
        f"</div>"
        f'<div class="report-brand-block">'
        f'<div class="report-brand-mark" aria-hidden="true">{mark}</div>'
        f"<div>"
        f'<div class="report-brand"><span>SiteSpider</span> · {escape(page_title)}</div>'
        f"{sub}"
        f"</div>"
        f"</div>"
        f'<div class="report-topbar-end">'
        f'<a class="report-guide-link" href="/guide" title="SiteSpider 完整使用說明">使用說明</a>'
        f"{view_site}"
        f"</div>"
        f"</div>"
        f'<div class="report-topbar-docs">'
        f'<span class="report-nav-label" aria-hidden="true">頁面</span>'
        f"{nav}"
        f"</div>"
        f"</header>"
        f"{_report_console_home_script(out_dir)}"
    )


def _report_console_home_script(out_dir: Path | None) -> str:
    """注入爬取中心 URL 與 nav-back（靜態報告、舊 HTML 皆適用）。"""
    href = console_home_href(out_dir)
    h_js = json.dumps(href)
    return (
        f"<script>window.__SS_CONSOLE_HOME={h_js};</script>\n"
        f'<script src="/ui/nav-back.js"></script>'
    )


def export_ai_placeholders(out_dir: Path) -> list[str]:
    """尚未執行 AI 文案時的說明頁，避免頂欄連結 404。"""
    if (out_dir / "ai-hub.html").is_file() and (out_dir / "ai-faq-cms.html").is_file():
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    css = report_styles_bundle()
    written: list[str] = []
    nav_dir = out_dir

    if not (out_dir / "ai-hub.html").is_file():
        hub = f"""<!DOCTYPE html>
<html lang="zh-TW"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 交付 — 尚未產生</title><style>{css}</style></head><body>
{report_topbar(nav_dir, "AI 交付", active="ai-hub.html")}
{REPORT_MAIN_OPEN}
  <h1>尚未產生 AI 文案</h1>
  <p class="lead">AI 交付包含：各頁 Title／Meta 建議、FAQ 草稿、JSON-LD、<code>llms.txt</code> 草稿等。請在<strong>爬取中心</strong>完成爬取後，到 <strong>AI 文案</strong> 頁設定 API 金鑰並按「產生 AI 文案」。</p>
  <div class="card">
    <h3>產出檔案（產生後）</h3>
    <ul>
      <li><code>ai-page-copy.html</code> — 標題與描述建議</li>
      <li><code>ai-faq.html</code> — FAQ 與 Schema 預覽</li>
      <li><code>ai-faq-cms.html</code> — FAQ 貼上版（給 Webflow／CMS）</li>
      <li><code>llms.txt.draft</code> — AI 網站說明草稿</li>
    </ul>
  </div>
  <p class="meta"><a href="REPORT-zh.html">← 交付導覽</a></p>
</main></body></html>"""
        (out_dir / "ai-hub.html").write_text(hub, encoding="utf-8")
        written.append("ai-hub.html")

    if not (out_dir / "ai-faq-cms.html").is_file():
        cms = f"""<!DOCTYPE html>
<html lang="zh-TW"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FAQ 貼上 — 尚未產生</title><style>{css}</style></head><body>
{report_topbar(nav_dir, "FAQ 貼上", active="ai-faq-cms.html")}
{REPORT_MAIN_OPEN}
  <h1>FAQ CMS 貼上版 — 尚未產生</h1>
  <p class="lead"><strong>FAQ CMS</strong> 是給 <strong>Webflow、WordPress、其他 CMS</strong> 用的 FAQ 區塊：內含可複製的 Rich Text 內容與 <code>FAQPage</code> JSON-LD，方便貼進頁面或全站 Custom Code，不必手打 HTML。</p>
  <p>請先在爬取中心執行「產生 AI 文案」；完成後此頁會顯示各頁 FAQ 的貼上區塊與一鍵複製按鈕。亦可從 <a href="ai-hub.html">AI 交付</a> 進入完整清單。</p>
  <p class="meta"><a href="REPORT-zh.html">← 交付導覽</a></p>
</main></body></html>"""
        (out_dir / "ai-faq-cms.html").write_text(cms, encoding="utf-8")
        written.append("ai-faq-cms.html")

    return written
