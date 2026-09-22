"""
內容相似度：SimHash 64-bit 與 shingle Jaccard / cosine，偵測近重複頁。
"""

from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport, PageResult

from sitespider.robots import meta_robots_noindex

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
_SHINGLE_SIZE = 3


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


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text) if len(t) >= 2]


def _shingles(text: str, k: int = _SHINGLE_SIZE) -> set[str]:
    tokens = _tokens(text)
    if len(tokens) < k:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + k]) for i in range(len(tokens) - k + 1)}


def simhash64(text: str, k: int = _SHINGLE_SIZE) -> int:
    """64-bit SimHash over word shingles."""
    shingles = _shingles(text, k)
    if not shingles:
        return 0
    vec = [0] * 64
    for sh in shingles:
        digest = hashlib.md5(sh.encode("utf-8")).digest()
        h = int.from_bytes(digest[:8], "big")
        for i in range(64):
            vec[i] += 1 if (h >> i) & 1 else -1
    out = 0
    for i, v in enumerate(vec):
        if v > 0:
            out |= 1 << i
    return out


def hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def shingle_jaccard(a: str, b: str, k: int = _SHINGLE_SIZE) -> float:
    sa, sb = _shingles(a, k), _shingles(b, k)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def shingle_cosine(a: str, b: str, k: int = _SHINGLE_SIZE) -> float:
    sa, sb = _shingles(a, k), _shingles(b, k)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    denom = (len(sa) * len(sb)) ** 0.5
    return inter / denom if denom else 0.0


def _combined_score(text_a: str, text_b: str) -> float:
    return max(shingle_jaccard(text_a, text_b), shingle_cosine(text_a, text_b))


def _eligible(page: PageResult) -> bool:
    if page.status != 200 or page.blocked_by_robots:
        return False
    if meta_robots_noindex(page.meta_robots):
        return False
    return bool(_page_text(page))


def detect_near_duplicates(
    report: CrawlReport,
    *,
    threshold: float = 0.90,
    simhash_max_dist: int = 3,
) -> list[dict[str, str | float]]:
    """
    比對全站頁面，回傳並寫入 report.near_duplicate_pairs。
    每筆：{url_a, url_b, score}。
    """
    entries: list[tuple[str, str, int]] = []
    for url, page in report.pages.items():
        if not _eligible(page):
            continue
        text = _page_text(page)
        entries.append((url, text, simhash64(text)))

    pairs: list[dict[str, str | float]] = []
    seen: set[tuple[str, str]] = set()

    for i in range(len(entries)):
        url_a, text_a, hash_a = entries[i]
        for j in range(i + 1, len(entries)):
            url_b, text_b, hash_b = entries[j]
            key = tuple(sorted((url_a, url_b)))
            if key in seen:
                continue
            score = _combined_score(text_a, text_b)
            dist = hamming_distance(hash_a, hash_b)
            if score >= threshold or (dist <= simhash_max_dist and score >= threshold * 0.8):
                seen.add(key)
                pairs.append({"url_a": url_a, "url_b": url_b, "score": round(score, 4)})

    pairs.sort(key=lambda p: (-float(p["score"]), str(p["url_a"]), str(p["url_b"])))
    report.near_duplicate_pairs = pairs
    return pairs


def audit_near_duplicates(report: CrawlReport, threshold: float = 0.90) -> None:
    """標記 near_duplicate issue。"""
    pairs = detect_near_duplicates(report, threshold=threshold)
    for pair in pairs:
        for url in (pair["url_a"], pair["url_b"]):
            page = report.pages.get(str(url))
            if page:
                _issue(page, "near_duplicate")
