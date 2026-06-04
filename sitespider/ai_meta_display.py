"""AI 執行紀錄顯示（設定模型 vs 實際 API 模型）。"""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path
from typing import Any

from sitespider.ai_providers import provider_display_name, resolve_model_names


def load_ai_polish_meta(out_dir: Path) -> dict[str, Any] | None:
    p = out_dir / "ai-polish-meta.json"
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def enrich_ai_meta(meta: dict[str, Any]) -> dict[str, Any]:
    """補齊 model_requested / model_resolved（舊紀錄僅有 model）。"""
    out = dict(meta)
    pid = str(out.get("provider_id") or "").strip()
    legacy = str(out.get("model") or "").strip()
    req = str(out.get("model_requested") or legacy).strip()
    res = str(out.get("model_resolved") or legacy).strip()
    if req and pid:
        r2, resolved = resolve_model_names(pid, req)
        if r2:
            req = r2
        if resolved:
            res = resolved
    elif req:
        res = req
    out["model_requested"] = req
    out["model_resolved"] = res or req
    out["model"] = out["model_resolved"]
    return out


def ai_model_caption(meta: dict[str, Any] | None, *, html: bool = True) -> str:
    if not meta:
        return ""
    m = enrich_ai_meta(meta)
    provider = m.get("provider_name") or provider_display_name(m.get("provider_id"))
    req = str(m.get("model_requested") or "").strip()
    res = str(m.get("model_resolved") or req).strip()
    wrap = (lambda s: f"<code>{escape(s)}</code>") if html else (lambda s: s)
    model_part = wrap(res or "—")
    if req and res and req.lower() != res.lower():
        model_part = f"設定 {wrap(req)} → 實際 {wrap(res)}"
    note = " · 請人工覆核後再上架。"
    if html:
        return f"平台 {wrap(str(provider))} · 模型 {model_part}{note}"
    return f"平台 {provider} · 模型 {model_part}{note}"


def patch_ai_html_model_line(html: str, out_dir: Path) -> str:
    """舊報告 HTML 依 ai-polish-meta.json 更新模型說明，避免與目前設定不一致。"""
    meta = load_ai_polish_meta(out_dir)
    if not meta:
        return html
    caption = ai_model_caption(meta, html=True)
    if not caption:
        return html
    lead = f'<p class="lead">{caption}</p>'
    if re.search(r'<p class="lead">.*?</p>', html, flags=re.DOTALL):
        return re.sub(r'<p class="lead">.*?</p>', lead, html, count=1)
    return html
