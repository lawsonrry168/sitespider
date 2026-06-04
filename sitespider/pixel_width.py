"""SERP 標題／描述像素寬度估算（近似 Screaming Frog）。"""

from __future__ import annotations

# Google 桌面 SERP 約 600px 標題、990px 描述（近似字元權重）
TITLE_MAX_PX = 600
META_MAX_PX = 990


def serp_pixel_width(text: str) -> int:
    """CJK 約 2px、拉丁約 1px 的簡化估算。"""
    if not text:
        return 0
    total = 0
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff" or "\u3400" <= ch <= "\u4dbf":
            total += 2
        elif ord(ch) > 127:
            total += 2
        else:
            total += 1
    return total
