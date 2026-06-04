"""
自訂擷取（Screaming Frog Custom Extraction）— CSS 選擇器或 Regex。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class ExtractionRule:
    name: str
    css: str = ""
    regex: str = ""
    attribute: str = ""
    extract: str = "text"  # text | html | attr

    @classmethod
    def from_dict(cls, data: dict) -> ExtractionRule | None:
        name = str(data.get("name") or "").strip()
        if not name:
            return None
        return cls(
            name=name,
            css=str(data.get("css") or data.get("selector") or ""),
            regex=str(data.get("regex") or data.get("pattern") or ""),
            attribute=str(data.get("attribute") or data.get("attr") or ""),
            extract=str(data.get("extract") or "text"),
        )


def apply_extractions(html: str, rules: tuple[ExtractionRule, ...]) -> dict[str, str]:
    if not rules or not html:
        return {}
    soup = BeautifulSoup(html, "lxml")
    out: dict[str, str] = {}
    for rule in rules:
        val = _apply_one(soup, html, rule)
        if val:
            out[rule.name] = val[:2000]
    return out


def _apply_one(soup: BeautifulSoup, html: str, rule: ExtractionRule) -> str:
    if rule.regex:
        m = re.search(rule.regex, html, re.I | re.S)
        return (m.group(1) if m.lastindex else m.group(0)).strip() if m else ""

    if not rule.css:
        return ""

    el = soup.select_one(rule.css)
    if not el:
        return ""

    if rule.extract == "html":
        return el.decode_contents().strip()[:2000]
    if rule.extract == "attr" and rule.attribute:
        return str(el.get(rule.attribute) or "").strip()
    return el.get_text(separator=" ", strip=True)[:2000]
