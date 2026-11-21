#!/usr/bin/env python3
"""Local MVP scraper: fetch a spa website and extract structured spa data via OpenAI."""

from __future__ import annotations

import ipaddress
import unicodedata
import json
import re
import sys
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from geocoding import geocode_location
from openai import OpenAI
import os

load_dotenv()

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HTTP_TIMEOUT = 15.0
MIN_TEXT_LENGTH = 500
MAX_OPENAI_TEXT = 10_000
RAW_PREVIEW_LENGTH = 300
GENERIC_HOST_LABELS = {"www", "app", "m", "shop", "booking", "web", "mail"}


def normalize_url(url: str) -> str:
    """Add https:// when the user enters a bare domain like laspasuite.ch."""
    url = url.strip()
    if not url:
        return url
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def validate_url(url: str) -> str:
    """Validate URL scheme and reject unsafe local/private targets."""
    url = normalize_url(url)
    if not url.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")

    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError("Invalid URL: missing host")

    host = parsed.hostname
    if not host:
        raise ValueError("Invalid URL: missing hostname")

    host_lower = host.lower()
    blocked_hosts = {"localhost", "0.0.0.0"}
    if host_lower in blocked_hosts or host_lower.endswith(".local"):
        raise ValueError(f"Unsafe URL: blocked host '{host}'")

    if host_lower == "127.0.0.1" or host_lower.startswith("127."):
        raise ValueError(f"Unsafe URL: blocked host '{host}'")

    # Resolve IP literals and reject private/reserved ranges
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # Not an IP literal — hostname is fine if not in blocked list
        return url

    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
        raise ValueError(f"Unsafe URL: private or reserved IP '{host}'")

    return url


def normalize_slug(value: str) -> str | None:
    """Normalize a string into a URL-friendly slug."""
    if not value:
        return None
    slug = value.lower().strip()
    # Same rules as the website: umlauts become ae/oe/ue, then only a-z, 0-9 and dashes.
    for src, dst in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        slug = slug.replace(src, dst)
    slug = unicodedata.normalize("NFKD", slug).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9\-]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or None


def extract_slug_from_url(url: str) -> str | None:
    """Derive a slug from the spa website URL (e.g. hirschen.ch -> hirschen)."""
    parsed = urlparse(normalize_url(url))
    host = (parsed.hostname or "").lower()
    if not host:
        return None

    if host.startswith("www."):
        host = host[4:]

    labels = host.split(".")
    if len(labels) >= 2:
        slug = labels[0]
        if slug in GENERIC_HOST_LABELS and len(labels) >= 3:
            slug = labels[1]
        normalized = normalize_slug(slug)
        if normalized:
            return normalized

    path_parts = [part for part in parsed.path.split("/") if part]
    if path_parts:
        return normalize_slug(path_parts[-1])

    return None


def fetch_with_httpx(url: str) -> str:
    """Fetch page HTML using httpx."""
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        return response.text


def fetch_with_playwright(url: str) -> str:
    """Fetch rendered HTML using headless Chromium."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=USER_AGENT)
            page.goto(url, wait_until="networkidle", timeout=int(HTTP_TIMEOUT * 1000))
            return page.content()
        finally:
            browser.close()


def parse_html(html: str) -> BeautifulSoup:
    """Parse raw HTML into a BeautifulSoup document."""
    return BeautifulSoup(html, "lxml")


def extract_image_urls(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Extract absolute image URLs from img tags and og:image meta tags."""
    urls: list[str] = []
    seen: set[str] = set()

    def add_url(raw: str | None) -> None:
        if not raw or raw.startswith("data:"):
            return
        absolute = urljoin(base_url, raw.strip())
        if absolute not in seen:
            seen.add(absolute)
            urls.append(absolute)

    for meta in soup.find_all(
        "meta", attrs={"property": re.compile(r"^og:image", re.I)}
    ):
        add_url(meta.get("content"))

    for img in soup.find_all("img"):
        for attr in ("src", "data-src", "data-lazy-src"):
            if img.get(attr):
                add_url(img[attr])
                break

    return urls


def _collect_address_strings(obj) -> list[str]:
    """Recursively collect address strings from JSON-LD objects."""
    found: list[str] = []

    if isinstance(obj, dict):
        address = obj.get("address")
        if isinstance(address, str) and address.strip():
            found.append(address.strip())
        elif isinstance(address, dict):
            parts = [
                address.get("streetAddress"),
                address.get("postalCode"),
                address.get("addressLocality"),
                address.get("addressRegion"),
                address.get("addressCountry"),
            ]
            line = ", ".join(str(part).strip() for part in parts if part)
            if line:
                found.append(line)

        for value in obj.values():
            found.extend(_collect_address_strings(value))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_collect_address_strings(item))

    return found


def extract_address_hints(soup: BeautifulSoup) -> list[str]:
    """Extract postal addresses from HTML before noisy sections are removed."""
    hints: list[str] = []
    seen: set[str] = set()

    def add_hint(text: str) -> None:
        normalized = " ".join(text.split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            hints.append(normalized)

    for tag in soup.find_all("address"):
        add_hint(tag.get_text(separator=" ", strip=True))

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for address in _collect_address_strings(payload):
            add_hint(address)

    return hints


def extract_visible_text(soup: BeautifulSoup) -> str:
    """Extract useful visible text from a parsed HTML document."""
    for tag in soup.find_all(
        ["script", "style", "nav", "footer", "header", "noscript", "svg", "form"]
    ):
        tag.decompose()

    parts: list[str] = []

    if soup.title and soup.title.string:
        parts.append(soup.title.string.strip())

    meta_desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if meta_desc and meta_desc.get("content"):
        parts.append(meta_desc["content"].strip())

    for meta in soup.find_all("meta"):
        name = (meta.get("name") or meta.get("property") or "").lower()
        content = meta.get("content")
        if not content:
            continue
        if any(k in name for k in ("geo", "latitude", "longitude", "icbm")):
            parts.append(
                f"{meta.get('name') or meta.get('property')}: {content.strip()}"
            )

    for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = tag.get_text(separator=" ", strip=True)
        if text:
            parts.append(text)

    seen: set[str] = set()
    unique_parts: list[str] = []
    for part in parts:
        normalized = " ".join(part.split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique_parts.append(normalized)

    return "\n".join(unique_parts)


def _normalize_coordinates(value) -> list[float] | None:
    """Validate coordinates as [latitude, longitude] or return null."""
    if not isinstance(value, list) or len(value) != 2:
        return None
    try:
        lat, lng = float(value[0]), float(value[1])
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    return [lat, lng]


def _normalize_price_from(value):
    if value is None or value == "":
        return None
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    if price < 0:
        return None
    return int(price) if price.is_integer() else price


def extract_spa_info_with_openai(text: str, url: str, image_urls: list[str]) -> dict:
    """Send extracted text to OpenAI and return structured spa data."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY environment variable is not set")

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key)

    truncated = text[:MAX_OPENAI_TEXT]

    system_prompt = (
        "You extract spa or wellness venue information from website text. "
        "The website may be written in German, English, French, Italian or another language. "
        "Read it in its own language, then always write description_de and amenities_de in "
        "natural German and description_en and amenities_en in natural English: translate "
        "faithfully, keep the facts, do not add anything, and keep proper names, brand names "
        "and place names as they are (e.g. 'Le Spa des Alpes', 'Suite Romantica'). Translate "
        "local terms correctly: French 'spa privatif' / Italian 'spa privata' = Private Spa "
        "(German) / private spa (English); 'jacuzzi privatif' = privater Whirlpool / private "
        "hot tub; 'hammam' = Hammam; 'nuitée' / 'pernottamento' = Übernachtung / overnight "
        "stay. "
        "Return ONLY valid JSON with exactly these keys: "
        "name, description, amenities, location, canton, coordinates, price_from, "
        "is_private_spa, private_spa_evidence, private_spa_reason, description_de, description_en, "
        "amenities_de, amenities_en, country. "
        "name: official venue or offer name, or null if unclear. "
        "description: 1-3 polished sentences in the same language as the website text, "
        "factual and based ONLY on the provided text. "
        "amenities: array of amenity or feature strings mentioned on the page (empty array if none). "
        "location: the most precise physical address or location available on the page. "
        "Prefer a full street address with postal code, city, and country when present "
        "(e.g. 'Hertensteinstrasse 42, 6353 Weggis, Schweiz'). "
        "If no street address exists, use the most specific place name available. "
        "Do not invent address parts. null if unclear. "
        "canton: the region the venue is in, if identifiable: the Swiss canton, the German or "
        "Austrian federal state, the Italian region or the French région, using its German "
        "name (e.g. Zürich, Bayern, Tirol, Toskana, Okzitanien); otherwise null. "
        "coordinates: [latitude, longitude] ONLY if explicitly present in the text "
        "(e.g. geo meta tags or map data), otherwise null. "
        "price_from: lowest starting price as a number, if explicitly mentioned "
        "on the page, in the page's currency (CHF in Switzerland, EUR in Germany, Austria, "
        "Italy and France; e.g. 'ab CHF 150' -> 150, 'ab 180 €' -> 180, 'à partir de 89 €' -> 89, "
        "'da 120 €' -> 120), otherwise null. "
        "is_private_spa: decide strictly by this definition. A PRIVATE SPA is a spa or "
        "wellness area (sauna, whirlpool/jacuzzi, steam bath, pool, …) that guests book for "
        "EXCLUSIVE use: only the booking person and their own companions are inside, no other "
        "guests, for a booked time slot or stay. It counts as a private spa if the page shows "
        "at least one of: (a) a spa/wellness area or spa suite rented by the hour or by the "
        "slot for exclusive use ('Private Spa', 'Privatspa', 'exklusiv für Sie', 'nur für "
        "Sie allein', 'zu mieten', 'stundenweise'; French: 'spa privatif', 'spa privé', "
        "'privatisé', 'privatisable', 'rien que pour vous', 'à l'heure', 'location'; Italian: "
        "'spa privata', 'in esclusiva', 'uso esclusivo', 'solo per voi', 'a ore', 'noleggio'); (b) a hotel that offers a SEPARATELY "
        "bookable private spa suite or private spa room for exclusive use, in addition to its "
        "normal spa; (c) a room, suite, chalet or holiday home with its OWN sauna, whirlpool "
        "or spa used only by the guests staying there. It is NOT a private spa if the "
        "wellness area is shared: a hotel spa, day spa, thermal bath, public sauna, wellness "
        "centre or fitness club where several guests or groups use the facilities at the "
        "same time, even if it is luxurious, adults-only, small, or 'exclusive to hotel "
        "guests'. Massage studios, beauty salons and treatment rooms alone are not private "
        "spas. If the page does not clearly say the spa is booked for exclusive use, answer "
        "false. "
        "private_spa_evidence: when is_private_spa is true, quote the exact sentence or "
        "phrase from the website text that shows exclusive booking (in its original "
        "language); otherwise null. "
        "private_spa_reason: one short sentence in English explaining is_private_spa. "
        "description_de and description_en: the description in German and in natural "
        "British English (same facts). amenities_de and amenities_en: the same amenity "
        "list in German and in English, in the same order; keep brand and place names. "
        "country: ISO code of the venue's country (CH, DE, AT, IT or FR), or null. "
        "Do NOT invent amenities, prices, locations, coordinates, or services. "
        "Return null for description if there is not enough information."
    )

    user_prompt = f"Source URL: {url}\n\nWebsite text:\n{truncated}"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("OpenAI returned an empty response")

    try:
        result = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"OpenAI returned invalid JSON: {e}") from e

    if not isinstance(result, dict):
        raise ValueError("OpenAI response is not a JSON object")

    def _str_list(value):
        return [str(a).strip() for a in value if a] if isinstance(value, list) else []

    amenities = _str_list(result.get("amenities_de")) or _str_list(result.get("amenities"))
    amenities_en = _str_list(result.get("amenities_en"))
    country = (result.get("country") or "").upper()

    return {
        # Only accept a "yes" that comes with a quoted proof of exclusive booking.
        "is_private_spa": result.get("is_private_spa") is True
        and bool(str(result.get("private_spa_evidence") or "").strip()),
        "private_spa_evidence": result.get("private_spa_evidence"),
        "private_spa_reason": result.get("private_spa_reason"),
        "data": {
            "amenities": amenities,
            "amenities_en": amenities_en,
            "country": country if country in ("CH", "DE", "AT", "IT", "FR") else None,
            "description_en": result.get("description_en"),
            "canton": result.get("canton"),
            "coordinates": _normalize_coordinates(result.get("coordinates")),
            "description": result.get("description_de") or result.get("description"),
            "images": image_urls,
            "location": result.get("location"),
            "name": result.get("name"),
            "premium": False,
            "price_from": _normalize_price_from(result.get("price_from")),
            "slug": extract_slug_from_url(url),
            "website": url,
        }
    }


def apply_geocoding(spa_info: dict) -> dict:
    """Fill in coordinates from Google Geocoding when location is known."""
    data = spa_info.get("data") or {}
    if data.get("coordinates"):
        return spa_info

    location = (data.get("location") or "").strip()
    if not location:
        return spa_info

    coordinates = geocode_location(location)
    if coordinates:
        data["coordinates"] = coordinates

    return spa_info


def scrape_url(url: str) -> dict:
    """Scrape a spa URL and return structured result with metadata."""
    url = url.strip()
    validate_url(url)

    used_playwright = False
    html = None

    try:
        html = fetch_with_httpx(url)
    except httpx.TimeoutException as e:
        raise TimeoutError("Request timed out while fetching the page") from e
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP error {e.response.status_code}") from e
    except httpx.RequestError as e:
        raise RuntimeError(f"Failed to fetch page: {e}") from e

    soup = parse_html(html) if html else None
    image_urls = extract_image_urls(soup, url) if soup else []
    address_hints = extract_address_hints(soup) if soup else []
    text = extract_visible_text(soup) if soup else ""

    if address_hints:
        text = "Addresses found on page:\n" + "\n".join(address_hints) + "\n\n" + text

    if len(text) < MIN_TEXT_LENGTH:
        try:
            html = fetch_with_playwright(url)
            used_playwright = True
            soup = parse_html(html)
            image_urls = extract_image_urls(soup, url)
            address_hints = extract_address_hints(soup)
            text = extract_visible_text(soup)
            if address_hints:
                text = (
                    "Addresses found on page:\n"
                    + "\n".join(address_hints)
                    + "\n\n"
                    + text
                )
        except Exception as e:
            raise RuntimeError(f"Playwright fetch failed: {e}") from e

    if len(text) < MIN_TEXT_LENGTH:
        raise RuntimeError("Extracted text is too short even after Playwright fallback")

    spa_info = extract_spa_info_with_openai(text, url, image_urls)
    spa_info = apply_geocoding(spa_info)

    return {
        **spa_info,
        "source_url": url,
        "used_playwright": used_playwright,
        "raw_text_preview": text[:RAW_PREVIEW_LENGTH],
    }


SPA_LINK_PATTERNS = [
    (re.compile(r"priva\w*[\s_-]*spa|spa[\s_-]*priv", re.I), 3),
    (re.compile(r"spa[\s_-]*suite|wellness[\s_-]*suite|day[\s_-]*spa[\s_-]*suite", re.I), 2),
    (re.compile(r"\bspa\b|wellness|sauna|jacuzzi|bien-?etre|bien-?être|benessere|hammam", re.I), 1),
]


def find_spa_links(url: str, limit: int = 2) -> list[str]:
    """Links on a page (same site) that most likely lead to its private spa offer."""
    try:
        soup = parse_html(fetch_with_httpx(url))
    except Exception:
        return []
    base_host = (urlparse(url).hostname or "").removeprefix("www.")
    scored: dict[str, int] = {}
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"]).split("#")[0]
        parsed = urlparse(href)
        if parsed.scheme not in ("http", "https"):
            continue
        if (parsed.hostname or "").removeprefix("www.") != base_host or href.rstrip("/") == url.rstrip("/"):
            continue
        haystack = f"{a.get_text(' ', strip=True)} {parsed.path}"
        score = max((weight for pattern, weight in SPA_LINK_PATTERNS if pattern.search(haystack)), default=0)
        if score:
            scored[href] = max(score, scored.get(href, 0))
    return [h for h, _ in sorted(scored.items(), key=lambda kv: -kv[1])][:limit]


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scrape_spa.py <url>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1].strip()

    try:
        output = scrape_url(url)
    except ValueError as e:
        print(json.dumps({"error": str(e)}, indent=2))
        sys.exit(1)
    except EnvironmentError as e:
        print(json.dumps({"error": str(e)}, indent=2))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
        sys.exit(1)

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
