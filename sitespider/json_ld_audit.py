"""
依 URL 路徑規則檢查 JSON-LD @type 是否齊全。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from sitespider.crawler import CrawlReport, PageResult
from sitespider.robots import meta_robots_noindex


@dataclass(frozen=True)
class JsonLdRule:
    """path_contains 與 path_regex 二擇一或同時（皆須符合）。"""

    types: tuple[str, ...]
    path_contains: str = ""
    path_regex: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> JsonLdRule | None:
        types = data.get("types") or data.get("type")
        if not types:
            return None
        if isinstance(types, str):
            types = [types]
        return cls(
            types=tuple(str(t).strip() for t in types if str(t).strip()),
            path_contains=str(data.get("path_contains") or ""),
            path_regex=str(data.get("path_regex") or ""),
        )


def _rule_matches(path: str, rule: JsonLdRule) -> bool:
    if rule.path_contains and rule.path_contains not in path:
        return False
    if rule.path_regex and not re.search(rule.path_regex, path, re.I):
        return False
    if not rule.path_contains and not rule.path_regex:
        return False
    return True


def _skip_page(page: PageResult) -> bool:
    if page.blocked_by_robots or page.status >= 400:
        return True
    if meta_robots_noindex(page.meta_robots):
        return True
    return False


def audit_json_ld_rules(report: CrawlReport, rules: tuple[JsonLdRule, ...]) -> None:
    if not rules:
        return
    for page in report.pages.values():
        if _skip_page(page):
            continue
        path = urlparse(page.url).path or "/"
        for rule in rules:
            if not _rule_matches(path, rule):
                continue
            found = {t for t in page.json_ld_types}
            if not any(t in found for t in rule.types):
                if "json_ld_missing_type" not in page.issues:
                    page.issues.append("json_ld_missing_type")
            break
