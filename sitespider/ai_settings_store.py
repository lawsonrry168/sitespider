"""Persist AI settings per tenant (server-side fallback)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def ai_settings_path(base: Path | None = None) -> Path:
    root = (base or Path.cwd()).resolve()
    return root / ".sitespider" / "ai-settings.json"


def load_ai_settings(base: Path | None = None) -> dict[str, dict]:
    p = ai_settings_path(base)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def get_tenant_ai_settings(tenant_id: str, base: Path | None = None) -> dict[str, Any]:
    rec = load_ai_settings(base).get((tenant_id or "default").strip() or "default") or {}
    return {
        "ai_provider": str(rec.get("ai_provider") or "").strip(),
        "ai_model": str(rec.get("ai_model") or "").strip(),
        "ai_model_custom": str(rec.get("ai_model_custom") or "").strip(),
        "ai_api_key": str(rec.get("ai_api_key") or "").strip(),
        "ai_base_url": str(rec.get("ai_base_url") or "").strip(),
        "auto_ai_polish": bool(rec.get("auto_ai_polish")),
    }


_AI_FIELDS = (
    "ai_provider",
    "ai_model",
    "ai_model_custom",
    "ai_api_key",
    "ai_base_url",
    "auto_ai_polish",
)


def merge_ai_into_payload(
    payload: dict[str, Any],
    saved: dict[str, Any] | None,
) -> dict[str, Any]:
    """合併租戶 AI 設定。若伺服器已存 API 金鑰，以伺服器為準（避免 localStorage 舊 provider 蓋掉）。"""
    out = dict(payload)
    if not saved:
        return out
    saved_key = str(saved.get("ai_api_key") or "").strip()
    if saved_key:
        for key in _AI_FIELDS:
            if saved.get(key) is not None and saved.get(key) != "":
                out[key] = saved[key]
        return out
    for key in _AI_FIELDS:
        if key == "auto_ai_polish":
            if out.get(key) is None and saved.get(key) is not None:
                out[key] = saved[key]
            continue
        if not str(out.get(key) or "").strip() and saved.get(key):
            out[key] = saved[key]
    return out


def classify_ai_run_status(
    *,
    written: list[str] | None,
    errors: list[str] | None,
    ok: bool | None = None,
) -> str:
    """done = 核心交付檔已產出；partial = 有產物但關鍵步驟失敗；error = 無可用 AI 交付。"""
    core = {"ai-page-copy.html", "ai-faq.html", "llms.txt.draft"}
    names = {Path(str(f)).name for f in (written or [])}
    has_core = bool(names & core)
    errs = list(errors or [])
    if errs and not has_core:
        return "error"
    if errs:
        return "partial"
    if ok is False:
        return "error"
    return "done"


def set_tenant_ai_settings(
    tenant_id: str,
    payload: dict[str, Any],
    *,
    base: Path | None = None,
) -> dict[str, Any]:
    tid = (tenant_id or "default").strip() or "default"
    db = load_ai_settings(base)
    cur = db.get(tid) or {}
    merged = {
        "ai_provider": str(payload.get("ai_provider", cur.get("ai_provider", ""))).strip(),
        "ai_model": str(payload.get("ai_model", cur.get("ai_model", ""))).strip(),
        "ai_model_custom": str(payload.get("ai_model_custom", cur.get("ai_model_custom", ""))).strip(),
        "ai_api_key": str(payload.get("ai_api_key", cur.get("ai_api_key", ""))).strip(),
        "ai_base_url": str(payload.get("ai_base_url", cur.get("ai_base_url", ""))).strip(),
        "auto_ai_polish": bool(payload.get("auto_ai_polish", cur.get("auto_ai_polish", False))),
    }
    db[tid] = merged
    p = ai_settings_path(base)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    return merged
