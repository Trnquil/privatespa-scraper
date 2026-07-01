"""Spa field schema: built-in fields plus custom fields stored in Firestore."""

from __future__ import annotations

import re

from firebase_admin import firestore

from firebase_client import init_firebase

SCHEMA_DOC_PATH = ("_config", "spa_schema")
FIELD_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
VALID_TYPES = ("string", "number", "boolean", "array")

BUILTIN_FIELDS: dict[str, dict] = {
    "name": {"type": "string", "label": "Name", "builtin": True},
    "slug": {"type": "string", "label": "Slug", "builtin": True},
    "premium": {"type": "boolean", "label": "Premium", "builtin": True},
    "description": {"type": "string", "label": "Description", "builtin": True},
    "location": {"type": "string", "label": "Location", "builtin": True},
    "canton": {"type": "string", "label": "Canton", "builtin": True},
    "website": {"type": "string", "label": "Website", "builtin": True},
    "price_from": {"type": "number", "label": "Price from (CHF)", "builtin": True},
    "coordinates": {"type": "coordinates", "label": "Coordinates", "builtin": True},
    "amenities": {"type": "array", "label": "Amenities", "builtin": True},
    "images": {"type": "array", "label": "Images", "builtin": True},
    "thumbnail": {"type": "string", "label": "Thumbnail", "builtin": True},
}

COMPLETENESS_EXCLUDED = frozenset({"premium", "thumbnail", "owner"})


def get_db():
    init_firebase()
    return firestore.client()


def _schema_ref():
    return get_db().collection(SCHEMA_DOC_PATH[0]).document(SCHEMA_DOC_PATH[1])


def _load_custom_fields() -> list[dict]:
    doc = _schema_ref().get()
    if not doc.exists:
        return []
    data = doc.to_dict() or {}
    custom = data.get("custom_fields") or []
    if not isinstance(custom, list):
        return []
    return [entry for entry in custom if isinstance(entry, dict) and entry.get("name")]


def _save_custom_fields(custom_fields: list[dict]) -> None:
    _schema_ref().set({"custom_fields": custom_fields}, merge=True)


def _normalize_field_name(name: str) -> str:
    return (name or "").strip().lower().replace("-", "_").replace(" ", "_")


def _field_label(name: str, label: str | None = None) -> str:
    if label and label.strip():
        return label.strip()
    return name.replace("_", " ").title()


def get_custom_fields() -> list[dict]:
    """Return custom field definitions from Firestore."""
    fields = []
    for entry in _load_custom_fields():
        name = _normalize_field_name(entry.get("name", ""))
        field_type = entry.get("type") or "string"
        if name not in BUILTIN_FIELDS and field_type in VALID_TYPES:
            fields.append(
                {
                    "name": name,
                    "type": field_type,
                    "label": _field_label(name, entry.get("label")),
                    "builtin": False,
                }
            )
    return fields


def get_all_fields() -> list[dict]:
    """Return built-in and custom field definitions."""
    builtin = [{**meta, "name": name} for name, meta in BUILTIN_FIELDS.items()]
    return builtin + get_custom_fields()


def get_spa_field_names() -> tuple[str, ...]:
    """All field names used when reading/writing spa documents."""
    custom_names = [field["name"] for field in get_custom_fields()]
    return tuple(BUILTIN_FIELDS.keys()) + tuple(custom_names)


def get_field_definition(name: str) -> dict | None:
    if name in BUILTIN_FIELDS:
        return {**BUILTIN_FIELDS[name], "name": name}
    for field in get_custom_fields():
        if field["name"] == name:
            return field
    return None


def get_completeness_field_names() -> tuple[str, ...]:
    """Fields checked for the incomplete (!) indicator."""
    return tuple(
        name for name in get_spa_field_names() if name not in COMPLETENESS_EXCLUDED
    )


def discover_extra_fields() -> list[dict]:
    """Find field keys present in spa documents but not in the schema."""
    known = set(get_spa_field_names())
    seen: dict[str, set[str]] = {}

    for doc in get_db().collection("spas").stream():
        data = doc.to_dict() or {}
        for key, value in data.items():
            if key in known or key.startswith("_"):
                continue
            types = seen.setdefault(key, set())
            types.add(_infer_type(value))

    discovered = []
    for name in sorted(seen):
        types = seen[name]
        field_type = next(iter(types)) if len(types) == 1 else "string"
        discovered.append(
            {
                "name": name,
                "type": field_type,
                "label": _field_label(name),
                "builtin": False,
                "discovered": True,
                "inferred_types": sorted(types),
            }
        )
    return discovered


def _infer_type(value) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, list):
        return "array"
    return "string"


def validate_field_name(name: str) -> str:
    normalized = _normalize_field_name(name)
    if not normalized:
        raise ValueError("Field name is required")
    if not FIELD_NAME_RE.match(normalized):
        raise ValueError(
            "Field name must start with a letter and use only lowercase letters, numbers, and underscores"
        )
    if normalized in BUILTIN_FIELDS:
        raise ValueError(f'"{normalized}" is a built-in field and cannot be added')
    return normalized


def add_custom_field(name: str, field_type: str, label: str | None = None) -> dict:
    """Add a custom field to the schema."""
    normalized = validate_field_name(name)
    if field_type not in VALID_TYPES:
        raise ValueError(f"Type must be one of: {', '.join(VALID_TYPES)}")

    custom_fields = _load_custom_fields()
    if any(
        _normalize_field_name(entry.get("name", "")) == normalized for entry in custom_fields
    ):
        raise ValueError(f'Field "{normalized}" already exists')

    entry = {
        "name": normalized,
        "type": field_type,
        "label": _field_label(normalized, label),
    }
    custom_fields.append(entry)
    _save_custom_fields(custom_fields)
    return {**entry, "builtin": False}


def remove_custom_field(name: str, *, strip_from_spas: bool = True) -> dict:
    """Remove a custom field from the schema and optionally from all spa documents."""
    normalized = _normalize_field_name(name)
    if not normalized:
        raise ValueError("Field name is required")
    if normalized in BUILTIN_FIELDS:
        raise ValueError(f'Cannot remove built-in field "{normalized}"')

    custom_fields = _load_custom_fields()
    remaining = [
        entry
        for entry in custom_fields
        if _normalize_field_name(entry.get("name", "")) != normalized
    ]
    if len(remaining) == len(custom_fields):
        raise ValueError(f'Custom field "{normalized}" not found in schema')

    _save_custom_fields(remaining)

    stripped_docs = 0
    if strip_from_spas:
        for doc in get_db().collection("spas").stream():
            data = doc.to_dict() or {}
            if normalized in data:
                doc.reference.update({normalized: firestore.DELETE_FIELD})
                stripped_docs += 1

    return {"name": normalized, "stripped_from_spas": stripped_docs}


def get_schema_payload() -> dict:
    """Full schema response for the dashboard."""
    return {
        "fields": get_all_fields(),
        "discovered": discover_extra_fields(),
    }
