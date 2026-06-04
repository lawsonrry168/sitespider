"""
錨點連結語意：nofollow / ugc / sponsored、DOM 區塊位置（對齊 SF Link Position）。
"""

from __future__ import annotations

import re
from typing import Any

# SF 常見 Link Position 標籤
POSITION_FOOTER = "Footer"
POSITION_NAV = "Navigation"
POSITION_HEADER = "Header"
POSITION_ASIDE = "Aside"
POSITION_CONTENT = "Content"

_ROLE_MAP = {
    "contentinfo": POSITION_FOOTER,
    "navigation": POSITION_NAV,
    "banner": POSITION_HEADER,
    "complementary": POSITION_ASIDE,
}

_HINT_FOOTER = re.compile(
    r"\b(footer|site-footer|page-footer|colophon)\b", re.I
)
_HINT_NAV = re.compile(
    r"\b(nav|navbar|navigation|menu|main-menu|primary-nav|w-nav)\b", re.I
)
_HINT_HEADER = re.compile(r"\b(header|site-header|page-header|masthead)\b", re.I)
_HINT_ASIDE = re.compile(r"\b(sidebar|aside|widget-area|w-sidebar)\b", re.I)


def rel_tokens(rel: Any) -> set[str]:
    if rel is None:
        return set()
    if isinstance(rel, list):
        parts = rel
    else:
        parts = [rel]
    out: set[str] = set()
    for part in parts:
        out.update(str(part).lower().split())
    return out


def is_nofollow(rel: Any) -> bool:
    return "nofollow" in rel_tokens(rel)


def _element_hint(tag: Any) -> str:
    parts = [
        str(getattr(tag, "name", "") or ""),
        str(tag.get("id") or "") if hasattr(tag, "get") else "",
    ]
    classes = tag.get("class") if hasattr(tag, "get") else None
    if isinstance(classes, list):
        parts.append(" ".join(classes))
    elif classes:
        parts.append(str(classes))
    role = tag.get("role") if hasattr(tag, "get") else None
    if role:
        parts.append(str(role))
    return " ".join(parts).lower()


def detect_link_position(anchor: Any) -> str:
    """由 <a> 向上遍歷，推斷連結所在版位。"""
    if anchor is None or not hasattr(anchor, "parents"):
        return POSITION_CONTENT

    for parent in anchor.parents:
        name = getattr(parent, "name", None)
        if not name or name in ("[document]", "html"):
            continue
        if name == "footer":
            return POSITION_FOOTER
        if name == "nav":
            return POSITION_NAV
        if name == "header":
            return POSITION_HEADER
        if name == "aside":
            return POSITION_ASIDE

        role = (parent.get("role") or "").lower() if hasattr(parent, "get") else ""
        if role in _ROLE_MAP:
            return _ROLE_MAP[role]

        hint = _element_hint(parent)
        if _HINT_FOOTER.search(hint):
            return POSITION_FOOTER
        if _HINT_NAV.search(hint):
            return POSITION_NAV
        if _HINT_HEADER.search(hint):
            return POSITION_HEADER
        if _HINT_ASIDE.search(hint):
            return POSITION_ASIDE

    return POSITION_CONTENT
