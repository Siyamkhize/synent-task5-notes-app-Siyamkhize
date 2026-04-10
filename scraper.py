from typing import List, Dict, Any
import re
import json
import requests
from bs4 import BeautifulSoup


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def extract_prices(soup: BeautifulSoup) -> List[str]:
    prices = []
    currency = r"(?:\\$|€|£|R|ZAR|USD|EUR|GBP)"
    number = r"(?:\\d{1,3}(?:[ ,\\.]\\d{3})*(?:[\\.,]\\d{2})?|\\d+(?:[\\.,]\\d{2}))"
    price_re = re.compile(fr"{currency}\\s?{number}|{number}\\s?{currency}", re.IGNORECASE)

    for el in soup.find_all(attrs={"data-price": True}):
        prices.append(clean_text(el.get("data-price")))
    for el in soup.find_all(string=price_re):
        prices.append(clean_text(str(el)))
    for el in soup.select("[class*=price], [id*=price]"):
        text = el.get_text(" ")
        if price_re.search(text):
            prices.append(clean_text(text))
    return list(dict.fromkeys(prices))[:20]


def extract_titles(soup: BeautifulSoup) -> List[str]:
    titles = []
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        titles.append(clean_text(og_title.get("content")))
    meta_title = soup.find("meta", attrs={"name": "title"})
    if meta_title and meta_title.get("content"):
        titles.append(clean_text(meta_title.get("content")))
    for tag in ["h1", "h2", "h3", "title"]:
        for el in soup.find_all(tag):
            text = clean_text(el.get_text(" "))
            if text:
                titles.append(text)
    return list(dict.fromkeys(titles))[:20]


def extract_json_ld_products(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except Exception:
            continue
        candidates = data if isinstance(data, list) else [data]
        for obj in candidates:
            t = (obj.get("@type") or obj.get("type") or "")
            if isinstance(t, list):
                t = next((x for x in t if isinstance(x, str)), "")
            if isinstance(t, str) and t.lower() in {"product", "offer"}:
                name = obj.get("name")
                offers = obj.get("offers") or {}
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                price = offers.get("price")
                currency = offers.get("priceCurrency")
                description = obj.get("description")
                item: Dict[str, Any] = {}
                if name:
                    item["name"] = clean_text(str(name))
                if price:
                    p = f"{currency} {price}" if currency else str(price)
                    item["price"] = clean_text(p)
                if description:
                    item["description"] = clean_text(str(description))
                if item:
                    items.append(item)
    return items[:10]


def normalize_url(url: str) -> str:
    u = url.strip()
    if not re.match(r"^https?://", u, re.IGNORECASE):
        u = "http://" + u
    return u


def scrape(url: str, include_titles: bool = True, include_prices: bool = True, limit: int = 50) -> List[Dict[str, str]]:
    url = normalize_url(url)
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
        resp.raise_for_status()
    except Exception as e:
        print(f"Scrape error for {url}: {e}")
        return []
    ctype = (resp.headers.get("Content-Type") or "").lower()
    if "text/html" not in ctype and "application/xhtml" not in ctype:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    titles = extract_titles(soup) if include_titles else []
    prices = extract_prices(soup) if include_prices else []
    products = extract_json_ld_products(soup) if include_titles or include_prices else []
    items = []
    if titles:
        for t in titles:
            items.append({"title": t, "content": f"From {url}"})
    if products:
        for p in products:
            if p.get("name"):
                title = p["name"]
                parts = []
                if p.get("price"):
                    parts.append(p["price"])
                if p.get("description"):
                    parts.append(p["description"])
                content = " · ".join(parts) + (f" from {url}" if parts else f"From {url}")
                items.append({"title": title, "content": content})
    if prices:
        for p in prices:
            items.append({"title": "Price", "content": f"{p} from {url}"})
    return items[: max(1, min(limit, 100)) ]
