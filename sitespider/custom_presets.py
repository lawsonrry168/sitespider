"""UI 可選的自訂擷取預設（無需手寫 JSON）。"""

from __future__ import annotations

from sitespider.custom_extract import ExtractionRule

# id -> rule dict（與 custom_extract.from_dict 相容）
CUSTOM_PRESET_RULES: dict[str, dict] = {
    "phone_hk": {
        "name": "Phone HK",
        "regex": r"(\+852[\s\-]?\d{4}[\s\-]?\d{4})",
    },
    "email": {
        "name": "Email",
        "regex": r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
    },
    "add_to_cart": {
        "name": "Add To Cart",
        "regex": r"(add[\s\-]?to[\s\-]?cart|加入購物車)",
        "extract": "text",
    },
    "product_price": {
        "name": "Product Price",
        "css": ".price, .woocommerce-Price-amount, [itemprop='price']",
        "extract": "text",
    },
    "json_ld_product": {
        "name": "JSON-LD Product",
        "regex": r'"@type"\s*:\s*"Product"',
    },
    "h1_count": {
        "name": "H1 Count",
        "css": "h1",
        "extract": "text",
    },
    "meta_robots": {
        "name": "Meta Robots",
        "css": "meta[name=robots]",
        "extract": "attr",
        "attribute": "content",
    },
}


def list_preset_ids() -> list[str]:
    return sorted(CUSTOM_PRESET_RULES.keys())


def rules_from_preset_ids(ids: list[str]) -> tuple[ExtractionRule, ...]:
    rules: list[ExtractionRule] = []
    for pid in ids:
        raw = CUSTOM_PRESET_RULES.get(pid)
        if not raw:
            continue
        rule = ExtractionRule.from_dict(raw)
        if rule:
            rules.append(rule)
    return tuple(rules)


def rules_from_payload(raw_list: list[dict] | None) -> tuple[ExtractionRule, ...]:
    if not raw_list:
        return ()
    rules: list[ExtractionRule] = []
    for item in raw_list:
        if isinstance(item, dict):
            rule = ExtractionRule.from_dict(item)
            if rule:
                rules.append(rule)
    return tuple(rules)
