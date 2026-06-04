from sitespider.custom_extract import ExtractionRule, apply_extractions


def test_css_extraction():
    html = "<html><body><span class='sku'>ABC-123</span></body></html>"
    rules = (ExtractionRule(name="sku", css=".sku"),)
    assert apply_extractions(html, rules)["sku"] == "ABC-123"


def test_regex_extraction():
    html = '<a href="tel:+85212345678">call</a>'
    rules = (ExtractionRule(name="phone", regex=r"tel:([+\d]+)"),)
    assert "852" in apply_extractions(html, rules)["phone"]
