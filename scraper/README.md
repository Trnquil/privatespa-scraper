# PrivateSpa Scraper (Local MVP)

A simple local Python script that fetches a spa website and extracts structured information using OpenAI.

## Setup

### 1. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate    # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Playwright Chromium

```bash
playwright install chromium
```

### 4. Configure environment variables

Create a `.env` file in the `scraper` directory:

```
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

`OPENAI_MODEL` is optional and defaults to `gpt-4o-mini` if not set.

### 5. Firebase (Admin SDK)

Place your service account JSON in the `scraper` directory (default):

```
privatespa-com-firebase-adminsdk-fbsvc-9d4b4739cd.json
```

Or set a custom path:

```
FIREBASE_CREDENTIALS_PATH=/path/to/serviceAccountKey.json
```

The web app initializes Firebase on startup and reads/writes the `spas` Firestore collection.

Verify the connection:

```bash
curl http://127.0.0.1:5000/api/health
curl http://127.0.0.1:5000/api/spas
```

## Usage

### CLI

```bash
python scrape_spa.py "https://example-spa.com"
```

### Web UI

Start the local frontend:

```bash
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000):

- **Existing spas** — click a spa to open its edit page at `/spa/<id>`
- **Scrape new spa** — after scraping, opens `/scrape/edit` in a new page

When editing a Firestore spa, use **Save to Firestore** to persist changes.

## Example output

```json
{
  "data": {
    "amenities": ["Sauna", "Massage", "Private rooms"],
    "canton": "Zürich",
    "coordinates": [47.3769, 8.5417],
    "description": "A polished description based only on the website text.",
    "images": [
      "https://example-spa.com/images/room-1.jpg",
      "https://example-spa.com/images/room-2.jpg"
    ],
    "location": "Example Spa, Zürich, Switzerland",
    "name": "Example Spa",
    "website": "https://example-spa.com"
  },
  "source_url": "https://example-spa.com",
  "used_playwright": false,
  "raw_text_preview": "..."
}
```

## How it works

1. Validates the URL (scheme, host, blocks localhost/private IPs)
2. Fetches the page with **httpx** (browser-like User-Agent, 15s timeout)
3. Parses HTML with **BeautifulSoup** + **lxml**, strips nav/footer/scripts, extracts visible text
4. If text is under 500 characters, retries with **Playwright** (headless Chromium)
5. Sends up to ~10,000 characters of text to the **OpenAI API** for structured extraction
