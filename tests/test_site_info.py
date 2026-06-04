"""對外網站資訊 API。"""

from sitespider.site_info import public_site_info


def test_public_site_info_defaults():
    info = public_site_info()
    assert info["product"] == "SiteSpider"
    assert "@" in info["contact_email"]


def test_public_site_info_env(monkeypatch):
    monkeypatch.setenv("SITESPIDER_CONTACT_EMAIL", "team@example.com")
    monkeypatch.setenv("SITESPIDER_COMPANY_NAME", "Example Ltd")
    info = public_site_info()
    assert info["contact_email"] == "team@example.com"
    assert info["company_name"] == "Example Ltd"
