#!/usr/bin/env python3
"""Crawl Swiss cantons and German/Austrian states for private spas; save new ones as drafts.

For one region:
  1. Search Google Places with the country's phrases (places_search.COUNTRY_QUERIES,
     e.g. "spa privatif" in France), top 20 results each.
  2. Skip places already seen, already in Firestore (same Google place or same
     website), outside CH/DE/AT, permanently closed, or without a website.
  3. Scrape each remaining website with the existing scraper (OpenAI extraction).
  4. Save it to Firestore with status "draft", so it does not appear on the
     website until you publish it in the editor.

Everything is recorded in crawl.db (see crawl_db.py).

CLI:
  python crawler.py status            show all regions
  python crawler.py next              crawl the next todo region
  python crawler.py run <region-id>   crawl a specific region (e.g. zh, de-by, at-t)
  python crawler.py reset <region-id> mark a region as todo again
  python crawler.py priority <region-id> <n>   higher runs first
  python crawler.py candidates [<region-id>]   list what was found
"""

from __future__ import annotations

import sys
import threading
from typing import Callable

from dotenv import load_dotenv

import crawl_db as db
from firestore_spas import DRAFT, create_spa, existing_spa_index, normalize_website
from places_search import search_queries, search_region
from regions import COUNTRY_NAMES, REGIONS_BY_ID, normalize_region
from scrape_spa import extract_slug_from_url, find_spa_links, normalize_slug, scrape_url

load_dotenv()

ProgressFn = Callable[[str], None]

# Only one crawl at a time (the web UI and the CLI share crawl.db).
_crawl_lock = threading.Lock()


def _unique_slug(base: str | None, taken: set[str]) -> str | None:
    if not base:
        return None
    slug, n = base, 2
    while slug in taken:
        slug = f"{base}-{n}"
        n += 1
    taken.add(slug)
    return slug


def _build_draft(place: dict, scraped: dict, taken_slugs: set[str]) -> dict:
    """Combine Google's place data (reliable location) with the scraped profile."""
    data = dict(scraped)
    data["name"] = data.get("name") or place.get("name")
    data["location"] = data.get("location") or place.get("address")
    # Google's canton and coordinates come from its address data and beat the AI's guess.
    country = place.get("country") if place.get("country") in COUNTRY_NAMES else data.get("country")
    data["country"] = country or "CH"
    # Google's region and coordinates come from its address data and beat the AI's guess.
    data["canton"] = (
        place.get("canton") or normalize_region(data["country"], data.get("canton")) or data.get("canton")
    )
    if place.get("lat") is not None and place.get("lng") is not None:
        data["coordinates"] = [place["lat"], place["lng"]]
    base_slug = (
        data.get("slug")
        or extract_slug_from_url(place.get("website") or "")
        or normalize_slug(data.get("name") or "")
    )
    data["slug"] = _unique_slug(base_slug, taken_slugs)
    data["status"] = DRAFT
    data["google_place_id"] = place["place_id"]
    data["source"] = "crawler"
    data["premium"] = False
    return data


def crawl_region(region_id: str, progress: ProgressFn = print) -> dict:
    """Crawl one region. Returns a summary dict."""
    region = REGIONS_BY_ID.get(region_id)
    if not region:
        raise ValueError(f"Unknown region: {region_id}")
    if not _crawl_lock.acquire(blocking=False):
        raise RuntimeError("Another crawl is already running")

    try:
        db.init_db()
        db.set_region_status(region.id, db.RUNNING, error=None)
        progress(f"Searching {region.name}…")

        # 1. Discover
        places: dict[str, dict] = {}
        saturated = False
        for query in search_queries(region.country):
            found, capped = search_region(region, query)
            saturated = saturated or capped
            for p in found:
                if p.get("place_id"):
                    places.setdefault(p["place_id"], p)
            progress(f"“{query}”: {len(found)} results")

        # 2. Deduplicate
        index = existing_spa_index()
        seen = db.known_place_ids()
        counts = {
            k: 0
            for k in (db.DRAFT_CREATED, db.NOT_PRIVATE, db.DUPLICATE, db.NO_WEBSITE, db.SKIPPED, db.FAILED_SCRAPE)
        }
        already_seen = 0
        queue: list[dict] = []

        for place in places.values():
            pid = place["place_id"]
            if pid in seen:
                already_seen += 1  # found in an earlier crawl, outcome already recorded
                continue
            if place.get("country") and place["country"] not in COUNTRY_NAMES:
                db.upsert_candidate(place, region.id, db.SKIPPED, note=f"Outside CH/DE/AT ({place['country']})")
                counts[db.SKIPPED] += 1
                continue
            if place.get("business_status") == "CLOSED_PERMANENTLY":
                db.upsert_candidate(place, region.id, db.SKIPPED, note="Permanently closed")
                counts[db.SKIPPED] += 1
                continue
            if pid in index["place_ids"]:
                db.upsert_candidate(place, region.id, db.DUPLICATE, note="Same Google place already in Firestore")
                counts[db.DUPLICATE] += 1
                continue
            site = normalize_website(place.get("website"))
            if not site:
                db.upsert_candidate(place, region.id, db.NO_WEBSITE)
                counts[db.NO_WEBSITE] += 1
                continue
            domain = site.split("/", 1)[0]
            if domain in index["domains"]:
                existing_id = index["domains"][domain]
                if existing_id is None:  # another result in this crawl has the same website
                    db.upsert_candidate(place, region.id, db.DUPLICATE, note="Same domain as another result in this crawl")
                else:
                    db.upsert_candidate(
                        place, region.id, db.DUPLICATE,
                        spa_id=existing_id, note="Same domain already in Firestore",
                    )
                counts[db.DUPLICATE] += 1
                continue
            index["domains"][domain] = None  # two places on one domain: scrape once
            queue.append(place)

        # 3 + 4. Scrape and save drafts
        for i, place in enumerate(queue, 1):
            progress(f"Scraping {i}/{len(queue)}: {place.get('name')} ({place['website']})")
            try:
                result = scrape_url(place["website"])
                if not result.get("is_private_spa"):
                    # Hotels often describe their private spa on a subpage.
                    for link in find_spa_links(place["website"]):
                        progress(f"  checking subpage {link}")
                        sub = scrape_url(link)
                        if sub.get("is_private_spa"):
                            result = sub
                            break
                if not result.get("is_private_spa"):
                    db.upsert_candidate(
                        place, region.id, db.NOT_PRIVATE,
                        note=result.get("private_spa_reason") or "Not a private spa",
                    )
                    counts[db.NOT_PRIVATE] += 1
                    continue
                draft = _build_draft(place, result["data"], index["slugs"])
                if result.get("private_spa_evidence"):
                    progress(f"  private spa: “{str(result['private_spa_evidence'])[:120]}”")
                spa = create_spa(draft)
                db.upsert_candidate(place, region.id, db.DRAFT_CREATED, spa_id=spa["id"])
                counts[db.DRAFT_CREATED] += 1
            except Exception as e:  # one bad website must not stop the crawl
                db.upsert_candidate(place, region.id, db.FAILED_SCRAPE, note=str(e)[:500])
                counts[db.FAILED_SCRAPE] += 1

        db.set_region_status(
            region.id,
            db.DONE,
            last_crawled=db.now(),
            results=len(places),
            drafts=counts[db.DRAFT_CREATED],
            saturated=int(saturated),
        )
        summary = {
            "region": region.id,
            "name": region.name,
            "results": len(places),
            "already_seen": already_seen,
            "saturated": saturated,
            **counts,
        }
        progress(
            f"Done: {counts[db.DRAFT_CREATED]} new drafts, {counts[db.NOT_PRIVATE]} not private spas, "
            f"{counts[db.DUPLICATE]} duplicates, "
            f"{counts[db.NO_WEBSITE]} without website, {counts[db.FAILED_SCRAPE]} failed"
            + (" — Google had more than 20 results for some phrases" if saturated else "")
        )
        return summary
    except Exception as e:
        db.set_region_status(region.id, db.FAILED, error=str(e)[:500])
        raise
    finally:
        _crawl_lock.release()


def crawl_next(progress: ProgressFn = print) -> dict | None:
    db.init_db()
    region = db.next_region()
    if not region:
        progress("All regions are done.")
        return None
    return crawl_region(region["id"], progress)


def _print_status() -> None:
    db.init_db()
    print(f"{'id':<6} {'region':<24} {'status':<8} {'last crawl':<20} {'found':>5} {'drafts':>6}")
    for r in db.list_regions():
        flag = "  ⚠ 60-cap" if r["saturated"] else ""
        print(
            f"{r['id']:<6} {r['name']:<24} {r['status']:<8} {(r['last_crawled'] or '-')[:16]:<20} "
            f"{r['results'] if r['results'] is not None else '-':>5} {r['drafts'] if r['drafts'] is not None else '-':>6}{flag}"
        )


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "status"
    if cmd == "status":
        _print_status()
    elif cmd == "next":
        crawl_next()
    elif cmd == "run" and len(argv) == 3:
        crawl_region(argv[2])
    elif cmd == "reset" and len(argv) == 3:
        db.init_db()
        db.reset_region(argv[2])
        print(f"{argv[2]} is todo again")
    elif cmd == "priority" and len(argv) == 4:
        db.init_db()
        db.set_priority(argv[2], int(argv[3]))
    elif cmd == "candidates":
        db.init_db()
        for c in db.list_candidates(argv[2] if len(argv) > 2 else None):
            print(f"{c['region_id']:<4} {c['status']:<14} {c['name'] or '-':<40} {c['website'] or '-'}  {c['note'] or ''}")
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
