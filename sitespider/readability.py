"""
可讀性指標：英文 Flesch / FK / Fog；中文以句均字數估算。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport, PageResult

from sitespider.robots import meta_robots_noindex

_WORD_RE = re.compile(r"[a-zA-Z]+(?:'[a-zA-Z]+)?")
_SENT_SPLIT_RE = re.compile(r"[.!?。！？]+")
_ZH_CHAR_RE = re.compile(r"[\u4e00-\u9fff]")
_VOWELS = "aeiouy"


def _issue(page: PageResult, code: str) -> None:
    if code not in page.issues:
        page.issues.append(code)


def _page_text(page: PageResult) -> str:
    body = getattr(page, "body_text", None) or ""
    if body.strip():
        return body.strip()
    parts = [
        page.title or "",
        page.meta_description or "",
        " ".join(page.h1 or []),
        " ".join(page.h2 or []),
    ]
    return " ".join(p for p in parts if p).strip()


def _is_chinese(page: PageResult, text: str) -> bool:
    lang = (page.html_lang or "").lower()
    if lang.startswith("zh"):
        return True
    zh = len(_ZH_CHAR_RE.findall(text))
    en = len(_WORD_RE.findall(text))
    return zh > en and zh >= 20


def _count_syllables(word: str) -> int:
    w = word.lower()
    if len(w) <= 3:
        return 1
    w = re.sub(r"e$", "", w)
    groups = re.findall(r"[aeiouy]+", w)
    return max(1, len(groups))


def _english_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENT_SPLIT_RE.split(text) if p.strip()]
    return parts if parts else ([text] if text.strip() else [])


def _english_metrics(text: str) -> tuple[float, float]:
    sentences = _english_sentences(text)
    words = _WORD_RE.findall(text)
    if not sentences or not words:
        return 0.0, 0.0
    syllables = sum(_count_syllables(w) for w in words)
    wps = len(words) / len(sentences)
    spw = syllables / len(words)
    ease = 206.835 - 1.015 * wps - 84.6 * spw
    grade = 0.39 * wps + 11.8 * spw - 15.59
    return round(ease, 1), round(grade, 1)


def _chinese_metrics(text: str) -> tuple[float, float]:
    sentences = [p.strip() for p in _SENT_SPLIT_RE.split(text) if p.strip()]
    if not sentences:
        sentences = [text] if text.strip() else []
    chars = _ZH_CHAR_RE.findall(text)
    if not sentences or not chars:
        return 0.0, 0.0
    avg_chars = len(chars) / len(sentences)
    # 句均字數映射到近似 ease（字越少越好讀）
    ease = max(0.0, min(100.0, 100.0 - (avg_chars - 20) * 1.2))
    grade = round(avg_chars / 10.0, 1)
    return round(ease, 1), grade


def compute_readability(page: PageResult) -> tuple[float, float]:
    """回傳 (readability_ease, readability_grade)。"""
    text = _page_text(page)
    if not text:
        return 0.0, 0.0
    if _is_chinese(page, text):
        return _chinese_metrics(text)
    return _english_metrics(text)


def audit_readability(report: CrawlReport) -> None:
    for page in report.pages.values():
        if page.status >= 400 or page.blocked_by_robots:
            continue
        if meta_robots_noindex(page.meta_robots):
            continue
        text = _page_text(page)
        if not text:
            continue
        ease, grade = compute_readability(page)
        page.readability_ease = ease
        page.readability_grade = grade
        if _is_chinese(page, text):
            sentences = [p.strip() for p in _SENT_SPLIT_RE.split(text) if p.strip()] or [text]
            chars = _ZH_CHAR_RE.findall(text)
            avg_chars = len(chars) / max(1, len(sentences))
            if avg_chars > 80:
                _issue(page, "low_readability")
        elif ease < 30:
            _issue(page, "low_readability")
