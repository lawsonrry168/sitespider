"""顧問白標：報告與交付物品牌欄位。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sitespider.plans import Plan

DEFAULT_BRAND_ACCENT = "#6ec9a0"


@dataclass(frozen=True)
class Branding:
    consultant_name: str = ""
    logo_url: str = ""
    accent_color: str = DEFAULT_BRAND_ACCENT

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Branding:
        if not data:
            return cls()
        return cls(
            consultant_name=str(data.get("consultant_name") or data.get("agency") or "").strip(),
            logo_url=str(data.get("logo_url") or data.get("logo") or "").strip(),
            accent_color=str(data.get("accent_color") or data.get("brand_color") or "#6ec9a0").strip()
            or "#3dd6a0",
        )

    def html_header(self) -> str:
        if not self.consultant_name and not self.logo_url:
            return ""
        logo = (
            f'<img src="{self.logo_url}" alt="" style="max-height:48px;margin-right:12px">'
            if self.logo_url
            else ""
        )
        name = f"<strong>{self.consultant_name}</strong>" if self.consultant_name else ""
        return f'<div style="display:flex;align-items:center;margin-bottom:1rem">{logo}{name}</div>'


def branding_for_plan(plan: Plan, data: object | None) -> Branding:
    """Apply subscription limits to consultant branding."""
    brand = (
        data
        if isinstance(data, Branding)
        else Branding.from_dict(data if isinstance(data, dict) else None)
    )
    if plan.has("white_label"):
        return brand
    if plan.has("branding_lite"):
        return Branding(
            consultant_name=brand.consultant_name,
            logo_url="",
            accent_color=DEFAULT_BRAND_ACCENT,
        )
    return Branding()
