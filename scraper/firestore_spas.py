"""Firestore access for the spas collection."""

from __future__ import annotations

from firebase_admin import firestore

from firebase_client import init_firebase

# Fields stored on the public `spas/{id}` document (readable by anyone).
SPA_FIELDS = (
    "amenities",
    "canton",
    "coordinates",
    "description",
    "images",
    "location",
    "name",
    "owner",
    "premium",
    "price_from",
    "slug",
    "status",
    "google_place_id",
    "source",
    "thumbnail",
    "website",
)

# Fields stored on `spa_private/{id}`, which only the admin tool can read.
PRIVATE_FIELDS = ("contact",)
PRIVATE_COLLECTION = "spa_private"

DRAFT, PUBLISHED = "draft", "published"
STATUSES = (DRAFT, PUBLISHED)

DEFAULT_SPA_VALUES = {
    "premium": False,
    "status": PUBLISHED,
}

COMPLETENESS_EXCLUDED = frozenset(
    {"premium", "thumbnail", "owner", "status", "google_place_id", "source"}
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


def _normalize_premium(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return bool(value) if value is not None else False


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


def _normalize_string(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_status(value) -> str:
    # Spas created before drafts existed have no status and are live.
    return value if value in STATUSES else PUBLISHED


def _private_ref(spa_id: str):
    return get_db().collection(PRIVATE_COLLECTION).document(spa_id)


def _get_private(spa_id: str) -> dict:
    doc = _private_ref(spa_id).get()
    return (doc.to_dict() or {}) if doc.exists else {}


def _save_private(spa_id: str, data: dict) -> None:
    payload = {f: _normalize_string(data[f]) for f in PRIVATE_FIELDS if f in data}
    if payload:
        _private_ref(spa_id).set(payload, merge=True)


def _is_field_filled(value, field: str) -> bool:
    if field in ("amenities", "images"):
        return bool(value)
    if field == "coordinates":
        return _normalize_coordinates(value) is not None
    if field == "price_from":
        return _normalize_price_from(value) is not None
    if field == "name":
        text = (value or "").strip()
        return bool(text) and text.lower() != "untitled"
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return bool(value)


def get_spa_completeness(data: dict) -> dict:
    """Return whether a spa has all expected fields filled in."""
    data = data or {}
    missing_fields = [
        field
        for field in SPA_FIELDS
        if field not in COMPLETENESS_EXCLUDED
        and not _is_field_filled(data.get(field), field)
    ]
    return {
        "complete": not missing_fields,
        "missing_fields": missing_fields,
    }


def _spa_to_editor_payload(doc_id: str, data: dict, private: dict | None = None) -> dict:
    data = data or {}
    private = private or {}
    return {
        "id": doc_id,
        "data": {
            "amenities": list(data.get("amenities") or []),
            "canton": data.get("canton"),
            "contact": _normalize_string(private.get("contact")),
            "coordinates": _normalize_coordinates(data.get("coordinates")),
            "description": data.get("description"),
            "images": list(data.get("images") or []),
            "location": data.get("location"),
            "name": data.get("name"),
            "owner": _normalize_string(data.get("owner")),
            "premium": _normalize_premium(data.get("premium")),
            "price_from": _normalize_price_from(data.get("price_from")),
            "slug": data.get("slug"),
            "status": _normalize_status(data.get("status")),
            "google_place_id": data.get("google_place_id"),
            "source": data.get("source"),
            "thumbnail": data.get("thumbnail"),
            "website": data.get("website"),
        },
    }


def list_spas() -> list[dict]:
    """Return summary info for all spas, sorted by name."""
    spas = []
    private = {
        doc.id: doc.to_dict() or {}
        for doc in get_db().collection(PRIVATE_COLLECTION).stream()
    }
    for doc in get_db().collection("spas").stream():
        data = doc.to_dict() or {}
        completeness = get_spa_completeness(data)
        spas.append(
            {
                "id": doc.id,
                "name": data.get("name") or "Untitled",
                "canton": data.get("canton"),
                "location": data.get("location"),
                "website": data.get("website"),
                "owner": _normalize_string(data.get("owner")),
                "contact": _normalize_string(private.get(doc.id, {}).get("contact")),
                "premium": _normalize_premium(data.get("premium")),
                "status": _normalize_status(data.get("status")),
                "source": data.get("source"),
                "complete": completeness["complete"],
                "missing_fields": completeness["missing_fields"],
            }
        )
    spas.sort(key=lambda spa: (spa.get("name") or "").lower())
    return spas


def get_spa(spa_id: str) -> dict | None:
    """Return full spa data for the editor."""
    doc = get_db().collection("spas").document(spa_id).get()
    if not doc.exists:
        return None

    payload = _spa_to_editor_payload(doc.id, doc.to_dict(), _get_private(spa_id))
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
        elif field == "premium":
            payload[field] = _normalize_premium(value)
        elif field == "price_from":
            payload[field] = _normalize_price_from(value)
        elif field in ("owner", "google_place_id", "source"):
            payload[field] = _normalize_string(value)
        elif field == "status":
            if value not in STATUSES:
                raise ValueError(f"Invalid status: {value!r}")
            payload[field] = value
        elif field in ("amenities", "images"):
            payload[field] = list(value or [])
        else:
            payload[field] = value
    return payload


def create_spa(data: dict) -> dict:
    """Create a new spa document with an auto-generated ID."""
    merged = {**DEFAULT_SPA_VALUES, **(data or {})}
    payload = _build_spa_payload(merged)
    doc_ref = get_db().collection("spas").document()
    doc_ref.set(payload)
    _save_private(doc_ref.id, merged)
    return _spa_to_editor_payload(doc_ref.id, payload, {f: merged.get(f) for f in PRIVATE_FIELDS})


def update_spa(spa_id: str, data: dict) -> dict:
    """Update an existing spa document."""
    payload = _build_spa_payload(data)
    get_db().collection("spas").document(spa_id).update(payload)
    _save_private(spa_id, data or {})
    updated = get_spa(spa_id)
    if not updated:
        raise RuntimeError("Spa not found after update")
    return updated


def update_spa_thumbnail(spa_id: str, thumbnail_url: str) -> None:
    """Persist the spa thumbnail URL in Firestore."""
    get_db().collection("spas").document(spa_id).update({"thumbnail": thumbnail_url})


def delete_spa(spa_id: str) -> dict:
    """Delete a spa document and all associated Firebase Storage files."""
    if not spa_id:
        raise ValueError("Spa ID is required")

    doc_ref = get_db().collection("spas").document(spa_id)
    if not doc_ref.get().exists:
        raise ValueError("Spa not found")

    from storage_images import delete_spa_storage

    deleted_files = delete_spa_storage(spa_id)
    doc_ref.delete()
    _private_ref(spa_id).delete()
    return {"id": spa_id, "deleted_storage_files": deleted_files}


def normalize_website(url: str | None) -> str | None:
    """Comparable form of a website URL: host without www + path, no scheme or slash."""
    if not url:
        return None
    from urllib.parse import urlparse

    text = url.strip().lower()
    if "://" not in text:
        text = "https://" + text
    parsed = urlparse(text)
    host = (parsed.hostname or "").removeprefix("www.")
    if not host:
        return None
    path = parsed.path.rstrip("/")
    return host + path


def existing_spa_index() -> dict:
    """Place ids, websites and slugs already in Firestore, for deduplication."""
    place_ids: set[str] = set()
    websites: dict[str, str] = {}
    slugs: set[str] = set()
    for doc in get_db().collection("spas").select(["google_place_id", "website", "slug"]).stream():
        data = doc.to_dict() or {}
        if data.get("google_place_id"):
            place_ids.add(data["google_place_id"])
        site = normalize_website(data.get("website"))
        if site:
            websites[site] = doc.id
        if data.get("slug"):
            slugs.add(data["slug"])
    domains = {site.split("/", 1)[0]: spa_id for site, spa_id in websites.items()}
    return {"place_ids": place_ids, "websites": websites, "domains": domains, "slugs": slugs}
