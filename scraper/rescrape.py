"""Re-scrape a spa website to fill in missing fields only."""

from __future__ import annotations

from firestore_spas import _is_field_filled, get_spa_completeness
from scrape_spa import extract_slug_from_url, scrape_url

SCRAPE_FILLABLE_FIELDS = (
    "amenities",
    "canton",
    "coordinates",
    "description",
    "images",
    "location",
    "name",
    "price_from",
    "slug",
    "website",
)


def _missing_scrapeable_fields(data: dict) -> list[str]:
    completeness = get_spa_completeness(data)
    return [
        field
        for field in completeness["missing_fields"]
        if field in SCRAPE_FILLABLE_FIELDS
    ]


def merge_scraped_missing_fields(
    current: dict, scraped: dict, source_url: str
) -> tuple[dict, list[str]]:
    """Fill empty fields in current data with scraped values."""
    merged = dict(current or {})
    scraped = scraped or {}
    filled: list[str] = []

    for field in SCRAPE_FILLABLE_FIELDS:
        if _is_field_filled(merged.get(field), field):
            continue

        value = scraped.get(field)
        if field == "slug" and not _is_field_filled(value, field):
            value = extract_slug_from_url(source_url)

        if _is_field_filled(value, field):
            merged[field] = value
            filled.append(field)

    return merged, filled


def rescrape_missing_fields(current_data: dict) -> dict:
    """Scrape the spa website and return data with missing fields filled in."""
    current_data = current_data or {}
    missing = _missing_scrapeable_fields(current_data)

    if not missing:
        return {
            "data": current_data,
            "filled_fields": [],
            "still_missing": get_spa_completeness(current_data)["missing_fields"],
            "used_playwright": False,
        }

    website = (current_data.get("website") or "").strip()
    if not website:
        raise ValueError("Website URL is required to rescrape missing fields")

    scraped = scrape_url(website)
    scraped_data = scraped.get("data") or {}
    merged, filled = merge_scraped_missing_fields(
        current_data,
        scraped_data,
        website,
    )

    return {
        "data": merged,
        "filled_fields": filled,
        "still_missing": get_spa_completeness(merged)["missing_fields"],
        "used_playwright": scraped.get("used_playwright", False),
    }
