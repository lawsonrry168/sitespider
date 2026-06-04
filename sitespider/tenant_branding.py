"""Per-tenant branding persisted on server."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def branding_db_path(base: Path | None = None) -> Path:
    root = (base or Path.cwd()).resolve()
    return root / ".sitespider" / "branding.json"


def load_all_branding(base: Path | None = None) -> dict[str, dict]:
    p = branding_db_path(base)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def get_tenant_branding(tenant_id: str, base: Path | None = None) -> dict[str, str]:
    tid = (tenant_id or "default").strip() or "default"
    rec = load_all_branding(base).get(tid) or {}
    return {
        "consultant_name": str(rec.get("consultant_name") or "").strip(),
        "logo_url": str(rec.get("logo_url") or "").strip(),
        "accent_color": str(rec.get("accent_color") or "#6ec9a0").strip() or "#6ec9a0",
    }


def set_tenant_branding(
    tenant_id: str,
    data: dict[str, Any],
    *,
    base: Path | None = None,
) -> dict[str, str]:
    tid = (tenant_id or "default").strip() or "default"
    db = load_all_branding(base)
    prev = db.get(tid) or {}
    merged = {
        "consultant_name": str(data.get("consultant_name", prev.get("consultant_name", ""))).strip(),
        "logo_url": str(data.get("logo_url", prev.get("logo_url", ""))).strip(),
        "accent_color": str(data.get("accent_color", prev.get("accent_color", "#6ec9a0"))).strip()
        or "#6ec9a0",
        "updated_at": time.time(),
    }
    db[tid] = merged
    p = branding_db_path(base)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    return get_tenant_branding(tid, base)
