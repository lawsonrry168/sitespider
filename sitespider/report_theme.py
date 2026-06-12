"""Shared Washi Indigo styles and HTML fragments for exported reports."""

from __future__ import annotations

import json
import re
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
    """報告頁內嵌樣式（含返回按鈕 + 交付潤飾 + 護眼字級/配色）。"""
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
        + "\n"
        + load_ui_css("comfort-display.css")
        + "\n"
        + load_ui_css("report-theme-unified.css")
    )


REPORT_MAIN_OPEN = '<main class="report-main" id="main-content" tabindex="-1">'


def report_theme_init_script() -> str:
    """與控制台同步深/淺色；預設深色。"""
    return (
        "<script>"
        '(function(){try{document.documentElement.setAttribute("data-theme",'
        'localStorage.getItem("sitespider-theme")||"dark");}catch(e){'
        'document.documentElement.setAttribute("data-theme","dark");}})();'
        "</script>"
    )


REPORT_TOKEN_BRIDGE_STYLE = (
    '<style id="ss-report-token-bridge">'
    ":root{"
    "--bg:#10141c;--bg2:#141a24;--card:#1c2432;--border:#2e384a;"
    "--text:#d8d6d0;--muted:#7d8796;--accent:#6aab8f;"
    "--link:#7ab89a;--link-hover:#94c9ad;"
    "--accent-dim:rgba(106,171,143,.1);"
    "--color-bg:var(--bg);--color-bg-subtle:var(--bg2);"
    "--color-surface:var(--card);--color-border:var(--border);"
    "--color-text:var(--text);--color-text-muted:var(--muted);"
    "--color-accent:var(--accent);--color-link:var(--link);"
    "--color-link-hover:var(--link-hover);"
    "--color-accent-muted:var(--accent-dim);"
    "--color-warn:#d4b86a;--color-danger:#d99a9a;"
    "}"
    "html{color-scheme:dark;background:var(--bg)}"
    "a{color:var(--link)}a:hover{color:var(--link-hover)}"
    ".report-nav a.nav-active{color:var(--accent)!important;"
    "border-color:var(--border)!important;background:var(--accent-dim)!important}"
    "a.report-guide-link:hover{background:var(--accent-dim)!important;"
    "color:var(--link-hover)!important}"
    '[data-theme="light"]{'
    "--bg:#f5f3ef;--bg2:#ece9e2;--card:#fff;--border:#d8d2c6;"
    "--text:#141820;--muted:#6a7384;--accent:#2a7d5a;"
    "color-scheme:light"
    "}"
    "</style>"
)


def inject_report_theme_toggle(html: str) -> str:
    """舊版報告 HTML 補上主題按鈕。"""
    if "theme-toggle" in html:
        return html
    btn = report_theme_toggle_button()
    marker = '<div class="report-topbar-end">'
    if marker in html:
        return html.replace(marker, marker + btn, 1)
    return html


def patch_report_html_theme(html: str) -> str:
    """舊版嵌入報告補齊 tokens、護眼、全頁主題一致（無需重新爬取）。"""
    needs_head = (
        "ss-report-token-bridge" not in html
        or "ss-eye-comfort" not in html
        or "ss-report-unified" not in html
        or (
            "ss-analytics-overrides" not in html
            and (
                "score-card" in html
                or "graph-toolbar" in html
                or "heatmap-legend" in html
            )
        )
    )
    needs_toggle = "report-theme-toggle.js" not in html
    if not needs_head and not needs_toggle and "theme-toggle" in html:
        return html

    patch = ""
    if "ss-report-token-bridge" not in html:
        patch += REPORT_TOKEN_BRIDGE_STYLE
    if "ss-eye-comfort" not in html:
        patch += (
            f'<style id="ss-eye-comfort">\n{load_ui_css("comfort-display.css")}\n</style>'
        )
    if "ss-report-unified" not in html:
        patch += (
            f'<style id="ss-report-unified">\n'
            f'{load_ui_css("report-theme-unified.css")}\n</style>'
        )
    if "score-card" in html and "ss-analytics-overrides" not in html:
        patch += (
            f'<style id="ss-analytics-overrides">\n'
            f'{load_ui_css("analytics-theme-overrides.css")}\n</style>'
        )
    patch += report_theme_init_script()

    out = html
    if needs_head and "</head>" in out:
        out = out.replace("</head>", patch + "\n</head>", 1)
    elif needs_head and "<body" in out:
        out = out.replace("<body", patch + "\n<body", 1)
    elif needs_head:
        out = patch + out

    out = inject_report_theme_toggle(out)

    if needs_toggle:
        script = '<script src="/ui/report-theme-toggle.js"></script>'
        if "</body>" in out:
            out = out.replace("</body>", script + "\n</body>", 1)
        else:
            out += script
    return out


def report_theme_toggle_button() -> str:
    """報告頂欄深/淺色切換（與控制台共用 localStorage）。"""
    return (
        '<button type="button" class="theme-toggle report-theme-toggle" '
        'title="切換淺色" aria-label="切換主題">◑</button>'
    )


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
        '  <meta name="theme-color" content="#10141c">'
    )


def console_stylesheet_tags(*extra: str) -> str:
    """Standard console CSS stack (paths only)."""
    names = (
        "tokens.css",
        "shell.css",
        "theme.css",
        "comfort-display.css",
        "nav-back.css",
        *extra,
    )
    return "\n".join(f'  <link rel="stylesheet" href="/ui/{n}">' for n in names)


def _nav_file_exists(out_dir: Path, href: str) -> bool:
    return _nav_resolve_href(out_dir, href) is not None


def _nav_resolve_href(out_dir: Path, href: str) -> str | None:
    """實際可開啟的檔名；交付導覽允許 .html / .md 互換。"""
    if (out_dir / href).is_file():
        return href
    if href == "REPORT-zh.html" and (out_dir / "REPORT-zh.md").is_file():
        return "REPORT-zh.md"
    if href == "REPORT-zh.md" and (out_dir / "REPORT-zh.html").is_file():
        return "REPORT-zh.html"
    return None


# 頂欄永遠保留（即使檔案暫缺也顯示鎖定，避免「交付導覽消失」）
_NAV_ALWAYS_SHOW = frozenset({"REPORT-zh.html"})


def ensure_report_zh_files(out_dir: Path) -> list[str]:
    """若 crawl-report.json 在但交付導覽遺失（常見 iCloud 同步），嘗試補產。"""
    written: list[str] = []
    if not out_dir.is_dir():
        return written
    if (out_dir / "REPORT-zh.html").is_file() and (out_dir / "REPORT-zh.md").is_file():
        return written
    crawl = out_dir / "crawl-report.json"
    if not crawl.is_file():
        return written
    try:
        from sitespider.branding import Branding
        from sitespider.report_load import load_report_json
        from sitespider.report_readme import export_report_readme_html, export_report_readme_md

        report = load_report_json(crawl)
        label = report.start_url
        summary_path = out_dir / "summary.json"
        if summary_path.is_file():
            try:
                meta = json.loads(summary_path.read_text(encoding="utf-8"))
                label = meta.get("site_label") or meta.get("label") or label
            except (json.JSONDecodeError, OSError):
                pass
        brand = Branding()
        if not (out_dir / "REPORT-zh.md").is_file():
            export_report_readme_md(report, out_dir / "REPORT-zh.md", site_label=label, branding=brand)
            written.append("REPORT-zh.md")
        if not (out_dir / "REPORT-zh.html").is_file():
            export_report_readme_html(
                report,
                out_dir / "REPORT-zh.html",
                site_label=label,
                branding=brand,
                out_dir=out_dir,
            )
            written.append("REPORT-zh.html")
    except Exception:
        pass
    return written


def report_nav_links(
    out_dir: Path | None = None,
    *,
    active: str | None = None,
) -> str:
    """交付報告共用頂欄連結；out_dir 存在時略過未產生的檔案，AI 項改為鎖定提示。"""
    parts: list[str] = []
    ai_hint = "請在爬取中心 → AI 文案 → 產生 AI 文案後再開啟"
    guide_missing = "交付導覽檔案遺失 — 請在爬取中心重新開啟任務或重新爬取"
    for href, label, requires_ai in REPORT_NAV_ITEMS:
        resolved = _nav_resolve_href(out_dir, href) if out_dir is not None else href
        if out_dir is not None and resolved is None:
            if requires_ai:
                parts.append(
                    f'<span class="nav-locked" title="{escape(ai_hint)}">{escape(label)}</span>'
                )
            elif href in _NAV_ALWAYS_SHOW:
                parts.append(
                    f'<span class="nav-locked" title="{escape(guide_missing)}">{escape(label)}</span>'
                )
            continue
        link = resolved if isinstance(resolved, str) else href
        is_active = active and (active == href or active == link)
        cls = ' class="nav-active"' if is_active else ""
        parts.append(f'<a href="{escape(link)}"{cls}>{escape(label)}</a>')
    return '<nav class="report-nav" aria-label="報告頁面">' + "".join(parts) + "</nav>"


def patch_report_nav(html: str, fp: Path) -> str:
    """舊版報告 HTML：依磁碟現況重算頂欄導覽（避免匯出當下缺檔導致交付導覽消失）。"""
    if 'class="report-nav"' not in html:
        return html
    job_dir = locate_report_job_dir(fp)
    if job_dir is None:
        return html
    ensure_report_zh_files(job_dir)
    fresh = report_nav_links(job_dir, active=fp.name)
    return re.sub(
        r'<nav class="report-nav"[^>]*>.*?</nav>',
        fresh,
        html,
        count=1,
        flags=re.DOTALL,
    )


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
        f"{report_theme_init_script()}"
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
        f"{report_theme_toggle_button()}"
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
        f'<script src="/ui/report-theme-toggle.js"></script>\n'
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
