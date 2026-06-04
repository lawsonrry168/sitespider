"""
SEO / GEO 文案 brief — 規則型建議 + 可選 LLM 潤飾。

- 無 API key：依爬蟲資料產生 `seo-briefs.md` / `.json`（繁中、可執行）
- 設各平台 API Key 環境變數（如 `OPENAI_API_KEY`、`DEEPSEEK_API_KEY`）或 `SITESPIDER_AI_API_KEY`：可觸發完整 AI 匯出
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING

from sitespider.ai_client import ai_configured, chat_completion, resolve_ai_config
from sitespider.geo_audit import compute_geo_rows
from sitespider.issues import ISSUE_LABELS
from sitespider.priority import compute_priority_rows
from sitespider.report_theme import REPORT_MAIN_OPEN, report_styles_bundle, report_topbar

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport


@dataclass(frozen=True)
class PageSeoBrief:
    url: str
    priority_score: int
    geo_score: int
    segment: str
    money_page: bool
    word_count: int
    current_title: str
    current_meta: str
    current_h1: str
    issues: tuple[str, ...]
    title_advice: str
    meta_advice: str
    h1_advice: str
    geo_advice: str
    content_advice: str


def _title_advice(title: str, issues: set[str]) -> str:
    if "missing_title" in issues:
        return "補上 title：品牌名 + 頁面主題 + 地區/品類，控制在 50–60 字元，核心關鍵字靠前。"
    if "title_too_long" in issues:
        return f"目前 {len(title)} 字元偏長，刪減次要詞，保留主關鍵字與品牌，目標 ≤60 字元。"
    if "title_too_short" in issues:
        return "title 過短，加入服務/品類與差異化賣點，避免只有品牌名。"
    if "duplicate_title" in issues:
        return "與站內其他頁重複：加入頁面獨有關鍵字（品項、地區、語系），勿共用同一 title。"
    if "title_equals_h1" in issues:
        return "title 與 H1 完全相同；title 可更偏搜尋意圖，H1 可更偏轉換文案。"
    if not title.strip():
        return "補上 title。"
    return "維持現有方向，可 A/B 測試加入數字或地域詞提升 CTR。"


def _meta_advice(meta: str, issues: set[str]) -> str:
    if "missing_meta_description" in issues:
        return "撰寫 120–155 字元 meta：一句痛點 + 一句解法 + 輕 CTA，勿與 title 逐字重複。"
    if "meta_description_too_long" in issues:
        return f"目前 {len(meta)} 字元，精簡至 160 字內，前 80 字放最重要訊息（行動裝置截斷）。"
    if "meta_description_too_short" in issues:
        return "meta 過短，補充服務範圍、信任訊號（如年資、評價）與下一步行動。"
    if "duplicate_meta_description" in issues:
        return "與其他頁重複：改寫為該頁專屬摘要，突出此 URL 獨有內容。"
    return "可加入 FAQ 式問句或限時優惠，提升摘要點擊率。"


def _h1_advice(h1: str, issues: set[str]) -> str:
    if "missing_h1" in issues:
        return "每頁一個 H1，清楚描述頁面主題；與 title 互補而非複製。"
    if "multiple_h1" in issues:
        return "頁面僅保留一個 H1，其餘改 H2/H3 階層。"
    if not h1.strip():
        return "補上 H1。"
    return "H1 可更口語、更偏轉換；確認與首段文字呼應。"


def _geo_advice(
    geo_score: int,
    *,
    has_faq: bool,
    has_schema: bool,
    word_count: int,
    issues: set[str],
) -> str:
    tips: list[str] = []
    if geo_score < 60:
        tips.append("GEO 分數偏低，優先補齊可被 AI 引用的結構化內容。")
    if not has_schema:
        tips.append("加入 JSON-LD（依頁型：Product / LocalBusiness / Article）。")
    if not has_faq:
        tips.append("可新增 FAQ 區塊 + FAQPage schema，利於 AI 摘要引用。")
    if word_count < 200:
        tips.append(f"字數 {word_count} 偏少，補充常見問題、規格、使用情境（目標 ≥200 字）。")
    if "missing_og_tags" in issues:
        tips.append("補 Open Graph（og:title / description / image）改善分享與 AI 預覽。")
    if "missing_json_ld" in issues or "json_ld_missing_type" in issues:
        tips.append("依 audit 規則補齊預期 @type（見 structured_data.csv）。")
    return " ".join(tips) if tips else "GEO 訊號良好，可定期更新 FAQ 與 HowTo 內容。"


def _content_advice(word_count: int, issues: set[str], segment: str) -> str:
    if "thin_content" in issues:
        target = 400 if segment in ("product", "service", "conversion") else 300
        return f"內容過薄（{word_count} 字），{segment} 頁建議 ≥{target} 字：規格、案例、常見問題、內鏈至相關頁。"
    if word_count < 150:
        return "段落過短，增加小標、列表與內部連結，提升主題完整度。"
    return "可加入摘要段（首 100 字直接回答搜尋意圖），利於 featured snippet / AI 引用。"


def build_page_briefs(report: CrawlReport, *, limit: int = 15) -> list[PageSeoBrief]:
    geo_map = {r.url: r for r in compute_geo_rows(report)}
    rows = compute_priority_rows(report)[:limit]
    briefs: list[PageSeoBrief] = []

    for row in rows:
        p = report.pages.get(row.url)
        if not p or p.status != 200:
            continue
        geo = geo_map.get(row.url)
        issue_codes = set(p.issues or [])
        issue_labels = tuple(ISSUE_LABELS.get(i, i) for i in sorted(issue_codes))
        title = (p.title or "").strip()
        meta = (p.meta_description or "").strip()
        h1 = (p.h1[0] if p.h1 else "").strip()

        briefs.append(
            PageSeoBrief(
                url=row.url,
                priority_score=row.score,
                geo_score=row.geo_score,
                segment=row.segment,
                money_page=row.money_page,
                word_count=p.word_count,
                current_title=title,
                current_meta=meta,
                current_h1=h1,
                issues=issue_labels,
                title_advice=_title_advice(title, issue_codes),
                meta_advice=_meta_advice(meta, issue_codes),
                h1_advice=_h1_advice(h1, issue_codes),
                geo_advice=_geo_advice(
                    row.geo_score,
                    has_faq=bool(geo and geo.has_faq),
                    has_schema=bool(geo and geo.has_schema),
                    word_count=p.word_count,
                    issues=issue_codes,
                ),
                content_advice=_content_advice(p.word_count, issue_codes, row.segment),
            )
        )
    return briefs


def _site_geo_notes(report: CrawlReport) -> list[str]:
    llms = report.llms_info or {}
    notes: list[str] = []
    for name in ("llms.txt", "llms-full.txt"):
        st = (llms.get(name) or {}).get("status")
        if st != 200:
            notes.append(f"站點缺少 `{name}`（HTTP {st or '—'}），建議建立供 AI 爬蟲讀取的站點摘要。")
    summary = compute_geo_rows(report)
    if summary:
        low = sum(1 for r in summary if r.score < 50)
        if low > len(summary) * 0.4:
            notes.append(f"{low} 頁 GEO 分數 <50，優先處理 Money Page 與首頁的 schema + 字數。")
    return notes


def export_seo_briefs_json(briefs: list[PageSeoBrief], path: Path) -> None:
    path.write_text(
        json.dumps([asdict(b) for b in briefs], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def export_seo_briefs_md(
    report: CrawlReport,
    briefs: list[PageSeoBrief],
    path: Path,
    *,
    site_label: str | None = None,
) -> None:
    host = site_label or report.start_url
    lines = [
        f"# SEO / GEO 文案 Brief — {host}",
        "",
        "> 規則型建議（非 LLM）。依 priority、issues、GEO 分數產生，供編輯或搭配 AI 文案流程使用。",
        "",
    ]
    site_notes = _site_geo_notes(report)
    if site_notes:
        lines.extend(["## 站級 GEO", ""] + [f"- {n}" for n in site_notes] + ["", "---", ""])

    for i, b in enumerate(briefs, 1):
        money = " · Money Page" if b.money_page else ""
        lines.extend(
            [
                f"## {i}. {b.url}",
                "",
                f"**Priority** {b.priority_score} · **GEO** {b.geo_score} · **{b.segment}**{money} · {b.word_count} 字",
                "",
            ]
        )
        if b.issues:
            lines.append("**問題**：" + "、".join(b.issues))
            lines.append("")
        lines.extend(
            [
                "### 現況",
                f"- **Title**：{b.current_title or '（缺）'}",
                f"- **Meta**：{b.current_meta or '（缺）'}",
                f"- **H1**：{b.current_h1 or '（缺）'}",
                "",
                "### 建議",
                f"- **Title**：{b.title_advice}",
                f"- **Meta**：{b.meta_advice}",
                f"- **H1**：{b.h1_advice}",
                f"- **GEO**：{b.geo_advice}",
                f"- **內容**：{b.content_advice}",
                "",
                "---",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def export_seo_briefs_html(
    report: CrawlReport,
    briefs: list[PageSeoBrief],
    path: Path,
    *,
    site_label: str | None = None,
) -> None:
    css = report_styles_bundle()
    label = escape(site_label or report.start_url)
    cards = ""
    for b in briefs:
        issues = "".join(f"<li>{escape(i)}</li>" for i in b.issues) or "<li>無顯著 on-page 問題</li>"
        money = '<span class="meta">Money Page</span>' if b.money_page else ""
        cards += f"""
    <article class="card brief-card">
      <h2 class="brief-url"><a href="{escape(b.url)}">{escape(b.url)}</a></h2>
      <p class="meta brief-meta">Priority {b.priority_score} · GEO {b.geo_score} · {escape(b.segment)} · {b.word_count} 字 {money}</p>
      <ul>{issues}</ul>
      <dl class="brief-dl">
        <dt>Title</dt><dd><code>{escape(b.current_title or '—')}</code><br><span class="brief-advice">{escape(b.title_advice)}</span></dd>
        <dt>Meta</dt><dd><code>{escape(b.current_meta or '—')}</code><br><span class="brief-advice">{escape(b.meta_advice)}</span></dd>
        <dt>H1</dt><dd><code>{escape(b.current_h1 or '—')}</code><br><span class="brief-advice">{escape(b.h1_advice)}</span></dd>
        <dt>GEO</dt><dd>{escape(b.geo_advice)}</dd>
        <dt>內容</dt><dd>{escape(b.content_advice)}</dd>
      </dl>
    </article>"""

    site_notes = _site_geo_notes(report)
    site_block = ""
    if site_notes:
        site_block = '<div class="card"><h2>站級 GEO</h2><ul>' + "".join(
            f"<li>{escape(n)}</li>" for n in site_notes
        ) + "</ul></div>"

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SEO Brief — {label}</title>
  <style>
{css}
  </style>
</head>
<body>
  {report_topbar(path.parent, "SEO Brief", active="seo-briefs.html", site_url=report.start_url)}
  {REPORT_MAIN_OPEN}
    <h1>{label}</h1>
    <p class="lead">規則型文案建議（Top {len(briefs)} 優先 URL）。可搭配 <code>ai-suggestions.md</code>（需 API key）產生 AI 文案。</p>
    {site_block}
    {cards}
  </main>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def generate_ai_suggestions_md(
    report: CrawlReport,
    briefs: list[PageSeoBrief],
    *,
    site_label: str | None = None,
    max_pages: int = 5,
    api_key: str | None = None,
    model: str | None = None,
) -> str | None:
    """呼叫 OpenAI 相容 API；失敗或未設定 key 時回傳 None。"""
    cfg = resolve_ai_config(api_key=api_key, model=model)
    if not cfg:
        return None

    targets = [b for b in briefs if b.money_page][:max_pages] or briefs[:max_pages]
    if not targets:
        return None

    payload = []
    for b in targets:
        payload.append(
            {
                "url": b.url,
                "segment": b.segment,
                "issues": list(b.issues),
                "title": b.current_title,
                "meta": b.current_meta,
                "h1": b.current_h1,
                "geo_score": b.geo_score,
                "word_count": b.word_count,
            }
        )

    prompt = f"""站點：{site_label or report.start_url}

以下 {len(payload)} 個高優先 URL 的爬蟲資料。請為每一頁輸出 Markdown：

1. **建議 Title**（2 個繁中 variant，50–60 字元內）
2. **建議 Meta**（2 個 variant，120–155 字元）
3. **H1 方向**（1 句）
4. **GEO 強化**（schema / FAQ / 內容結構，2–3 條 bullet）

資料：
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""
    try:
        text = chat_completion(prompt, cfg)
    except (OSError, KeyError, json.JSONDecodeError, ValueError):
        return None
    if not text.strip():
        return None
    header = f"# AI 文案建議 — {site_label or report.start_url}\n\n"
    header += f"> 模型 `{cfg.model}` · 請人工覆核後再上架\n\n---\n\n"
    return header + text.strip() + "\n"


def export_seo_briefs_bundle(
    report: CrawlReport,
    out_dir: Path,
    *,
    site_label: str | None = None,
    brief_limit: int = 15,
    ai_max_pages: int = 5,
    run_ai: bool = False,
    api_key: str | None = None,
) -> list[str]:
    """匯出 seo-briefs.*；有 API key 時執行完整 AI 匯出。"""
    briefs = build_page_briefs(report, limit=brief_limit)
    written: list[str] = []
    export_seo_briefs_json(briefs, out_dir / "seo-briefs.json")
    export_seo_briefs_md(report, briefs, out_dir / "seo-briefs.md", site_label=site_label)
    export_seo_briefs_html(report, briefs, out_dir / "seo-briefs.html", site_label=site_label)
    written.extend(["seo-briefs.json", "seo-briefs.md", "seo-briefs.html"])

    if run_ai and resolve_ai_config(api_key=api_key):
        from sitespider.ai_exports import run_ai_polish

        result = run_ai_polish(
            report, out_dir, site_label=site_label, api_key=api_key
        )
        written.extend(result.get("written") or [])
    return written
