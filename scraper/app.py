#!/usr/bin/env python3
"""Local web UI for the spa scraper."""

from flask import Flask, jsonify, render_template, request

from scrape_spa import scrape_url

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html")


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
