"""
Playwright cookie JSON 載入 / 儲存（供登入後 session 重用）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_cookies(path: str | Path) -> list[dict[str, Any]]:
    """讀取 Playwright storage state 或純 cookie 陣列 JSON。"""
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        cookies = raw.get("cookies")
        if isinstance(cookies, list):
            return cookies
    return []


def save_cookies(path: str | Path, cookies: list[dict[str, Any]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")


def apply_cookies_to_context(context: Any, cookies: list[dict[str, Any]]) -> None:
    """context: playwright.sync_api.BrowserContext"""
    if cookies:
        context.add_cookies(cookies)
