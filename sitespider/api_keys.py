"""租戶 API Key 儲存（與 SITESPIDER_API_KEYS 環境變數合併）。"""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any


def keys_path(base: Path | None = None) -> Path:
    root = (base or Path.cwd()).resolve()
    return root / ".sitespider" / "api-keys.json"


def load_file_keys(base: Path | None = None) -> dict[str, dict[str, Any]]:
    p = keys_path(base)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_file_keys(data: dict, base: Path | None = None) -> None:
    p = keys_path(base)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def merged_key_map(base: Path | None = None) -> dict[str, dict[str, Any]]:
    """環境變數 + 檔案（檔案可覆寫）。"""
    out: dict[str, dict[str, Any]] = {}
    raw = os.environ.get("SITESPIDER_API_KEYS", "").strip()
    if raw:
        try:
            env_map = json.loads(raw)
            if isinstance(env_map, dict):
                out.update(env_map)
        except json.JSONDecodeError:
            pass
    path = os.environ.get("SITESPIDER_API_KEYS_FILE", "").strip()
    if path and Path(path).is_file():
        try:
            file_map = json.loads(Path(path).read_text(encoding="utf-8"))
            if isinstance(file_map, dict):
                out.update(file_map)
        except (json.JSONDecodeError, OSError):
            pass
    out.update(load_file_keys(base))
    return out


def generate_key() -> str:
    return "sk_live_" + secrets.token_urlsafe(24)


def issue_tenant_key(
    tenant_id: str,
    plan_id: str,
    *,
    label: str = "",
    base: Path | None = None,
) -> str:
    """建立或輪替租戶 API Key，回傳明文 key（僅此次顯示）。"""
    data = load_file_keys(base)
    for token, meta in list(data.items()):
        if isinstance(meta, dict) and meta.get("tenant") == tenant_id:
            del data[token]
    token = generate_key()
    data[token] = {
        "tenant": tenant_id,
        "plan": plan_id,
        "label": label or tenant_id,
    }
    save_file_keys(data, base)
    return token


def revoke_tenant_keys(tenant_id: str, base: Path | None = None) -> int:
    data = load_file_keys(base)
    removed = 0
    for token, meta in list(data.items()):
        if isinstance(meta, dict) and meta.get("tenant") == tenant_id:
            del data[token]
            removed += 1
    if removed:
        save_file_keys(data, base)
    return removed


def list_tenant_keys(base: Path | None = None) -> dict[str, list[str]]:
    """tenant_id -> [key prefixes]（不暴露完整 key）。"""
    out: dict[str, list[str]] = {}
    for token, meta in merged_key_map(base).items():
        if not isinstance(meta, dict):
            continue
        tid = str(meta.get("tenant") or meta.get("tenant_id") or "")
        if not tid:
            continue
        out.setdefault(tid, []).append(token[:16] + "…")
    return out
