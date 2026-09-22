"""
爬蟲 User-Agent 預設值。
"""

from __future__ import annotations

PRESETS: dict[str, str] = {
    "googlebot-desktop": (
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    ),
    "googlebot-smartphone": (
        "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/W.X.Y.Z Mobile Safari/537.36 "
        "(compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    ),
    "bingbot": (
        "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"
    ),
    "chrome-desktop": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "chrome-mobile": (
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36"
    ),
}


def resolve_user_agent(preset_or_custom: str) -> str:
    """預設名稱回傳對應 UA；否則視為自訂字串。"""
    key = (preset_or_custom or "").strip()
    if not key:
        return PRESETS["chrome-desktop"]
    lowered = key.lower()
    if lowered in PRESETS:
        return PRESETS[lowered]
    return key
