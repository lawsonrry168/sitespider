#!/usr/bin/env python3
"""Sync brand-mark.svg → favicon.svg (single source of truth)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "sitespider" / "ui"
MASTER = UI / "brand-mark.svg"
FAVICON = UI / "favicon.svg"


def main() -> int:
    if not MASTER.is_file():
        print(f"MISSING {MASTER}")
        return 1
    FAVICON.write_text(MASTER.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"OK   {MASTER.name} → {FAVICON.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
