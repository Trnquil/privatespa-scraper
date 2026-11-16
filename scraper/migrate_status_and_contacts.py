#!/usr/bin/env python3
"""One-time migration before using the crawler.

1. Sets status = "published" on every spa that has no status yet, so existing
   spas stay visible once the website only shows published spas.
2. Moves the `contact` email from the public `spas/{id}` document to the
   admin-only `spa_private/{id}` document, then deletes it from `spas`.

Dry run by default; pass --apply to write.

    python migrate_status_and_contacts.py           # show what would change
    python migrate_status_and_contacts.py --apply   # do it
"""

from __future__ import annotations

import sys

from dotenv import load_dotenv
from firebase_admin import firestore

from firestore_spas import PRIVATE_COLLECTION, PUBLISHED, get_db

load_dotenv()


def main(apply: bool) -> None:
    db = get_db()
    status_updates = 0
    contacts_moved = 0
    batch = db.batch()
    pending = 0

    for doc in db.collection("spas").stream():
        data = doc.to_dict() or {}
        update: dict = {}
        if data.get("status") not in ("draft", PUBLISHED):
            update["status"] = PUBLISHED
            status_updates += 1
        if "contact" in data:
            contact = (data.get("contact") or "").strip()
            if contact:
                batch.set(db.collection(PRIVATE_COLLECTION).document(doc.id), {"contact": contact}, merge=True)
                contacts_moved += 1
            update["contact"] = firestore.DELETE_FIELD
        if update:
            batch.update(doc.reference, update)
            pending += 1
        if pending >= 200:
            if apply:
                batch.commit()
            batch, pending = db.batch(), 0

    if apply and pending:
        batch.commit()

    verb = "Updated" if apply else "Would update"
    print(f"{verb}: {status_updates} spas get status=published, {contacts_moved} contacts moved to {PRIVATE_COLLECTION}.")
    if not apply:
        print("Dry run only. Run again with --apply to write.")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
