"""自適應擷取 — JSON-LD、regex 鏈、CSS fallback（Scrapling adaptive 精簡版）。"""

from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from sitespider.custom_extract import ExtractionRule, apply_extractions


def extract_json_ld_value(html: str, type_name: str, field: str) -> str:
    if not html or not type_name:
        return ""
    want = type_name.strip().lower()
    field_key = field.strip()
    for block in _ld_blocks(html):
        types = block.get("@type") or ""
        type_list = [types] if isinstance(types, str) else list(types) if isinstance(types, list) else []
        if want not in {t.lower() for t in type_list}:
            continue
        val = _dig(block, field_key)
        if val is not None and str(val).strip():
            return str(val).strip()[:2000]
    return ""


def _ld_blocks(html: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.I | re.S,
    ):
        raw = m.group(1).strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            out.extend(x for x in data if isinstance(x, dict))
        elif isinstance(data, dict):
            out.append(data)
    return out


def _dig(obj: Any, dotted: str) -> Any:
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _css_fallbacks(css: str) -> list[str]:
    css = css.strip()
    if not css:
        return []
    out = [css]
    if "." in css:
        tag = css.split(".", 1)[0] or "*"
        if tag != "*":
            out.append(tag)
    if "[" in css:
        out.append(css.split("[", 1)[0])
    return out


def apply_rule_adaptive(soup: BeautifulSoup, html: str, rule: ExtractionRule) -> str:
    json_type = getattr(rule, "json_ld_type", "") or ""
    json_field = getattr(rule, "json_ld_field", "") or ""
    if json_type and json_field:
        val = extract_json_ld_value(html, json_type, json_field)
        if val:
            return val

    fallbacks = getattr(rule, "fallback_regex", "") or ""
    if fallbacks:
        for pat in fallbacks.split("||"):
            pat = pat.strip()
            if not pat:
                continue
            m = re.search(pat, html, re.I | re.S)
            if m:
                return (m.group(1) if m.lastindex else m.group(0)).strip()[:2000]

    css = rule.css.strip()
    if css:
        selectors = _css_fallbacks(css) if getattr(rule, "adaptive", False) else [css]
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                return _element_value(el, rule)

    if rule.regex:
        m = re.search(rule.regex, html, re.I | re.S)
        if m:
            return (m.group(1) if m.lastindex else m.group(0)).strip()[:2000]
    return ""


def _element_value(el: Tag, rule: ExtractionRule) -> str:
    if rule.extract == "html":
        return el.decode_contents().strip()[:2000]
    if rule.extract == "attr" and rule.attribute:
        return str(el.get(rule.attribute) or "").strip()
    return el.get_text(separator=" ", strip=True)[:2000]


def apply_extractions_adaptive(html: str, rules: tuple[ExtractionRule, ...]) -> dict[str, str]:
    if not rules or not html:
        return {}
    soup = BeautifulSoup(html, "lxml")
    out: dict[str, str] = {}
    for rule in rules:
        adaptive = getattr(rule, "adaptive", False) or getattr(rule, "json_ld_type", "")
        if adaptive:
            val = apply_rule_adaptive(soup, html, rule)
        else:
            val = apply_extractions(html, (rule,)).get(rule.name, "")
        if val:
            out[rule.name] = val
    return out
