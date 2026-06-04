"""UI static file serving (/ui/*.svg etc.)."""

from __future__ import annotations

from pathlib import Path

from sitespider.server import UI_DIR, UI_STATIC_TYPES


def test_ui_static_types_include_svg() -> None:
    assert UI_STATIC_TYPES[".svg"] == "image/svg+xml"


def test_brand_mark_file_exists() -> None:
    assert (UI_DIR / "brand-mark.svg").is_file()
