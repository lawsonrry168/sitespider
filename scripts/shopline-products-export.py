#!/usr/bin/env python3
"""從 Shopline 商店 sitemap 擷取產品價格與圖片，輸出 CSV（並下載圖片）。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import requests

_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
_UA = "SiteSpider-ShoplineExport/1.0 (+https://github.com/sitespider)"


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": _UA, "Accept-Language": "zh-HK,zh;q=0.9"})
    return s


def product_urls_from_sitemap(base_url: str, session: requests.Session) -> list[str]:
    root = base_url.rstrip("/")
    resp = session.get(f"{root}/sitemap.xml", timeout=60)
    resp.raise_for_status()
    tree = ET.fromstring(resp.content)
    urls: list[str] = []
    for loc in tree.findall(".//sm:loc", _NS):
        if loc.text and "/products/" in loc.text:
            urls.append(loc.text.strip())
    if not urls:
        for loc in tree.findall(".//loc"):
            if loc.text and "/products/" in loc.text:
                urls.append(loc.text.strip())
    return sorted(set(urls))


def _parse_ld_blocks(html: str) -> list[dict]:
    out: list[dict] = []
    for m in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.I | re.S,
    ):
        raw = m.group(1).strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            out.extend(x for x in data if isinstance(x, dict))
        elif isinstance(data, dict):
            out.append(data)
    return out


def _money_block(html: str, key: str) -> dict[str, str]:
    """從頁面內嵌（可能轉義）JSON 擷取 price / price_sale 物件。"""
    q = r'\\?"'
    m = re.search(
        rf'{q}{re.escape(key)}{q}\s*:\s*\{{{q}cents{q}\s*:\s*(\d+).+?{q}label{q}\s*:\s*{q}([^"\\]*){q}.+?{q}dollars{q}\s*:\s*([\d.]+)',
        html,
        re.S,
    )
    if not m:
        return {}
    return {
        "cents": m.group(1),
        "label": m.group(2),
        "dollars": m.group(3),
    }


def _offer_fields(offers) -> dict[str, str]:
    if not offers:
        return {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if not isinstance(offers, dict):
        return {}
    price = offers.get("price") or offers.get("lowPrice") or ""
    high = offers.get("highPrice") or ""
    return {
        "price": str(price) if price != "" else "",
        "price_high": str(high) if high != "" else "",
        "price_currency": str(offers.get("priceCurrency") or "HKD"),
        "availability": str(offers.get("availability") or "").replace("http://schema.org/", "").replace("https://schema.org/", ""),
    }


def parse_product_page(url: str, html: str) -> dict | None:
    product: dict | None = None
    breadcrumb = ""
    for block in _parse_ld_blocks(html):
        t = block.get("@type") or ""
        types = [t] if isinstance(t, str) else list(t) if isinstance(t, list) else []
        if "Product" in types or block.get("@type") == "Product":
            product = block
        if block.get("@type") == "BreadcrumbList":
            items = block.get("itemListElement") or []
            names = []
            for it in items:
                if isinstance(it, dict) and it.get("name"):
                    names.append(str(it["name"]))
            if len(names) > 2:
                breadcrumb = " > ".join(names[1:-1])
    if not product:
        return None
    offers = _offer_fields(product.get("offers"))
    list_price = _money_block(html, "price")
    sale_price = _money_block(html, "price_sale")
    images = product.get("image") or []
    if isinstance(images, str):
        images = [images]
    rating = product.get("aggregateRating") or {}
    return {
        "url": url,
        "name": str(product.get("name") or ""),
        "sku": str(product.get("sku") or product.get("productID") or ""),
        "brand": str((product.get("brand") or {}).get("name") if isinstance(product.get("brand"), dict) else product.get("brand") or ""),
        "description": re.sub(r"\s+", " ", str(product.get("description") or "")).strip(),
        "list_price": list_price.get("dollars", ""),
        "list_price_label": list_price.get("label", ""),
        "sale_price": sale_price.get("dollars", "") or offers.get("price", ""),
        "sale_price_label": sale_price.get("label", ""),
        "price_high": offers.get("price_high", ""),
        "price_currency": offers.get("price_currency", "HKD"),
        "availability": offers.get("availability", ""),
        "category": breadcrumb,
        "rating_value": str(rating.get("ratingValue") or ""),
        "review_count": str(rating.get("reviewCount") or ""),
        "image_urls": "|".join(str(u) for u in images if u),
    }


def fetch_product(session: requests.Session, url: str) -> dict | None:
    try:
        r = session.get(url, timeout=45)
        if r.status_code != 200:
            return {"url": url, "error": f"HTTP {r.status_code}"}
        row = parse_product_page(url, r.text)
        if not row:
            return {"url": url, "error": "no Product JSON-LD"}
        return row
    except requests.RequestException as e:
        return {"url": url, "error": str(e)}


def _safe_image_name(url: str, idx: int) -> str:
    path = urlparse(url).path
    ext = Path(path).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        ext = ".jpg"
    digest = hashlib.sha1(url.encode()).hexdigest()[:10]
    return f"{idx:04d}_{digest}{ext}"


def download_images(
    session: requests.Session,
    products: list[dict],
    images_dir: Path,
) -> list[dict]:
    images_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    seen: set[str] = set()
    idx = 0
    for p in products:
        if p.get("error"):
            continue
        for img_url in (p.get("image_urls") or "").split("|"):
            img_url = img_url.strip()
            if not img_url or img_url in seen:
                continue
            seen.add(img_url)
            idx += 1
            fname = _safe_image_name(img_url, idx)
            local = images_dir / fname
            status = "ok"
            if not local.is_file():
                try:
                    ir = session.get(img_url, timeout=30)
                    ir.raise_for_status()
                    local.write_bytes(ir.content)
                except requests.RequestException as e:
                    status = str(e)
            rows.append(
                {
                    "product_url": p.get("url", ""),
                    "product_name": p.get("name", ""),
                    "image_url": img_url,
                    "local_file": str(local.relative_to(images_dir.parent)),
                    "download_status": status,
                }
            )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Shopline 產品 + 圖片匯出 CSV")
    parser.add_argument("url", help="商店首頁，例如 https://www.saanfolouhk.com/")
    parser.add_argument("-o", "--output", type=Path, default=Path("reports/shopline-export"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--no-images", action="store_true", help="僅 CSV，不下載圖片檔")
    parser.add_argument("--limit", type=int, default=0, help="測試用：只抓前 N 個產品")
    args = parser.parse_args(argv)

    base = args.url.rstrip("/") + "/"
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)

    session = _session()
    print(f"讀取 sitemap… {base}", flush=True)
    urls = product_urls_from_sitemap(base, session)
    if args.limit > 0:
        urls = urls[: args.limit]
    print(f"產品 URL：{len(urls)} 個", flush=True)
    if not urls:
        print("sitemap 內找不到 /products/ 網址", file=sys.stderr)
        return 2

    products: list[dict] = []
    errors = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(fetch_product, session, u): u for u in urls}
        done = 0
        for fut in as_completed(futures):
            done += 1
            row = fut.result()
            if row:
                if row.get("error"):
                    errors += 1
                products.append(row)
            if done % 50 == 0 or done == len(urls):
                print(f"  已抓取 {done}/{len(urls)}…", flush=True)

    products.sort(key=lambda r: r.get("url") or "")
    prod_path = out / "products.csv"
    prod_fields = [
        "url",
        "name",
        "sku",
        "brand",
        "list_price",
        "list_price_label",
        "sale_price",
        "sale_price_label",
        "price_high",
        "price_currency",
        "availability",
        "category",
        "rating_value",
        "review_count",
        "image_urls",
        "description",
        "error",
    ]
    with prod_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=prod_fields, extrasaction="ignore")
        w.writeheader()
        for row in products:
            w.writerow(row)

    ok = sum(1 for p in products if not p.get("error"))
    print(f"products.csv：{ok} 筆成功，{errors} 筆失敗 → {prod_path}", flush=True)

    if not args.no_images:
        print("下載圖片…", flush=True)
        img_rows = download_images(session, products, out / "images")
        img_path = out / "images.csv"
        with img_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(
                f,
                fieldnames=["product_url", "product_name", "image_url", "local_file", "download_status"],
            )
            w.writeheader()
            w.writerows(img_rows)
        print(f"images.csv：{len(img_rows)} 張 → {img_path}", flush=True)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
