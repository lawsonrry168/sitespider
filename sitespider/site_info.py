"""對外網站基本資訊（關於／聯絡頁與 API）。"""

from __future__ import annotations

import os


def public_site_info() -> dict:
    email = (os.environ.get("SITESPIDER_CONTACT_EMAIL") or "hello@sitespider.app").strip()
    company = (os.environ.get("SITESPIDER_COMPANY_NAME") or "").strip()
    return {
        "product": "SiteSpider",
        "tagline": "顧問級 SEO / GEO 交付",
        "contact_email": email,
        "company_name": company or None,
    }
