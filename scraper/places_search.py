"""Find spas in a region with the Google Places API (New) Text Search.

Requires "Places API (New)" to be enabled for GOOGLE_MAPS_API_KEY in the
Google Cloud console. Each region is searched with several phrases, and for
each phrase only Google's top 20 results are used (one page): the most
relevant hits per phrase, at one request per phrase and region.
"""

from __future__ import annotations

import os
import time

import httpx

from regions import Region, normalize_region

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.addressComponents",
        "places.location",
        "places.websiteUri",
        "places.businessStatus",
        "nextPageToken",
    ]
)
MAX_PAGES = 1  # top 20 per phrase

# Search phrases per country, in the words people there use.
COUNTRY_QUERIES: dict[str, list[str]] = {
    "CH": ["private spa", "privatspa", "wellness suite", "romantik zimmer whirlpool"],
    "DE": ["private spa", "privatspa", "wellness suite", "romantik zimmer whirlpool"],
    "AT": ["private spa", "privatspa", "wellness suite", "romantik zimmer whirlpool"],
    "IT": ["spa privata", "private spa", "suite con spa privata", "jacuzzi privata"],
    "FR": ["spa privatif", "jacuzzi privatif", "love room spa", "suite avec spa privatif"],
}
# Language Google answers in (names, addresses): the country's own language.
COUNTRY_LANGUAGE = {"CH": "de", "DE": "de", "AT": "de", "IT": "it", "FR": "fr"}


def search_queries(country: str = "CH") -> list[str]:
    """Search phrases for a country; CRAWL_QUERIES (comma separated) overrides them for all."""
    raw = os.environ.get("CRAWL_QUERIES")
    if raw:
        return [q.strip() for q in raw.split(",") if q.strip()]
    return COUNTRY_QUERIES.get(country, COUNTRY_QUERIES["CH"])


def _component(place: dict, type_name: str, text: str = "shortText") -> str | None:
    for comp in place.get("addressComponents") or []:
        if type_name in (comp.get("types") or []):
            return comp.get(text)
    return None


def _normalize_place(place: dict) -> dict:
    location = place.get("location") or {}
    country = _component(place, "country")
    # Google gives "ZH"/"BY" as short text and "Tirol"/"Bayern" as long text; try both.
    region = normalize_region(country, _component(place, "administrative_area_level_1")) or normalize_region(
        country, _component(place, "administrative_area_level_1", "longText")
    )
    return {
        "place_id": place.get("id"),
        "name": (place.get("displayName") or {}).get("text"),
        "address": place.get("formattedAddress"),
        "website": place.get("websiteUri"),
        "business_status": place.get("businessStatus"),
        "country": country,
        "canton": region,
        "lat": location.get("latitude"),
        "lng": location.get("longitude"),
    }


def search_region(region: Region, query: str) -> tuple[list[dict], bool]:
    """Search one phrase in one region.

    Returns (places, more_available). `more_available` means Google had more
    results than the top 20 we take.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_MAPS_API_KEY environment variable is not set")

    headers = {"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": FIELD_MASK}
    body: dict = {
        "textQuery": query,
        "pageSize": 20,
        "languageCode": COUNTRY_LANGUAGE.get(region.country, "de"),
        "regionCode": region.country,
        "locationRestriction": {
            "rectangle": {
                "low": {"latitude": region.south, "longitude": region.west},
                "high": {"latitude": region.north, "longitude": region.east},
            }
        },
    }

    places: list[dict] = []
    more_available = False
    with httpx.Client(timeout=30) as client:
        for page in range(MAX_PAGES):
            response = client.post(SEARCH_URL, headers=headers, json=body)
            if response.status_code >= 400:
                raise RuntimeError(
                    f"Places search failed ({response.status_code}): {response.text[:300]}"
                )
            data = response.json()
            places.extend(_normalize_place(p) for p in data.get("places") or [])
            token = data.get("nextPageToken")
            if not token:
                break
            if page == MAX_PAGES - 1:
                more_available = True
                break
            body = {**body, "pageToken": token}
            time.sleep(1)  # the next page token needs a moment to become valid

    return places, more_available
