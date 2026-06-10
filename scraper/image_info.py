"""Fetch image dimensions and file size from a URL."""

from __future__ import annotations

import io

import httpx
from PIL import Image, UnidentifiedImageError

from scrape_spa import validate_url

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HTTP_TIMEOUT = 30.0


def get_image_info(url: str) -> dict:
    """Return width, height, and size in KB for an image URL."""
    url = validate_url(url)
    headers = {"User-Agent": USER_AGENT}

    with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        content_type = (response.headers.get("content-type") or "").lower()
        if content_type.startswith("text/"):
            raise ValueError(f"URL returned HTML instead of an image ({content_type})")
        data = response.content

    try:
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
    except UnidentifiedImageError as e:
        raise ValueError("Unsupported or corrupt image data") from e

    size_kb = round(len(data) / 1024, 1)
    return {
        "width": width,
        "height": height,
        "size_kb": size_kb,
    }
