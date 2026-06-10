"""Firebase Admin SDK initialization."""

from __future__ import annotations

import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CREDENTIALS_FILE = "privatespa-com-firebase-adminsdk-fbsvc-9d4b4739cd.json"


def get_project_id() -> str:
    """Return Firebase project ID from env or service account JSON."""
    configured = os.environ.get("FIREBASE_PROJECT_ID")
    if configured:
        return configured

    cred_path = get_credentials_path()
    if cred_path.is_file():
        import json

        with cred_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        project_id = data.get("project_id")
        if project_id:
            return project_id

    raise FileNotFoundError("Firebase project ID not configured")


def get_storage_bucket_name() -> str:
    """Resolve Firebase Storage bucket name."""
    configured = os.environ.get("FIREBASE_STORAGE_BUCKET")
    if configured:
        return configured
    return f"{get_project_id()}.firebasestorage.app"


def get_credentials_path() -> Path:
    """Resolve path to the Firebase service account JSON."""
    configured = os.environ.get("FIREBASE_CREDENTIALS_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return BASE_DIR / DEFAULT_CREDENTIALS_FILE


def init_firebase() -> firebase_admin.App:
    """Initialize Firebase Admin if not already initialized."""
    if firebase_admin._apps:
        return firebase_admin.get_app()

    cred_path = get_credentials_path()
    if not cred_path.is_file():
        raise FileNotFoundError(f"Firebase credentials not found: {cred_path}")

    cred = credentials.Certificate(str(cred_path))
    return firebase_admin.initialize_app(
        cred,
        {"storageBucket": get_storage_bucket_name()},
    )
