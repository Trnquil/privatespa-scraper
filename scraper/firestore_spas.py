"""Firestore access for the spas collection."""

from __future__ import annotations

from firebase_admin import firestore

from firebase_client import init_firebase
from spa_schema import get_completeness_field_names, get_field_definition, get_spa_field_names

DEFAULT_SPA_VALUES = {
    "premium": False,
}


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
    definition = get_field_definition(field)
    if definition:
        field_type = definition.get("type")
        if field_type == "boolean":
            return True
        if field_type == "array":
            return bool(value)
        if field_type == "number":
            return _normalize_custom_number(value) is not None
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return bool(value)


def _normalize_custom_number(value):
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def _normalize_custom_value(value, field_type: str):
    if field_type == "boolean":
        return _normalize_premium(value)
    if field_type == "number":
        return _normalize_custom_number(value)
    if field_type == "array":
        if isinstance(value, str):
            return [line.strip() for line in value.splitlines() if line.strip()]
        return list(value or [])
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _serialize_field_value(name: str, value):
    definition = get_field_definition(name)
    if not definition:
        return value
    field_type = definition.get("type")
    if field_type == "coordinates":
        return _normalize_coordinates(value)
    if field_type == "boolean" or name == "premium":
        return _normalize_premium(value)
    if field_type == "number" or name == "price_from":
        if name == "price_from":
            return _normalize_price_from(value)
        return _normalize_custom_number(value)
    if field_type == "array" or name in ("amenities", "images"):
        return list(value or [])
    return value


def _editor_field_value(name: str, value):
    definition = get_field_definition(name)
    if not definition:
        return value
    field_type = definition.get("type")
    if field_type == "coordinates":
        return _normalize_coordinates(value)
    if field_type == "boolean" or name == "premium":
        return _normalize_premium(value)
    if field_type == "number" or name == "price_from":
        if name == "price_from":
            return _normalize_price_from(value)
        return _normalize_custom_number(value)
    if field_type == "array" or name in ("amenities", "images"):
        return list(value or [])
    return value


def get_spa_completeness(data: dict) -> dict:
    """Return whether a spa has all expected fields filled in."""
    data = data or {}
    missing_fields = [
        field
        for field in get_completeness_field_names()
        if not _is_field_filled(data.get(field), field)
    ]
    return {
        "complete": not missing_fields,
        "missing_fields": missing_fields,
    }


def _spa_to_editor_payload(doc_id: str, data: dict) -> dict:
    data = data or {}
    payload_data = {}
    for field in get_spa_field_names():
        payload_data[field] = _editor_field_value(field, data.get(field))
    return {"id": doc_id, "data": payload_data}


def list_spas() -> list[dict]:
    """Return summary info for all spas, sorted by name."""
    spas = []
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
                "owner": (data.get("owner") or "").strip() or None,
                "premium": _normalize_premium(data.get("premium")),
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
    for field in get_spa_field_names():
        if field not in data:
            continue
        payload[field] = _serialize_field_value(field, data[field])
    return payload


def create_spa(data: dict) -> dict:
    """Create a new spa document with an auto-generated ID."""
    merged = {**DEFAULT_SPA_VALUES, **(data or {})}
    payload = _build_spa_payload(merged)
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
    return {"id": spa_id, "deleted_storage_files": deleted_files}
