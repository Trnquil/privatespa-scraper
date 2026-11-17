#!/usr/bin/env python3
"""Local web UI for the spa scraper."""

import threading
from datetime import datetime

import httpx
from flask import Flask, jsonify, render_template, request

import crawl_db
from regions import REGIONS_BY_ID
from crawler import crawl_next, crawl_region

from firebase_client import init_firebase
from firestore_spas import (
    DRAFT,
    PUBLISHED,
    create_spa,
    delete_spa,
    get_db,
    get_spa,
    list_spas,
    update_spa,
)
from image_info import get_image_info
from rescrape import rescrape_missing_fields
from scrape_spa import scrape_url
from storage_images import (
    generate_all_spa_thumbnails,
    generate_spa_thumbnail,
    upload_spa_images,
)

app = Flask(__name__)

# State of the background crawl job (one at a time).
_crawl_job: dict = {"running": False, "region": None, "log": [], "summary": None, "error": None}
_crawl_job_lock = threading.Lock()


def _log(message: str) -> None:
    _crawl_job["log"].append(f"{datetime.now():%H:%M:%S}  {message}")
    del _crawl_job["log"][:-200]


def _run_crawl(region_id: str | None) -> None:
    try:
        if region_id:
            _crawl_job["summary"] = crawl_region(region_id, progress=_log)
        else:
            _crawl_job["summary"] = crawl_next(progress=_log)
    except Exception as e:
        _crawl_job["error"] = str(e)
        _log(f"Error: {e}")
    finally:
        _crawl_job["running"] = False


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/regions")
def regions_page():
    return render_template("regions.html")


@app.get("/api/regions")
def api_regions():
    crawl_db.init_db()
    regions = crawl_db.list_regions()
    for r in regions:
        r["country"] = REGIONS_BY_ID[r["id"]].country if r["id"] in REGIONS_BY_ID else "CH"
    return jsonify({"regions": regions, "job": _crawl_job})


@app.get("/api/regions/<region_id>/candidates")
def api_region_candidates(region_id):
    crawl_db.init_db()
    return jsonify({"candidates": crawl_db.list_candidates(region_id)})


@app.post("/api/crawl")
def api_start_crawl():
    """Start a crawl in the background: {"region": "zh"} or {} for the next todo region."""
    body = request.get_json(silent=True) or {}
    region_id = (body.get("region") or "").strip() or None
    crawl_db.init_db()
    if region_id and not crawl_db.get_region(region_id):
        return jsonify({"error": f"Unknown region: {region_id}"}), 400
    if not region_id and not crawl_db.next_region():
        return jsonify({"error": "All regions are done"}), 400

    with _crawl_job_lock:
        if _crawl_job["running"]:
            return jsonify({"error": "A crawl is already running"}), 409
        _crawl_job.update(running=True, region=region_id, log=[], summary=None, error=None)
        threading.Thread(target=_run_crawl, args=(region_id,), daemon=True).start()
    return jsonify({"started": True, "job": _crawl_job}), 202


@app.post("/api/regions/<region_id>/reset")
def api_reset_region(region_id):
    crawl_db.init_db()
    if not crawl_db.get_region(region_id):
        return jsonify({"error": "Unknown region"}), 404
    crawl_db.reset_region(region_id)
    return jsonify({"ok": True})


@app.post("/api/regions/<region_id>/priority")
def api_region_priority(region_id):
    body = request.get_json(silent=True) or {}
    try:
        crawl_db.set_priority(region_id, int(body.get("priority", 0)))
    except (TypeError, ValueError):
        return jsonify({"error": "priority must be a number"}), 400
    return jsonify({"ok": True})


@app.post("/api/spas/<spa_id>/publish")
def api_publish_spa(spa_id):
    """Make a draft live: copy its images to Firebase Storage, make a thumbnail, set status."""
    spa = get_spa(spa_id)
    if not spa:
        return jsonify({"error": "Spa not found"}), 404
    data = spa["data"]
    if not (data.get("name") and data.get("slug")):
        return jsonify({"error": "Name and slug are required before publishing"}), 400

    images = data.get("images") or []
    if not images:
        return jsonify({"error": "Add at least one image before publishing"}), 400

    errors = []
    external = [u for u in images if "firebasestorage" not in u]
    if external:
        result = upload_spa_images(spa_id, images)
        errors = result.get("errors") or []
        if errors:
            return jsonify(
                {"error": "Some images could not be copied; remove them and try again", "errors": errors}
            ), 502
        spa = result.get("spa") or get_spa(spa_id)
        images = spa["data"].get("images") or []

    if not spa["data"].get("thumbnail"):
        generate_spa_thumbnail(spa_id, images[0])

    updated = update_spa(spa_id, {"status": PUBLISHED})
    crawl_db.init_db()
    crawl_db.mark_spa_reviewed(spa_id, crawl_db.ACCEPTED)
    return jsonify(updated)


@app.post("/api/spas/<spa_id>/reject")
def api_reject_draft(spa_id):
    """Reject a draft: delete it (and any uploaded images). Only drafts can be rejected."""
    spa = get_spa(spa_id)
    if not spa:
        return jsonify({"error": "Spa not found"}), 404
    if spa["data"].get("status") != DRAFT:
        return jsonify({"error": "Only drafts can be rejected; use Delete listing for published spas"}), 400
    result = delete_spa(spa_id)
    crawl_db.init_db()
    crawl_db.mark_spa_reviewed(spa_id, crawl_db.REJECTED, note="Rejected in review")
    return jsonify(result)


@app.post("/api/spas/<spa_id>/unpublish")
def api_unpublish_spa(spa_id):
    if not get_spa(spa_id):
        return jsonify({"error": "Spa not found"}), 404
    return jsonify(update_spa(spa_id, {"status": DRAFT}))


@app.get("/spa/<spa_id>")
def edit_spa_page(spa_id):
    return render_template(
        "edit.html",
        editor_config={"mode": "firestore", "spaId": spa_id},
    )


@app.get("/scrape/edit")
def edit_scrape_page():
    return render_template(
        "edit.html",
        editor_config={"mode": "scrape", "spaId": None},
    )


@app.get("/api/health")
def health():
    """Confirm the app can read from Firestore."""
    try:
        init_firebase()
        get_db().collection("spas").limit(1).get()
        return jsonify({"status": "ok", "firebase": "connected"})
    except Exception as e:
        return jsonify({"status": "error", "firebase": str(e)}), 503


@app.get("/api/spas")
def api_list_spas():
    try:
        return jsonify({"spas": list_spas()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/api/spas/generate-all-thumbnails")
def api_generate_all_spa_thumbnails():
    try:
        result = generate_all_spa_thumbnails()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/spas/<spa_id>")
def api_get_spa(spa_id):
    try:
        spa = get_spa(spa_id)
        if not spa:
            return jsonify({"error": "Spa not found"}), 404
        return jsonify(spa)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/api/spas")
def api_create_spa():
    body = request.get_json(silent=True) or {}
    data = body.get("data")
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must include a data object"}), 400

    try:
        spa = create_spa(data)
        return jsonify(spa), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.put("/api/spas/<spa_id>")
def api_update_spa(spa_id):
    body = request.get_json(silent=True) or {}
    data = body.get("data")
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must include a data object"}), 400

    try:
        spa = update_spa(spa_id, data)
        return jsonify(spa)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/image-info")
def api_image_info():
    url = (request.args.get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        return jsonify(get_image_info(url))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except httpx.HTTPError as e:
        return jsonify({"error": f"Failed to fetch image: {e}"}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.delete("/api/spas/<spa_id>")
def api_delete_spa(spa_id):
    body = request.get_json(silent=True) or {}
    confirm = (body.get("confirm") or "").strip()
    if confirm != "DELETE":
        return jsonify({"error": 'Type DELETE to confirm deletion'}), 400

    try:
        result = delete_spa(spa_id)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/api/spas/<spa_id>/rescrape-missing")
def api_rescrape_missing_fields(spa_id):
    body = request.get_json(silent=True) or {}
    data = body.get("data")
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must include a data object"}), 400

    spa = get_spa(spa_id)
    if not spa:
        return jsonify({"error": "Spa not found"}), 404

    try:
        result = rescrape_missing_fields(data)
        return jsonify(
            {
                **result,
                "spa": {"id": spa_id, "data": result["data"]},
            }
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except EnvironmentError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/api/spas/<spa_id>/generate-thumbnail")
def api_generate_spa_thumbnail(spa_id):
    body = request.get_json(silent=True) or {}
    source_url = (body.get("url") or "").strip()
    if not source_url:
        return jsonify({"error": "Request body must include a url"}), 400

    try:
        result = generate_spa_thumbnail(spa_id, source_url)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/api/spas/<spa_id>/upload-images")
def api_upload_spa_images(spa_id):
    body = request.get_json(silent=True) or {}
    urls = body.get("urls")
    if not isinstance(urls, list):
        return jsonify({"error": "Request body must include a urls array"}), 400

    try:
        result = upload_spa_images(spa_id, urls)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/api/scrape")
def api_scrape():
    body = request.get_json(silent=True) or {}
    url = (body.get("url") or "").strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        result = scrape_url(url)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except EnvironmentError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", "5001"))
    init_firebase()
    # Firestore uses gRPC; Flask's debug reloader forks after init and can deadlock.
    use_reloader = os.environ.get("FLASK_USE_RELOADER", "").lower() in {"1", "true", "yes"}
    # FLASK_DEBUG=0 when running as a service (the debugger allows running code).
    debug = os.environ.get("FLASK_DEBUG", "1").lower() in {"1", "true", "yes"}
    app.run(debug=debug, host="127.0.0.1", port=port, use_reloader=use_reloader and debug)
