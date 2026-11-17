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
GOOGLE_MAPS_API_KEY=your_google_maps_key_here
```

`OPENAI_MODEL` is optional and defaults to `gpt-4o-mini` if not set.

`GOOGLE_MAPS_API_KEY` is used after scraping to geocode the extracted location into latitude/longitude.

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

When editing a spa, use **Save to Firebase** to persist changes. New scraped spas are also saved to Firebase on first save.

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
6. Geocodes the extracted **location** with **Google Maps** when coordinates are not already on the page

## Crawling regions (finding new spas automatically)

The crawler searches Google for "private spa" one region at a time (26 Swiss
cantons, 16 German and 9 Austrian federal states; ids like `zh`, `de-by`,
`at-t`), skips spas
you already have, scrapes the rest with the scraper above, and saves them to
Firestore as **drafts**. Drafts are not shown on privatespa.com until you
publish them.

### One-time setup

1. In Google Cloud, enable **Places API (New)** for `GOOGLE_MAPS_API_KEY`.
2. Run the migration once. It marks existing spas as published and moves
   contact emails to the admin-only `spa_private` collection:
   ```bash
   python migrate_status_and_contacts.py          # dry run
   python migrate_status_and_contacts.py --apply
   ```
3. Paste `firestore.rules` into Firebase console → Firestore → Rules, so
   nobody outside this tool can read contact emails. Check it against your
   current rules first.

### Using it

In the web UI, open **Regions** (`/regions`):

- **Crawl next region** crawls the highest-priority canton still marked *todo*.
- Click a canton to see every place Google returned and what happened to it:
  new draft, already listed, no website, skipped (outside CH or closed), or
  scrape failed.
- **Priority:** higher numbers are crawled first.
- **Mark todo** queues a canton again. Places already handled are not
  re-added; failed scrapes are retried.
- ⚠ next to a region means Google returned its maximum of 60 results, so
  some spas may be missing. Large German states (Bayern, NRW, BW) will likely
  hit this; splitting them into districts is the fix if it matters.
- Websites can be German or English; the AI always writes the description and
  amenities in both languages, and the country and region come from Google.

Then go through the **Drafts** filter on the home page, fix anything the AI
got wrong, remove bad images, and click **Publish**. Publishing copies the
images to Firebase Storage, creates the thumbnail and sets the spa live.

Or from the command line:

```bash
python crawler.py status        # all cantons and their state
python crawler.py next          # crawl the next one
python crawler.py run zh        # crawl a specific canton
python crawler.py candidates zh # what was found in Zürich
python crawler.py reset zh      # mark Zürich todo again
```

Tracking lives in `crawl.db` (SQLite, next to this file, not committed).
Back it up if you move machines.

Optional `.env` settings:

```
CRAWL_QUERIES=private spa            # comma-separated search phrases
CRAWL_DB_PATH=/path/to/crawl.db
```

### Running on a server

The UI has no login and can delete spas, so never expose its port. Keep it
bound to `127.0.0.1` and connect through an SSH tunnel:

```bash
ssh -L 5001:localhost:5001 user@server   # then open http://localhost:5001
```
