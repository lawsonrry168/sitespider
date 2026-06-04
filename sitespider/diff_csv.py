"""
比對 SiteSpider internal.csv 與 Screaming Frog 匯出（Internal 分頁 CSV）。
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse, urlunparse


ADDRESS_COLUMNS = ("Address", "address", "URL", "url")


@dataclass
class CsvUrlDiff:
    sf_path: str
    ours_path: str
    sf_count: int = 0
    ours_count: int = 0
    in_both: list[str] = field(default_factory=list)
    only_sf: list[str] = field(default_factory=list)
    only_ours: list[str] = field(default_factory=list)
    sf_rows: dict[str, dict] = field(default_factory=dict)
    ours_rows: dict[str, dict] = field(default_factory=dict)

    @property
    def overlap_pct_sf(self) -> float:
        if not self.sf_count:
            return 0.0
        return 100.0 * len(self.in_both) / self.sf_count

    def summary_lines(self) -> list[str]:
        lines = [
            f"Screaming Frog：{self.sf_count} URL（{self.sf_path}）",
            f"SiteSpider：{self.ours_count} URL（{self.ours_path}）",
            f"兩邊皆有：{len(self.in_both)}（佔 SF {self.overlap_pct_sf:.1f}%）",
            f"僅 SF 有：{len(self.only_sf)}",
            f"僅 SiteSpider 有：{len(self.only_ours)}",
        ]
        return lines


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    p = urlparse(url)
    if not p.scheme:
        url = "https://" + url.lstrip("/")
        p = urlparse(url)
    path = p.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    if path.endswith("/index.html"):
        path = path[: -len("index.html")] or "/"
    return urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", p.query, ""))


def _detect_address_column(fieldnames: list[str] | None) -> str | None:
    if not fieldnames:
        return None
    for col in ADDRESS_COLUMNS:
        if col in fieldnames:
            return col
    lower = {f.lower(): f for f in fieldnames}
    for col in ADDRESS_COLUMNS:
        if col.lower() in lower:
            return lower[col.lower()]
    return None


def load_csv_urls(path: Path) -> tuple[dict[str, dict], str]:
    """回傳 normalized_url -> row dict, address_column_name。"""
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    reader = csv.DictReader(text.splitlines())
    addr_col = _detect_address_column(reader.fieldnames)
    if not addr_col:
        raise ValueError(
            f"找不到 URL 欄位（需 Address / URL）：{path}\n欄位：{reader.fieldnames}"
        )
    rows: dict[str, dict] = {}
    for row in reader:
        raw = (row.get(addr_col) or "").strip()
        if not raw:
            continue
        norm = normalize_url(raw)
        if norm:
            rows[norm] = row
    return rows, addr_col


def compare_csv_urls(sf_csv: Path, ours_csv: Path) -> CsvUrlDiff:
    sf_rows, _ = load_csv_urls(sf_csv)
    ours_rows, _ = load_csv_urls(ours_csv)
    sf_set = set(sf_rows)
    ours_set = set(ours_rows)
    both = sorted(sf_set & ours_set)
    only_sf = sorted(sf_set - ours_set)
    only_ours = sorted(ours_set - sf_set)
    return CsvUrlDiff(
        sf_path=str(sf_csv),
        ours_path=str(ours_csv),
        sf_count=len(sf_set),
        ours_count=len(ours_set),
        in_both=both,
        only_sf=only_sf,
        only_ours=only_ours,
        sf_rows=sf_rows,
        ours_rows=ours_rows,
    )


def _compare_field(sf_row: dict, our_row: dict, field: str) -> bool:
    a = str(sf_row.get(field, "") or "").strip()
    b = str(our_row.get(field, "") or "").strip()
    return a == b


def field_mismatches(diff: CsvUrlDiff, *, fields: tuple[str, ...] | None = None) -> dict[str, list[str]]:
    """對共同 URL 比對指定欄位差異。"""
    check = fields or (
        "Status Code",
        "Indexability",
        "Indexability Status",
        "Title 1",
        "Canonical Link Element 1",
    )
    out: dict[str, list[str]] = {f: [] for f in check}
    for url in diff.in_both:
        sf = diff.sf_rows[url]
        ours = diff.ours_rows[url]
        for f in check:
            if f in sf or f in ours:
                if not _compare_field(sf, ours, f):
                    out[f].append(url)
    return {k: v for k, v in out.items() if v}


def write_diff_exports(diff: CsvUrlDiff, out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    only_sf_path = out_dir / "diff-only-screaming-frog.csv"
    with only_sf_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Address"])
        for u in diff.only_sf:
            w.writerow([u])
    written.append(only_sf_path.name)

    only_ours_path = out_dir / "diff-only-sitespider.csv"
    with only_ours_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Address"])
        for u in diff.only_ours:
            w.writerow([u])
    written.append(only_ours_path.name)

    mismatches = field_mismatches(diff)
    md_path = out_dir / "diff-sf-comparison.md"
    lines = [
        "# Screaming Frog × SiteSpider URL 比對",
        "",
        *[f"- {line}" for line in diff.summary_lines()],
        "",
        "## 僅 Screaming Frog 有的 URL（前 30）",
        "",
    ]
    if diff.only_sf:
        for u in diff.only_sf[:30]:
            lines.append(f"- {u}")
        if len(diff.only_sf) > 30:
            lines.append(f"- …共 {len(diff.only_sf)} 筆，見 `diff-only-screaming-frog.csv`")
    else:
        lines.append("無")

    lines.extend(["", "## 僅 SiteSpider 有的 URL（前 30）", ""])
    if diff.only_ours:
        for u in diff.only_ours[:30]:
            lines.append(f"- {u}")
        if len(diff.only_ours) > 30:
            lines.append(f"- …共 {len(diff.only_ours)} 筆，見 `diff-only-sitespider.csv`")
    else:
        lines.append("無")

    lines.extend(["", "## 共同 URL 欄位不一致", ""])
    for field, urls in mismatches.items():
        lines.append(f"### {field}（{len(urls)} 筆）")
        for u in urls[:10]:
            sf = diff.sf_rows[u]
            ours = diff.ours_rows[u]
            lines.append(
                f"- `{u}`  \n  SF: `{str(sf.get(field, ''))[:80]}`  \n  SS: `{str(ours.get(field, ''))[:80]}`"
            )
        if len(urls) > 10:
            lines.append(f"- …及其他 {len(urls) - 10} 筆")
        lines.append("")

    lines.append(
        "\n*在 Screaming Frog：Bulk Export → Internal → 存成 CSV，再執行 "
        "`sitespider diff-csv screamfrog.csv internal.csv`*\n"
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    written.append(md_path.name)
    return written


def write_diff_csv_list(path: Path, urls: list[str], header: str = "Address") -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow([header])
        for u in urls:
            w.writerow([u])
