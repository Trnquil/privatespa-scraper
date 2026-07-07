#!/usr/bin/env python3
"""Local web UI for the spa scraper."""

import httpx
from flask import Flask, jsonify, render_template, request

from firebase_client import init_firebase
from firestore_spas import create_spa, delete_spa, get_db, get_spa, list_spas, update_spa
from image_info import get_image_info
from rescrape import rescrape_missing_fields
from scrape_spa import scrape_url
from storage_images import (
    generate_all_spa_thumbnails,
    generate_spa_thumbnail,
    upload_spa_images,
)

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html")


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
    app.run(debug=True, host="127.0.0.1", port=port, use_reloader=use_reloader)
