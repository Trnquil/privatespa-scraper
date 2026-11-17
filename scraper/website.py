"""Tell privatespa.com to refresh its cached spa data after a change.

Needs WEBSITE_URL (default https://www.privatespa.com) and
WEBSITE_REVALIDATE_SECRET in .env; the same secret must be set as
REVALIDATE_SECRET in the website's Vercel project. Without it the website
picks up changes within the hour on its own.
"""

from __future__ import annotations

import logging
import os
import threading

import httpx

log = logging.getLogger(__name__)


def _post() -> None:
    secret = os.environ.get("WEBSITE_REVALIDATE_SECRET")
    if not secret:
        return
    url = os.environ.get("WEBSITE_URL", "https://www.privatespa.com").rstrip("/") + "/api/revalidate"
    try:
        r = httpx.post(url, headers={"Authorization": f"Bearer {secret}"}, timeout=15)
        if r.status_code != 200:
            log.warning("Website refresh failed: %s %s", r.status_code, r.text[:200])
    except httpx.HTTPError as e:
        log.warning("Website refresh failed: %s", e)


def refresh_website() -> None:
    """Fire-and-forget refresh, so the editor never waits on the website."""
    threading.Thread(target=_post, daemon=True).start()
