"""Download spa images, convert to WebP, and upload to Firebase Storage."""

from __future__ import annotations

import io
import re
import uuid
from pathlib import PurePosixPath
from urllib.parse import quote, unquote, urlparse

import httpx
from firebase_admin import storage
from PIL import Image, UnidentifiedImageError

from firebase_client import init_firebase
from firestore_spas import get_spa, update_spa

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HTTP_TIMEOUT = 30.0
WEBP_QUALITY = 85
STORAGE_PREFIX = "spas"


def _get_bucket():
    init_firebase()
    return storage.bucket()


def _storage_path(spa_id: str, filename: str) -> str:
    return f"{STORAGE_PREFIX}/{spa_id}/images/{filename}"


def _filename_for_url(url: str, index: int, used_names: set[str]) -> str:
    path = unquote(urlparse(url).path)
    stem = PurePosixPath(path).stem
    stem = re.sub(r"[^\w\-]+", "-", stem).strip("-").lower()
    if not stem:
        stem = f"image-{index + 1}"

    name = f"{stem}.webp"
    counter = 2
    while name in used_names:
        name = f"{stem}-{counter}.webp"
        counter += 1

    used_names.add(name)
    return name


def _download_image(url: str) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        content_type = (response.headers.get("content-type") or "").lower()
        if content_type.startswith("text/"):
            raise ValueError(f"URL returned HTML instead of an image ({content_type})")
        return response.content


def _convert_to_webp(image_bytes: bytes) -> bytes:
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            output = io.BytesIO()
            img.save(output, format="WEBP", quality=WEBP_QUALITY, method=6)
            return output.getvalue()
    except UnidentifiedImageError as e:
        raise ValueError("Unsupported or corrupt image data") from e


def _download_url(bucket_name: str, blob_path: str, token: str) -> str:
    encoded_path = quote(blob_path, safe="")
    return (
        f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}/o/"
        f"{encoded_path}?alt=media&token={token}"
    )


def _upload_webp(bucket, blob_path: str, webp_bytes: bytes) -> str:
    blob = bucket.blob(blob_path)
    token = str(uuid.uuid4())
    blob.metadata = {"firebaseStorageDownloadTokens": token}
    blob.upload_from_string(webp_bytes, content_type="image/webp")
    return _download_url(bucket.name, blob_path, token)


def _is_already_uploaded(url: str, spa_id: str) -> bool:
    if "firebasestorage.googleapis.com" not in url:
        return False
    encoded_prefix = quote(f"{STORAGE_PREFIX}/{spa_id}/images/", safe="")
    plain_prefix = f"{STORAGE_PREFIX}/{spa_id}/images/"
    return encoded_prefix in url or plain_prefix in url


def upload_spa_images(spa_id: str, source_urls: list[str]) -> dict:
    """Download images, convert to WebP, upload to Firebase Storage, update Firestore."""
    if not spa_id:
        raise ValueError("Spa ID is required")
    if not source_urls:
        raise ValueError("At least one image URL is required")

    spa = get_spa(spa_id)
    if not spa:
        raise ValueError("Spa not found")

    bucket = _get_bucket()
    used_names: set[str] = set()
    uploaded: list[dict] = []
    errors: list[dict] = []
    new_urls: list[str] = []

    for index, source_url in enumerate(source_urls):
        source_url = (source_url or "").strip()
        if not source_url:
            continue

        if _is_already_uploaded(source_url, spa_id):
            new_urls.append(source_url)
            continue

        filename = _filename_for_url(source_url, index, used_names)
        blob_path = _storage_path(spa_id, filename)

        try:
            raw_bytes = _download_image(source_url)
            webp_bytes = _convert_to_webp(raw_bytes)
            public_url = _upload_webp(bucket, blob_path, webp_bytes)
            uploaded.append(
                {
                    "source_url": source_url,
                    "filename": filename,
                    "storage_path": blob_path,
                    "public_url": public_url,
                }
            )
            new_urls.append(public_url)
        except Exception as e:
            errors.append({"source_url": source_url, "error": str(e)})
            new_urls.append(source_url)

    if not new_urls:
        raise ValueError("No valid image URLs to upload")

    spa_data = dict(spa["data"])
    spa_data["images"] = new_urls
    updated_spa = update_spa(spa_id, spa_data)

    return {
        "spa": updated_spa,
        "uploaded": uploaded,
        "errors": errors,
    }
