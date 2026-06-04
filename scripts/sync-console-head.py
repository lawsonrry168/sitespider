#!/usr/bin/env python3
"""Check / sync console HTML <head> brand + CSS block."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "sitespider" / "ui"

CONSOLE_PAGES = (
    "dashboard.html",
    "guide.html",
    "workspace.html",
    "branding.html",
    "ai.html",
    "pricing.html",
    "admin.html",
    "demo.html",
    "checkout_success.html",
    "about.html",
    "contact.html",
    "sites.html",
)

# Canonical block (after charset, before viewport)
HEAD_BLOCK = """  <link rel="icon" href="/ui/brand-mark.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/ui/apple-touch-icon.svg">
  <meta name="theme-color" content="#0c0e14">"""

REQUIRED = [
    'href="/ui/brand-mark.svg"',
    "apple-touch-icon.svg",
    "theme-color",
    "tokens.css",
    "shell.css",
    "theme.css",
    "comfort-display.css",
    "polish.css",
    "ux-friendly.css",
    "site-reset.css",
]

_OLD_HEAD_RE = re.compile(
    r"  <link rel=\"icon\"[^>]*>\n"
    r"(?:  <link rel=\"icon\"[^>]*>\n)?"
    r"  <link rel=\"apple-touch-icon\"[^>]*>\n"
    r"  <meta name=\"theme-color\"[^>]*>\n",
    re.MULTILINE,
)


def check(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [r for r in REQUIRED if r not in text]


def sync_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if 'charset="UTF-8">' not in text:
        return False
    if _OLD_HEAD_RE.search(text):
        text = _OLD_HEAD_RE.sub(HEAD_BLOCK + "\n", text, count=1)
    elif HEAD_BLOCK.strip() not in text:
        text = text.replace(
            '<meta charset="UTF-8">',
            '<meta charset="UTF-8">\n' + HEAD_BLOCK,
            1,
        )
    else:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true", help="Apply canonical head block")
    args = parser.parse_args()

    failed = False
    for name in CONSOLE_PAGES:
        path = UI / name
        if not path.is_file():
            print(f"MISSING {name}")
            failed = True
            continue
        if args.fix:
            if sync_file(path):
                print(f"SYNC {name}")
            else:
                miss = check(path)
                if miss:
                    print(f"FAIL {name}: missing {miss}")
                    failed = True
                else:
                    print(f"OK   {name}")
        else:
            miss = check(path)
            if miss:
                print(f"FAIL {name}: missing {miss}")
                failed = True
            else:
                print(f"OK   {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
