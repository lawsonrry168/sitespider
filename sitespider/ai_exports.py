"""
AI 協助匯出：Title/Meta 潤飾、FAQ schema、llms.txt 草稿、綜合建議。

由 `run_ai_polish()` 一次產生；控制台 POST `/api/job/{id}/ai-polish` 觸發。
"""

from __future__ import annotations

import csv
import time
import json
from dataclasses import asdict, dataclass
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sitespider.ai_client import AiConfig, chat_completion, chat_json, resolve_ai_config
from sitespider.priority import compute_priority_rows
from sitespider.report_analytics import compute_analytics
from sitespider.report_theme import REPORT_MAIN_OPEN, report_styles_bundle, report_topbar
from sitespider.page_url_match import resolve_page_url
from sitespider.seo_briefs import PageSeoBrief, build_page_briefs, generate_ai_suggestions_md

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport


@dataclass(frozen=True)
class CopyVariant:
    text: str
    chars: int
    ok: bool
    note: str


@dataclass(frozen=True)
class PageCopyDraft:
    url: str
    segment: str
    current_title: str
    current_meta: str
    titles: tuple[CopyVariant, ...]
    metas: tuple[CopyVariant, ...]
    h1: str


def _validate(text: str, kind: str) -> CopyVariant:
    n = len(text)
    if kind == "title":
        ok = 10 <= n <= 60
        note = "OK" if ok else ("過短" if n < 10 else "過長")
    else:
        ok = 50 <= n <= 160
        note = "OK" if ok else ("過短" if n < 50 else "過長")
    return CopyVariant(text=text, chars=n, ok=ok, note=note)


def _variants(raw_list: list[Any], kind: str) -> tuple[CopyVariant, ...]:
    out: list[CopyVariant] = []
    for item in raw_list or []:
        text = str(item.get("text") if isinstance(item, dict) else item).strip()
        if text:
            out.append(_validate(text, kind))
    return tuple(out[:3])


def _target_pages(report: CrawlReport, *, limit: int = 8) -> list[tuple[str, Any]]:
    rows = compute_priority_rows(report)
    picked: list[tuple[str, Any]] = []
    for row in rows:
        p = report.pages.get(row.url)
        if p and p.status == 200:
            picked.append((row.url, p))
        if len(picked) >= limit:
            break
    return picked


def generate_page_copy_drafts(report: CrawlReport, cfg: AiConfig, *, limit: int = 8) -> list[PageCopyDraft]:
    rows = compute_priority_rows(report)[:limit]
    pages: list[tuple[str, Any, str]] = []
    for row in rows:
        p = report.pages.get(row.url)
        if p and p.status == 200:
            pages.append((row.url, p, row.segment))
    if not pages:
        return []
    payload = []
    for url, p, segment in pages:
        payload.append(
            {
                "url": url,
                "title": p.title or "",
                "meta": p.meta_description or "",
                "h1": (p.h1[0] if p.h1 else ""),
                "segment": segment,
            }
        )
    data = chat_json(
        f"""站點 {report.start_url}
為以下 URL 產生繁中 SEO 文案。JSON 陣列，每項：
{{"url","segment","titles":[{{"text"}} x2],"metas":[{{"text"}} x2],"h1":"..."}}
Title 目標 50-60 字；Meta 120-155 字。

{json.dumps(payload, ensure_ascii=False)}""",
        cfg,
    )
    if not isinstance(data, list):
        data = data.get("pages") or []
    by_url: dict[str, dict] = {}
    for x in data:
        if not isinstance(x, dict):
            continue
        raw = str(x.get("url") or "").strip()
        if not raw:
            continue
        canon = resolve_page_url(raw, report.pages) or raw
        by_url.setdefault(canon, x)
    seg_map = {url: seg for url, _, seg in pages}
    drafts: list[PageCopyDraft] = []
    for url, p, _ in pages:
        row = by_url.get(url) or {}
        drafts.append(
            PageCopyDraft(
                url=url,
                segment=str(row.get("segment") or seg_map.get(url) or "other"),
                current_title=(p.title or ""),
                current_meta=(p.meta_description or ""),
                titles=_variants(row.get("titles") or [], "title"),
                metas=_variants(row.get("metas") or [], "meta"),
                h1=str(row.get("h1") or "").strip(),
            )
        )
    return drafts


def faq_json_ld(faqs: list[dict[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f["question"],
                "acceptedAnswer": {"@type": "Answer", "text": f["answer"]},
            }
            for f in faqs
            if f.get("question") and f.get("answer")
        ],
    }


def faq_body_html(faqs: list[dict[str, str]], *, heading: str = "常見問題") -> str:
    """Webflow / CMS Rich Text 可貼上的語意 HTML（不含 script）。"""
    if not faqs:
        return ""
    items = []
    for f in faqs:
        q = escape(str(f.get("question") or ""))
        a = escape(str(f.get("answer") or ""))
        if not q:
            continue
        items.append(
            f'  <div class="faq-item">\n'
            f'    <h3 class="faq-question">{q}</h3>\n'
            f'    <div class="faq-answer"><p>{a}</p></div>\n'
            f"  </div>"
        )
    if not items:
        return ""
    return (
        f'<section class="faq-section" aria-label="{escape(heading)}">\n'
        f"  <h2>{escape(heading)}</h2>\n"
        + "\n".join(items)
        + "\n</section>"
    )


def faq_schema_script_tag(json_ld: dict) -> str:
    if not json_ld.get("mainEntity"):
        return ""
    return (
        '<script type="application/ld+json">\n'
        + json.dumps(json_ld, ensure_ascii=False, indent=2)
        + "\n</script>"
    )


_COPY_BTN_JS = """
function copyText(btn, text) {
  navigator.clipboard.writeText(text).then(() => {
    const prev = btn.textContent;
    btn.textContent = '已複製';
    setTimeout(() => { btn.textContent = prev; }, 1200);
  }).catch(() => prompt('複製：', text));
}
"""

def generate_faq_drafts(report: CrawlReport, cfg: AiConfig, *, limit: int = 5) -> list[dict]:
    pages = _target_pages(report, limit=limit)
    payload = []
    for url, p in pages:
        payload.append(
            {
                "url": url,
                "title": p.title or "",
                "h1": (p.h1[0] if p.h1 else ""),
                "h2": (p.h2 or [])[:8],
                "h3": (p.h3 or [])[:8],
                "meta": (p.meta_description or "")[:200],
            }
        )
    data = chat_json(
        f"""依各頁 H2/H3 與主題，產生 3-5 組 FAQ（繁中）。JSON 陣列：
{{"url","faqs":[{{"question","answer"}}]}}
答案 2-4 句，可引用頁面已有資訊，勿捏造價格。

{json.dumps(payload, ensure_ascii=False)}""",
        cfg,
    )
    if not isinstance(data, list):
        data = data.get("pages") or []
    out: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        faqs = [f for f in (item.get("faqs") or []) if isinstance(f, dict)]
        raw = str(item.get("url") or "").strip()
        if not raw or not faqs:
            continue
        url = resolve_page_url(raw, report.pages) or raw
        out.append({"url": url, "faqs": faqs, "json_ld": faq_json_ld(faqs)})
    return out


def generate_llms_drafts(report: CrawlReport, cfg: AiConfig) -> dict[str, str]:
    analytics = compute_analytics(report)
    urls = sorted(report.pages.keys())[:40]
    sitemap_sample = list(report.sitemap_urls or [])[:20]
    prompt = f"""為以下網站撰寫 llms.txt 與 llms-full.txt 草稿（繁中為主，可夾英文專有名詞）。

站點：{report.start_url}
健康分：{analytics.get("health_score")} · 頁數：{len(report.pages)}
Top issues：{json.dumps((analytics.get("issues") or [])[:6], ensure_ascii=False)}
範例 URL：{json.dumps(urls[:15], ensure_ascii=False)}
Sitemap 樣本：{json.dumps(sitemap_sample, ensure_ascii=False)}

JSON 格式：{{"llms_txt":"...","llms_full_txt":"..."}}
llms.txt 簡短（<800 字）；llms-full.txt 含服務摘要、主要路徑、聯絡/政策提示（<2500 字）。"""
    data = chat_json(prompt, cfg, timeout=120)
    return {
        "llms.txt": str(data.get("llms_txt") or data.get("llms.txt") or "").strip(),
        "llms-full.txt": str(data.get("llms_full_txt") or data.get("llms-full.txt") or "").strip(),
    }


def export_page_copy_files(drafts: list[PageCopyDraft], out_dir: Path) -> list[str]:
    written: list[str] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    serial = [asdict(d) for d in drafts]
    for d in serial:
        for t in d.get("titles") or []:
            t["ok"] = bool(t.get("ok"))
        for m in d.get("metas") or []:
            m["ok"] = bool(m.get("ok"))
    (out_dir / "ai-page-copy.json").write_text(
        json.dumps(serial, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    written.append("ai-page-copy.json")

    with (out_dir / "ai-page-copy.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["URL", "Field", "Variant", "Text", "Chars", "Valid", "Note"])
        for d in drafts:
            for i, t in enumerate(d.titles, 1):
                w.writerow([d.url, "title", i, t.text, t.chars, "Yes" if t.ok else "No", t.note])
            for i, m in enumerate(d.metas, 1):
                w.writerow([d.url, "meta", i, m.text, m.chars, "Yes" if m.ok else "No", m.note])
            if d.h1:
                w.writerow([d.url, "h1", 1, d.h1, len(d.h1), "", ""])
    written.append("ai-page-copy.csv")

    css = report_styles_bundle()
    site_url = drafts[0].url if drafts else None
    rows = ""
    for d in drafts:
        def _vars(items: tuple[CopyVariant, ...], label: str) -> str:
            if not items:
                return f"<p class='meta'>無 {label} 建議</p>"
            bits = ""
            for i, v in enumerate(items, 1):
                cls = "ok" if v.ok else "bad"
                bits += (
                    f"<li><span class='badge {cls}'>{v.chars} 字 · {escape(v.note)}</span> "
                    f"{escape(v.text)}"
                    f"<button type='button' class='copy-btn' data-copy=\"{escape(v.text)}\">複製</button></li>"
                )
            return f"<ul>{bits}</ul>"

        h1_block = escape(d.h1 or "—")
        if d.h1:
            h1_block += f"<button type='button' class='copy-btn' data-copy=\"{escape(d.h1)}\">複製 H1</button>"
        rows += f"""
    <article class="card" style="margin-bottom:1rem">
      <h2 style="font-size:0.95rem;word-break:break-all"><a href="{escape(d.url)}">{escape(d.url)}</a></h2>
      <p class="meta">{escape(d.segment)}</p>
      <h3>Title 建議</h3>{_vars(d.titles, "title")}
      <h3>Meta 建議</h3>{_vars(d.metas, "meta")}
      <h3>H1</h3><p>{h1_block}</p>
    </article>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-TW"><head><meta charset="UTF-8"><title>AI Title / Meta</title>
<style>
{css}
.badge {{ font-family:var(--font-mono); font-size:0.68rem; padding:0.15rem 0.4rem; border-radius:4px; margin-right:0.35rem; }}
.badge.ok {{ background:var(--accent-dim); color:var(--accent); }}
.badge.bad {{ background:rgba(248,113,113,0.15); color:var(--danger); }}
h3 {{ font-size:0.72rem; text-transform:uppercase; letter-spacing:0.08em; color:var(--muted); margin:1rem 0 0.35rem; }}
.copy-btn {{ font-size:0.68rem; padding:0.25rem 0.5rem; margin-left:0.35rem; border-radius:6px; border:1px solid var(--border); background:var(--card); color:var(--accent); cursor:pointer; }}
</style></head><body>
{report_topbar(out_dir, "AI Title / Meta", active="ai-page-copy.html", site_url=site_url)}
{REPORT_MAIN_OPEN}<h1>AI 文案建議</h1><p class="lead">字元數已驗證：Title 10–60、Meta 50–160。點「複製」貼至 CMS。</p>{rows}</main>
<script>{_COPY_BTN_JS}
document.querySelectorAll('[data-copy]').forEach(btn => {{
  btn.addEventListener('click', () => copyText(btn, btn.getAttribute('data-copy')));
}});
</script>
</body></html>"""
    (out_dir / "ai-page-copy.html").write_text(html, encoding="utf-8")
    written.append("ai-page-copy.html")
    return written


def export_faq_files(faq_pages: list[dict], out_dir: Path) -> list[str]:
    if not faq_pages:
        return []
    (out_dir / "ai-faq.json").write_text(
        json.dumps(faq_pages, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    css = report_styles_bundle()
    site_url = (faq_pages[0].get("url") if faq_pages else None) or None
    blocks = ""
    cms_blocks = ""
    for page in faq_pages:
        faqs = page.get("faqs") or []
        uid = abs(hash(page.get("url", ""))) & 0xFFFF
        qa = "".join(
            f"<dt>{escape(f.get('question',''))}</dt><dd>{escape(f.get('answer',''))}</dd>"
            for f in faqs
        )
        ld = page.get("json_ld") or faq_json_ld(faqs)
        ld_str = json.dumps(ld, ensure_ascii=False, indent=2)
        body_html = faq_body_html(faqs)
        schema_tag = faq_schema_script_tag(ld)
        blocks += f"""
    <article class="card" style="margin-bottom:1rem">
      <h2 style="font-size:0.9rem;word-break:break-all">{escape(page.get('url',''))}</h2>
      <dl style="display:grid;grid-template-columns:1fr;gap:0.5rem;font-size:0.85rem">{qa}</dl>
      <h3 style="font-size:0.72rem;color:var(--muted);margin-top:1rem">FAQPage JSON-LD</h3>
      <pre class="copy-src" id="ld-{uid}" style="overflow:auto;font-size:0.72rem;background:var(--bg2);padding:0.75rem;border-radius:8px">{escape(ld_str)}</pre>
      <button type="button" class="copy-btn" data-copy-from="ld-{uid}">複製 JSON-LD</button>
    </article>"""
        cms_blocks += f"""
    <article class="card" style="margin-bottom:1.5rem">
      <h2 style="font-size:0.9rem;word-break:break-all">{escape(page.get('url',''))}</h2>
      <p class="meta">貼至 Webflow Rich Text / 自訂 code 區塊</p>
      <h3>FAQ 內容（body）</h3>
      <pre class="copy-src cms-pre" id="body-{uid}" style="overflow:auto;font-size:0.72rem;background:var(--bg2);padding:0.75rem;border-radius:8px;white-space:pre-wrap">{escape(body_html)}</pre>
      <button type="button" class="copy-btn" data-copy-from="body-{uid}">複製 FAQ HTML</button>
      <h3 style="margin-top:1rem">Schema（&lt;head&gt; 或 Webflow Custom Code）</h3>
      <pre class="copy-src cms-pre" id="schema-{uid}" style="overflow:auto;font-size:0.72rem;background:var(--bg2);padding:0.75rem;border-radius:8px;white-space:pre-wrap">{escape(schema_tag)}</pre>
      <button type="button" class="copy-btn" data-copy-from="schema-{uid}">複製 Schema script</button>
    </article>"""

    copy_js = _COPY_BTN_JS + """
document.querySelectorAll('[data-copy-from]').forEach(btn => {
  btn.addEventListener('click', () => {
    const el = document.getElementById(btn.getAttribute('data-copy-from'));
    if (el) copyText(btn, el.textContent);
  });
});
"""
    copy_css = """
.copy-btn { font-size:0.68rem; padding:0.3rem 0.55rem; margin:0.35rem 0.25rem 0 0; border-radius:6px; border:1px solid var(--border); background:var(--card); color:var(--accent); cursor:pointer; }
.copy-btn:hover { background:var(--accent-dim); }
"""

    html = f"""<!DOCTYPE html>
<html lang="zh-TW"><head><meta charset="UTF-8"><title>AI FAQ</title><style>{css}{copy_css}</style></head><body>
{report_topbar(out_dir, "AI FAQ", active="ai-faq.html", site_url=site_url)}
{REPORT_MAIN_OPEN}<h1>FAQ 草稿 + Schema</h1>
<p class="lead"><a href="ai-faq-cms.html">CMS 貼上版</a> · 複製 JSON-LD 至 head。</p>{blocks}</main>
<script>{copy_js}</script>
</body></html>"""
    (out_dir / "ai-faq.html").write_text(html, encoding="utf-8")

    cms_html = f"""<!DOCTYPE html>
<html lang="zh-TW"><head><meta charset="UTF-8"><title>FAQ CMS 區塊</title><style>{css}{copy_css}</style></head><body>
{report_topbar(out_dir, "FAQ 貼上", active="ai-faq-cms.html", site_url=site_url)}
{REPORT_MAIN_OPEN}
  <h1>FAQ — Webflow / CMS 貼上</h1>
  <p class="lead">先貼「FAQ 內容」至 Rich Text Embed；再貼「Schema」至頁面或全站 Custom Code。</p>
  {cms_blocks}
</main>
<script>{copy_js}</script>
</body></html>"""
    (out_dir / "ai-faq-cms.html").write_text(cms_html, encoding="utf-8")
    return ["ai-faq.json", "ai-faq.html", "ai-faq-cms.html"]


def export_llms_draft_files(drafts: dict[str, str], out_dir: Path) -> list[str]:
    written: list[str] = []
    for name, content in drafts.items():
        if not content:
            continue
        fname = name.replace("/", "-") + ".draft"
        (out_dir / fname).write_text(content + "\n", encoding="utf-8")
        written.append(fname)
    return written


def run_ai_polish(
    report: CrawlReport,
    out_dir: Path,
    *,
    site_label: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    provider_id: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    """執行完整 AI 匯出；回傳 {{written, errors}}。"""
    cfg = resolve_ai_config(
        api_key=api_key,
        model=model,
        provider_id=provider_id,
        base_url=base_url,
    )
    if not cfg:
        return {"ok": False, "error": "未設定 AI API key 或端點", "written": [], "errors": []}

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    errors: list[str] = []

    def _gap() -> None:
        if cfg.provider_id == "google":
            time.sleep(2.0)

    try:
        copies = generate_page_copy_drafts(report, cfg)
        written.extend(export_page_copy_files(copies, out_dir))
    except Exception as e:
        errors.append(f"page-copy: {e}")
    _gap()

    try:
        faqs = generate_faq_drafts(report, cfg)
        written.extend(export_faq_files(faqs, out_dir))
    except Exception as e:
        errors.append(f"faq: {e}")
    _gap()

    try:
        llms = generate_llms_drafts(report, cfg)
        written.extend(export_llms_draft_files(llms, out_dir))
    except Exception as e:
        errors.append(f"llms: {e}")

    try:
        briefs = build_page_briefs(report)
        md = generate_ai_suggestions_md(report, briefs, site_label=site_label)
        if md:
            (out_dir / "ai-suggestions.md").write_text(md, encoding="utf-8")
            written.append("ai-suggestions.md")
    except Exception as e:
        errors.append(f"suggestions: {e}")

    # 索引頁 + 更新 inspector（載入 AI sidecar）
    try:
        from sitespider.page_inspector import export_page_inspector

        export_page_inspector(report, out_dir / "inspector.html")
        written.append("inspector.html")
    except Exception as e:
        errors.append(f"inspector: {e}")

    try:
        from sitespider.ai_providers import provider_display_name

        _export_ai_hub_html(out_dir, written, site_label or report.start_url, cfg)
        written.append("ai-hub.html")
    except Exception as e:
        errors.append(f"hub: {e}")

    meta = {
        "provider_id": cfg.provider_id,
        "provider_name": provider_display_name(cfg.provider_id),
        "model": cfg.model,
        "model_requested": cfg.model_requested or cfg.model,
        "model_resolved": cfg.model,
        "written": list(dict.fromkeys(written)),
        "errors": errors,
        "ok": not errors or bool(written),
    }
    try:
        (out_dir / "ai-polish-meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written.append("ai-polish-meta.json")
        _export_ai_polish_meta_html(out_dir, meta)
        written.append("ai-polish-meta.html")
    except OSError:
        pass

    return {
        "ok": meta["ok"],
        "written": list(dict.fromkeys(written)),
        "errors": errors,
        "model": cfg.model,
        "provider_id": cfg.provider_id,
        "provider_name": meta["provider_name"],
    }


def _export_ai_polish_meta_html(out_dir: Path, meta: dict) -> None:
    from sitespider.ai_meta_display import ai_model_caption, enrich_ai_meta

    meta = enrich_ai_meta(meta)
    css = report_styles_bundle()
    files = meta.get("written") or []
    errs = meta.get("errors") or []
    lis = "".join(f"<li><code>{escape(str(f))}</code></li>" for f in files)
    err_block = ""
    if errs:
        err_block = "<h3>警告</h3><ul>" + "".join(
            f"<li>{escape(str(e))}</li>" for e in errs
        ) + "</ul>"
    html = f"""<!DOCTYPE html>
<html lang="zh-TW"><head><meta charset="UTF-8"><title>AI 執行紀錄</title><style>{css}</style></head><body>
{report_topbar(out_dir, "AI 紀錄", active="ai-polish-meta.html")}
{REPORT_MAIN_OPEN}
  <h1>AI 文案執行紀錄</h1>
  <p class="lead">{ai_model_caption(meta, html=True)} · 狀態 <code>{'完成' if meta.get('ok') else '部分失敗'}</code></p>
  <div class="card"><h3>產出檔案</h3><ul>{lis or '<li>無</li>'}</ul>{err_block}</div>
  <p class="meta"><a href="ai-hub.html">→ AI 交付中心</a></p>
</main></body></html>"""
    (out_dir / "ai-polish-meta.html").write_text(html, encoding="utf-8")


def _export_ai_hub_html(out_dir: Path, files: list[str], label: str, cfg: AiConfig) -> None:
    from sitespider.ai_meta_display import ai_model_caption
    from sitespider.ai_providers import provider_display_name

    meta_stub = {
        "provider_id": cfg.provider_id,
        "provider_name": provider_display_name(cfg.provider_id),
        "model_requested": cfg.model_requested or cfg.model,
        "model_resolved": cfg.model,
    }
    lead = ai_model_caption(meta_stub, html=True)
    css = report_styles_bundle()
    links = {
        "ai-hub.html": "AI 總覽",
        "ai-page-copy.html": "Title / Meta",
        "ai-faq.html": "FAQ + Schema",
        "ai-faq-cms.html": "FAQ CMS 貼上",
        "ai-suggestions.md": "綜合建議 MD",
        "seo-briefs.html": "規則型 Brief",
        "llms.txt.draft": "llms.txt 草稿",
        "llms-full.txt.draft": "llms-full.txt 草稿",
        "ai-polish-meta.json": "AI 執行紀錄 JSON",
        "ai-polish-meta.html": "AI 執行紀錄",
    }
    lis = ""
    for f in files:
        if f in links:
            lis += f'<li><a href="{escape(f)}">{escape(links[f])}</a> <code>{escape(f)}</code></li>'
    html = f"""<!DOCTYPE html>
<html lang="zh-TW"><head><meta charset="UTF-8"><title>AI Hub</title><style>{css}</style></head><body>
{report_topbar(out_dir, "AI 交付", active="ai-hub.html", site_url=label)}
{REPORT_MAIN_OPEN}
  <h1>{escape(label)}</h1>
  <p class="lead">{lead}</p>
  <div class="card"><ul class="link-list">{lis or '<li>尚無 AI 產物</li>'}</ul></div>
</main></body></html>"""
    (out_dir / "ai-hub.html").write_text(html, encoding="utf-8")
