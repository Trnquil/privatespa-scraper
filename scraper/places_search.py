"""Find spas in a region with the Google Places API (New) Text Search.

Requires "Places API (New)" to be enabled for GOOGLE_MAPS_API_KEY in the
Google Cloud console. One call returns up to 20 places; we follow the next
page token up to 3 pages (Google's maximum of 60 results per search).
"""

from __future__ import annotations

import os
import time

import httpx

from regions import Region, normalize_canton

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
MAX_PAGES = 3
GOOGLE_RESULT_CAP = 60


def search_queries() -> list[str]:
    """Search phrases, configurable via CRAWL_QUERIES (comma separated)."""
    raw = os.environ.get("CRAWL_QUERIES", "private spa")
    return [q.strip() for q in raw.split(",") if q.strip()]


def _component(place: dict, type_name: str, text: str = "shortText") -> str | None:
    for comp in place.get("addressComponents") or []:
        if type_name in (comp.get("types") or []):
            return comp.get(text)
    return None


def _normalize_place(place: dict) -> dict:
    location = place.get("location") or {}
    return {
        "place_id": place.get("id"),
        "name": (place.get("displayName") or {}).get("text"),
        "address": place.get("formattedAddress"),
        "website": place.get("websiteUri"),
        "business_status": place.get("businessStatus"),
        "country": _component(place, "country"),
        "canton": normalize_canton(_component(place, "administrative_area_level_1")),
        "lat": location.get("latitude"),
        "lng": location.get("longitude"),
    }


def search_region(region: Region, query: str) -> tuple[list[dict], bool]:
    """Search one phrase in one region.

    Returns (places, saturated). `saturated` means Google returned its maximum
    of 60 results, so some places may have been cut off.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_MAPS_API_KEY environment variable is not set")

    headers = {"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": FIELD_MASK}
    body: dict = {
        "textQuery": query,
        "pageSize": 20,
        "languageCode": "de",
        "regionCode": "CH",
        "locationRestriction": {
            "rectangle": {
                "low": {"latitude": region.south, "longitude": region.west},
                "high": {"latitude": region.north, "longitude": region.east},
            }
        },
    }

    places: list[dict] = []
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
            body = {**body, "pageToken": token}
            time.sleep(1)  # the next page token needs a moment to become valid

    return places, len(places) >= GOOGLE_RESULT_CAP
