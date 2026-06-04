"""
拼寫檢查：預設啟發式詞表；安裝 sitespider[spelling] 後使用 pyspellchecker。
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from sitespider.crawler import CrawlReport

_WORD_RE = re.compile(r"[a-zA-Z]{4,}")

_SPELL: object | None = None
_SPELL_TRIED = False
_HUNSPELL: object | None = None
_HUNSPELL_TRIED = False


def hunspell_available() -> bool:
    """需系統 Hunspell 字典；設定 HUNSPELL_DICT 為不含副檔名的詞典路徑前綴。"""
    global _HUNSPELL, _HUNSPELL_TRIED
    if _HUNSPELL_TRIED:
        return _HUNSPELL is not None
    _HUNSPELL_TRIED = True
    import os

    base = os.environ.get("HUNSPELL_DICT", "").strip()
    if not base:
        return False
    try:
        import hunspell  # type: ignore[import-untyped]

        _HUNSPELL = hunspell.HunSpell(f"{base}.aff", f"{base}.dic")
    except Exception:
        _HUNSPELL = None
    return _HUNSPELL is not None


def spellchecker_available() -> bool:
    global _SPELL, _SPELL_TRIED
    if _SPELL_TRIED:
        return _SPELL is not None
    _SPELL_TRIED = True
    try:
        from spellchecker import SpellChecker

        _SPELL = SpellChecker()
    except ImportError:
        _SPELL = None
    return _SPELL is not None


def spelling_engine_name() -> str:
    if hunspell_available():
        return "hunspell"
    if spellchecker_available():
        return "pyspellchecker"
    return "heuristic"


_COMMON_EN = frozenset(
    w.lower()
    for w in """
    about above access account across action active add address admin after again against
    all allow also alternative always among analysis and another any anyone anything appear
    apply approach area around article ask asset assist association at author available back
    based basic beauty because become been before begin being below best better between
    blog book both brand bring browser build business but buy call campaign can cancel
    card care case category center change check choose city click client close code collection
    color come comment community company compare contact content continue copy cost could
    country course create customer data date day deal default delivery design detail develop
    device different digital direct discount discover display do document does done download
    each early easy edit email end enjoy enough ensure enter error especially even event
    every example experience expert explore express extra face facebook faq fast feature feel
    few file filter find first follow footer for form free from full further gallery general
    get give go good google great group grow guide hair have health help here high home
    how however html https if image important improve include index info information instagram
    instead into introduction item its join just keep keyword know language last latest learn
    left less let level like link list live local login long look love low machine made
    mail main make manage many market may media menu message method might mobile mode model
    more most much must name need network new next not now number offer office often old
    on once one online only open option or order other our out over own page part partner
    pass password pay payment people per perfect phone photo place plan please policy popular
    post price privacy private pro process product professional profile program project promo
    provide purchase quality question quick read ready real really reason receive recent
    recommend redirect register related remove report request require result review right
    sale same save search section secure see select sell send service session set share ship
    shop short should show sign simple site sitemap size skin small social software solution
    some something special specific start state status still store story strategy structure
    style submit success such support sure system tag take team technology tell terms test
    text than thank that the their them then there these they thing think this those through
    time title to today together too tool top total track traffic training treatment try
    twitter type under understand unique update upload url use used user using value variety
    very video view visit website welcome well what when where which while who why will with
    without work world would write year you your youtube
    """.split()
)


def _unknown_words_heuristic(text: str) -> list[str]:
    found: list[str] = []
    for m in _WORD_RE.finditer(text or ""):
        w = m.group().lower()
        if w in _COMMON_EN:
            continue
        if w.endswith(("s", "ed", "ing")) and w[:-1] in _COMMON_EN:
            continue
        if w.endswith("ly") and w[:-2] in _COMMON_EN:
            continue
        found.append(m.group())
    return found


def _unknown_words_spellchecker(text: str) -> list[str]:
    spell = _SPELL
    if spell is None:
        return _unknown_words_heuristic(text)
    found: list[str] = []
    for m in _WORD_RE.finditer(text or ""):
        word = m.group()
        if spell.unknown([word.lower()]):
            found.append(word)
    return found


def _unknown_words_hunspell(text: str) -> list[str]:
    hs = _HUNSPELL
    if hs is None:
        return _unknown_words_heuristic(text)
    found: list[str] = []
    for m in _WORD_RE.finditer(text or ""):
        word = m.group()
        if not hs.spell(word):
            found.append(word)
    return found


def _checker() -> Callable[[str], list[str]]:
    if hunspell_available():
        return _unknown_words_hunspell
    if spellchecker_available():
        return _unknown_words_spellchecker
    return _unknown_words_heuristic


def collect_spelling_rows(report: CrawlReport) -> list[dict[str, str]]:
    engine = spelling_engine_name()
    check = _checker()
    rows: list[dict[str, str]] = []
    for url, page in report.pages.items():
        if page.status != 200:
            continue
        fields = [
            ("Title", page.title),
            ("Meta Description", page.meta_description),
            ("H1", " ".join(page.h1 or [])),
        ]
        seen: set[tuple[str, str]] = set()
        for field_name, text in fields:
            if not text:
                continue
            for word in check(text):
                key = (field_name, word.lower())
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "Address": url,
                        "Field": field_name,
                        "Word": word,
                        "Engine": engine,
                        "Snippet": (text or "")[:120],
                    }
                )
    rows.sort(key=lambda r: (r["Word"].lower(), r["Address"]))
    return rows


def export_spelling_csv(report: CrawlReport, path: Path) -> None:
    rows = collect_spelling_rows(report)
    fields = ["Address", "Field", "Word", "Engine", "Snippet"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
