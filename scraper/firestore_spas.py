"""Firestore access for the spas collection."""

from __future__ import annotations

from firebase_admin import firestore

from firebase_client import init_firebase

SPA_FIELDS = (
    "amenities",
    "canton",
    "coordinates",
    "description",
    "images",
    "location",
    "name",
    "thumbnail",
    "website",
)


def get_db():
    init_firebase()
    return firestore.client()


def _normalize_coordinates(value):
    if value is None:
        return None
    if hasattr(value, "latitude") and hasattr(value, "longitude"):
        return [float(value.latitude), float(value.longitude)]
    if isinstance(value, (list, tuple)) and len(value) == 2:
        try:
            return [float(value[0]), float(value[1])]
        except (TypeError, ValueError):
            return None
    return None


def _spa_to_editor_payload(doc_id: str, data: dict) -> dict:
    data = data or {}
    return {
        "id": doc_id,
        "data": {
            "amenities": list(data.get("amenities") or []),
            "canton": data.get("canton"),
            "coordinates": _normalize_coordinates(data.get("coordinates")),
            "description": data.get("description"),
            "images": list(data.get("images") or []),
            "location": data.get("location"),
            "name": data.get("name"),
            "thumbnail": data.get("thumbnail"),
            "website": data.get("website"),
        },
    }


def list_spas() -> list[dict]:
    """Return summary info for all spas, sorted by name."""
    spas = []
    for doc in get_db().collection("spas").stream():
        data = doc.to_dict() or {}
        spas.append(
            {
                "id": doc.id,
                "name": data.get("name") or "Untitled",
                "canton": data.get("canton"),
                "location": data.get("location"),
                "website": data.get("website"),
            }
        )
    spas.sort(key=lambda spa: (spa.get("name") or "").lower())
    return spas


def get_spa(spa_id: str) -> dict | None:
    """Return full spa data for the editor."""
    doc = get_db().collection("spas").document(spa_id).get()
    if not doc.exists:
        return None

    payload = _spa_to_editor_payload(doc.id, doc.to_dict())
    if not payload["data"].get("thumbnail"):
        from storage_images import get_stored_thumbnail_url

        stored_thumbnail = get_stored_thumbnail_url(spa_id)
        if stored_thumbnail:
            payload["data"]["thumbnail"] = stored_thumbnail

    return payload


def _build_spa_payload(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Spa data must be an object")

    payload = {}
    for field in SPA_FIELDS:
        if field not in data:
            continue
        value = data[field]
        if field == "coordinates":
            payload[field] = _normalize_coordinates(value)
        elif field in ("amenities", "images"):
            payload[field] = list(value or [])
        else:
            payload[field] = value
    return payload


def create_spa(data: dict) -> dict:
    """Create a new spa document with an auto-generated ID."""
    payload = _build_spa_payload(data)
    doc_ref = get_db().collection("spas").document()
    doc_ref.set(payload)
    return _spa_to_editor_payload(doc_ref.id, payload)


def update_spa(spa_id: str, data: dict) -> dict:
    """Update an existing spa document."""
    payload = _build_spa_payload(data)
    get_db().collection("spas").document(spa_id).update(payload)
    updated = get_spa(spa_id)
    if not updated:
        raise RuntimeError("Spa not found after update")
    return updated


def update_spa_thumbnail(spa_id: str, thumbnail_url: str) -> None:
    """Persist the spa thumbnail URL in Firestore."""
    get_db().collection("spas").document(spa_id).update({"thumbnail": thumbnail_url})
