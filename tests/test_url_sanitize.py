from sitespider.url_sanitize import sanitize_start_url, start_url_looks_invalid


def test_sanitize_embedded_scheme_in_path():
    raw = "https://www.vitagreen.com/zh/index://example.com/"
    assert sanitize_start_url(raw) == "https://www.vitagreen.com/zh/"


def test_sanitize_unchanged_ok_url():
    raw = "https://www.vitagreen.com/zh/"
    assert sanitize_start_url(raw) == raw


def test_invalid_mixed_domains():
    bad = start_url_looks_invalid("https://www.vitagreen.com/zh/index://example.com/")
    assert bad is not None
