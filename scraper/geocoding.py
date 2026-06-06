"""Google Maps Geocoding helpers."""

from __future__ import annotations

import os

import httpx

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
HTTP_TIMEOUT = 15.0


def _normalize_coordinates(value) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    try:
        lat, lng = float(value[0]), float(value[1])
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    return [lat, lng]


def geocode_location(location: str) -> list[float] | None:
    """Return [latitude, longitude] for a location string using Google Geocoding."""
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    location = location.strip()
    if not api_key or not location:
        return None

    params = {
        "address": location,
        "key": api_key,
        "region": "ch",
    }

    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        response = client.get(GEOCODE_URL, params=params)
        response.raise_for_status()
        data = response.json()

    status = data.get("status")
    if status != "OK" or not data.get("results"):
        return None

    loc = data["results"][0]["geometry"]["location"]
    return _normalize_coordinates([loc["lat"], loc["lng"]])
