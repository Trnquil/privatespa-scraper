#!/usr/bin/env python3
"""Local MVP scraper: fetch a spa website and extract structured spa data via OpenAI."""

import ipaddress
import json
import re
import sys
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
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


def validate_url(url: str) -> str:
    """Validate URL scheme and reject unsafe local/private targets."""
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

    for meta in soup.find_all("meta", attrs={"property": re.compile(r"^og:image", re.I)}):
        add_url(meta.get("content"))

    for img in soup.find_all("img"):
        for attr in ("src", "data-src", "data-lazy-src"):
            if img.get(attr):
                add_url(img[attr])
                break

    return urls


def extract_visible_text(soup: BeautifulSoup) -> str:
    """Extract useful visible text from a parsed HTML document."""
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "noscript", "svg", "form"]):
        tag.decompose()

    parts: list[str] = []

    if soup.title and soup.title.string:
        parts.append(soup.title.string.strip())

    meta_desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if meta_desc and meta_desc.get("content"):
        parts.append(meta_desc["content"].strip())

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
        "Return ONLY valid JSON with exactly these keys: "
        "name, description, amenities, location, canton, coordinates. "
        "name: official venue or offer name, or null if unclear. "
        "description: 1-3 polished sentences in the same language as the website text, "
        "factual and based ONLY on the provided text. "
        "amenities: array of amenity or feature strings mentioned on the page (empty array if none). "
        "location: human-readable location string (e.g. 'Hirschen Ramsen, Ramsen, Schweiz'), or null. "
        "canton: Swiss canton name if identifiable from the text, otherwise null. "
        "coordinates: [latitude, longitude] ONLY if explicitly present in the text "
        "(e.g. geo meta tags or map data), otherwise null. "
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

    amenities = result.get("amenities")
    if not isinstance(amenities, list):
        amenities = []
    else:
        amenities = [str(a).strip() for a in amenities if a]

    return {
        "data": {
            "amenities": amenities,
            "canton": result.get("canton"),
            "coordinates": _normalize_coordinates(result.get("coordinates")),
            "description": result.get("description"),
            "images": image_urls,
            "location": result.get("location"),
            "name": result.get("name"),
            "website": url,
        }
    }


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scrape_spa.py <url>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1].strip()
    used_playwright = False

    try:
        validate_url(url)
    except ValueError as e:
        print(json.dumps({"error": str(e)}, indent=2))
        sys.exit(1)

    html = None
    try:
        html = fetch_with_httpx(url)
    except httpx.TimeoutException:
        print(json.dumps({"error": "Request timed out while fetching the page"}, indent=2))
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(json.dumps({"error": f"HTTP error {e.response.status_code}"}, indent=2))
        sys.exit(1)
    except httpx.RequestError as e:
        print(json.dumps({"error": f"Failed to fetch page: {e}"}, indent=2))
        sys.exit(1)

    soup = parse_html(html) if html else None
    image_urls = extract_image_urls(soup, url) if soup else []
    text = extract_visible_text(soup) if soup else ""

    if len(text) < MIN_TEXT_LENGTH:
        try:
            html = fetch_with_playwright(url)
            used_playwright = True
            soup = parse_html(html)
            image_urls = extract_image_urls(soup, url)
            text = extract_visible_text(soup)
        except Exception as e:
            print(json.dumps({"error": f"Playwright fetch failed: {e}"}, indent=2))
            sys.exit(1)

    if len(text) < MIN_TEXT_LENGTH:
        print(
            json.dumps(
                {"error": "Extracted text is too short even after Playwright fallback"},
                indent=2,
            )
        )
        sys.exit(1)

    try:
        spa_info = extract_spa_info_with_openai(text, url, image_urls)
    except EnvironmentError as e:
        print(json.dumps({"error": str(e)}, indent=2))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"OpenAI API failure: {e}"}, indent=2))
        sys.exit(1)

    output = {
        **spa_info,
        "source_url": url,
        "used_playwright": used_playwright,
        "raw_text_preview": text[:RAW_PREVIEW_LENGTH],
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
