#!/usr/bin/env python3
"""Local web UI for the spa scraper."""

from flask import Flask, jsonify, render_template, request

from firebase_client import init_firebase
from firestore_spas import create_spa, get_spa, list_spas, update_spa
from scrape_spa import scrape_url

app = Flask(__name__)

init_firebase()


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
    """Confirm the app and Firebase connection are ready."""
    init_firebase()
    return jsonify({"status": "ok", "firebase": "connected"})


@app.get("/api/spas")
def api_list_spas():
    try:
        return jsonify({"spas": list_spas()})
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
    app.run(debug=True, port=5000)
