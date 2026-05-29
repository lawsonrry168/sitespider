"""
Google Lighthouse CLI 整合 — 效能、無障礙、SEO、最佳實踐分數。
需安裝 Node.js：`npm install -g lighthouse` 或使用 npx。
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse


@dataclass
class LighthouseScores:
    url: str
    performance: float | None = None
    accessibility: float | None = None
    best_practices: float | None = None
    seo: float | None = None
    error: str | None = None
    raw_path: str | None = None


def lighthouse_available() -> bool:
    local_bin = Path(__file__).resolve().parent / "node_modules" / ".bin" / "lighthouse"
    if local_bin.exists():
        return True
    if shutil.which("lighthouse"):
        return True
    if shutil.which("npx"):
        return True
    return False


def _lighthouse_cmd(url: str, output_path: Path, *, mobile: bool = True) -> list[str]:
    args = [
        "--output=json",
        "--output-path=" + str(output_path.with_suffix("")),
        "--quiet",
        "--chrome-flags=--headless --no-sandbox --disable-gpu",
    ]
    if mobile:
        args.append("--form-factor=mobile")
    local_bin = Path(__file__).resolve().parent / "node_modules" / ".bin" / "lighthouse"
    if local_bin.exists():
        return [str(local_bin), url, *args]
    if shutil.which("lighthouse"):
        return ["lighthouse", url, *args]
    return ["npx", "--yes", "lighthouse", url, *args]


def run_lighthouse(
    url: str,
    out_dir: Path,
    *,
    mobile: bool = True,
    timeout: int = 120,
) -> LighthouseScores:
    """對單一 URL 執行 Lighthouse，回傳分數。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = urlparse(url).path.replace("/", "_").strip("_") or "index"
    json_base = out_dir / f"lh_{safe_name}"

    result = LighthouseScores(url=url)
    if not lighthouse_available():
        result.error = "未安裝 lighthouse 或 npx（請執行: npm install -g lighthouse）"
        return result

    if url.startswith("file:"):
        result.error = "Lighthouse 需 HTTP(S) URL，請使用 --mode http 並啟動本機伺服器"
        return result

    cmd = _lighthouse_cmd(url, json_base, mobile=mobile)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != 0 and proc.stderr:
            result.error = proc.stderr[:500]
    except subprocess.TimeoutExpired:
        result.error = f"逾時（>{timeout}s）"
        return result
    except FileNotFoundError:
        result.error = "找不到 lighthouse 執行檔"
        return result

    report_file = json_base.with_suffix(".report.json")
    if not report_file.exists():
        alt = Path(str(json_base) + ".report.json")
        report_file = alt if alt.exists() else json_base.with_name(json_base.name + ".report.json")

    for candidate in [report_file, json_base.with_suffix(".json"), Path(f"{json_base}.report.json")]:
        if candidate.exists():
            report_file = candidate
            break
    else:
        result.error = "Lighthouse 未產生 JSON 報告"
        return result

    try:
        data = json.loads(report_file.read_text(encoding="utf-8"))
        cats = data.get("categories", {})
        result.performance = _cat_score(cats, "performance")
        result.accessibility = _cat_score(cats, "accessibility")
        result.best_practices = _cat_score(cats, "best-practices")
        result.seo = _cat_score(cats, "seo")
        result.raw_path = str(report_file)
    except (json.JSONDecodeError, OSError) as e:
        result.error = str(e)

    return result


def _cat_score(categories: dict, key: str) -> float | None:
    cat = categories.get(key)
    if cat and "score" in cat and cat["score"] is not None:
        return round(cat["score"] * 100, 1)
    return None


def run_lighthouse_batch(
    urls: list[str],
    out_dir: Path,
    *,
    max_urls: int = 10,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, LighthouseScores]:
    """批次執行（依序，Lighthouse 不適合高度並行）。"""
    scores: dict[str, LighthouseScores] = {}
    batch = urls[:max_urls]
    for i, url in enumerate(batch):
        if on_progress:
            on_progress(i + 1, len(batch), url)
        scores[url] = run_lighthouse(url, out_dir / "lighthouse")
    return scores
