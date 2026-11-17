"""Local crawl tracking in SQLite (crawl.db, next to this file, gitignored).

Tracks which regions have been crawled and every place Google returned, so a
region is never searched twice by accident and every candidate's outcome
(draft created, duplicate, no website, failed, …) can be reviewed later.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from regions import REGIONS

DB_PATH = Path(os.environ.get("CRAWL_DB_PATH", Path(__file__).resolve().parent / "crawl.db"))

# Region statuses
TODO, RUNNING, DONE, FAILED = "todo", "running", "done", "failed"

# Candidate statuses
DRAFT_CREATED = "draft_created"  # scraped and saved to Firestore as a draft
DUPLICATE = "duplicate"          # already in Firestore (same place or website)
NO_WEBSITE = "no_website"        # Google has no website for it; add by hand if relevant
SKIPPED = "skipped"              # outside Switzerland or permanently closed
FAILED_SCRAPE = "failed"         # website could not be scraped
NOT_PRIVATE = "not_private"      # the AI judged it is not a private spa (e.g. regular hotel spa)
REJECTED = "rejected"            # draft was rejected in review; never re-added
ACCEPTED = "accepted"            # draft was accepted and published

SCHEMA = """
CREATE TABLE IF NOT EXISTS regions (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'todo',
    priority      INTEGER NOT NULL DEFAULT 0,
    last_crawled  TEXT,
    results       INTEGER,
    drafts        INTEGER,
    saturated     INTEGER NOT NULL DEFAULT 0,
    error         TEXT
);
CREATE TABLE IF NOT EXISTS candidates (
    place_id      TEXT PRIMARY KEY,
    region_id     TEXT NOT NULL REFERENCES regions(id),
    name          TEXT,
    website       TEXT,
    address       TEXT,
    canton        TEXT,
    lat           REAL,
    lng           REAL,
    status        TEXT NOT NULL,
    spa_id        TEXT,
    note          TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS candidates_region ON candidates(region_id);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables and make sure every canton has a row (new ones start as todo)."""
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT OR IGNORE INTO regions (id, name) VALUES (?, ?)",
            [(r.id, r.name) for r in REGIONS],
        )
        # A crash mid-crawl leaves a region 'running'; make it retryable.
        conn.execute("UPDATE regions SET status = ? WHERE status = ?", (TODO, RUNNING))


def list_regions() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT r.id, r.name, r.status, r.priority, r.last_crawled, r.results,
                   r.saturated, r.error,
                   (SELECT COUNT(*) FROM candidates c WHERE c.region_id = r.id) AS candidates,
                   (SELECT COUNT(*) FROM candidates c
                     WHERE c.region_id = r.id
                       AND c.status IN ('draft_created', 'accepted', 'rejected')) AS drafts,
                   (SELECT COUNT(*) FROM candidates c
                     WHERE c.region_id = r.id AND c.status = 'draft_created') AS to_review
            FROM regions r
            ORDER BY CASE r.status WHEN 'running' THEN 0 WHEN 'todo' THEN 1
                                   WHEN 'failed' THEN 2 ELSE 3 END,
                     r.priority DESC, r.name
            """
        ).fetchall()
    return [dict(r) for r in rows]


def get_region(region_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM regions WHERE id = ?", (region_id,)).fetchone()
    return dict(row) if row else None


def next_region() -> dict | None:
    """The next region to crawl: highest priority todo region, then alphabetical."""
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM regions WHERE status = ? ORDER BY priority DESC, name LIMIT 1",
            (TODO,),
        ).fetchone()
    return dict(row) if row else None


def set_region_status(region_id: str, status: str, **fields) -> None:
    columns = {"status": status, **fields}
    assignments = ", ".join(f"{k} = ?" for k in columns)
    with connect() as conn:
        conn.execute(
            f"UPDATE regions SET {assignments} WHERE id = ?",
            (*columns.values(), region_id),
        )


def set_priority(region_id: str, priority: int) -> None:
    with connect() as conn:
        conn.execute("UPDATE regions SET priority = ? WHERE id = ?", (priority, region_id))


def reset_region(region_id: str) -> None:
    """Mark a region as todo again (its candidates are kept, so nothing is re-added)."""
    set_region_status(region_id, TODO, error=None)


def known_place_ids() -> set[str]:
    """Places already handled. Failed scrapes are left out so the next crawl retries them."""
    with connect() as conn:
        return {
            r[0]
            for r in conn.execute("SELECT place_id FROM candidates WHERE status != ?", (FAILED_SCRAPE,))
        }


def upsert_candidate(place: dict, region_id: str, status: str, spa_id: str | None = None, note: str | None = None) -> None:
    ts = now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO candidates (place_id, region_id, name, website, address, canton, lat, lng,
                                    status, spa_id, note, created_at, updated_at)
            VALUES (:place_id, :region_id, :name, :website, :address, :canton, :lat, :lng,
                    :status, :spa_id, :note, :ts, :ts)
            ON CONFLICT(place_id) DO UPDATE SET
                status = excluded.status, spa_id = excluded.spa_id, note = excluded.note,
                website = excluded.website, updated_at = excluded.updated_at
            """,
            {
                "place_id": place["place_id"],
                "region_id": region_id,
                "name": place.get("name"),
                "website": place.get("website"),
                "address": place.get("address"),
                "canton": place.get("canton"),
                "lat": place.get("lat"),
                "lng": place.get("lng"),
                "status": status,
                "spa_id": spa_id,
                "note": note,
                "ts": ts,
            },
        )


def list_candidates(region_id: str | None = None) -> list[dict]:
    with connect() as conn:
        if region_id:
            rows = conn.execute(
                "SELECT * FROM candidates WHERE region_id = ? ORDER BY status, name", (region_id,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM candidates ORDER BY region_id, status, name").fetchall()
    return [dict(r) for r in rows]


def mark_spa_reviewed(spa_id: str, status: str, note: str | None = None) -> None:
    """Record the review outcome of a crawled draft (by its Firestore id)."""
    with connect() as conn:
        conn.execute(
            "UPDATE candidates SET status = ?, note = COALESCE(?, note), updated_at = ? WHERE spa_id = ?",
            (status, note, now(), spa_id),
        )
