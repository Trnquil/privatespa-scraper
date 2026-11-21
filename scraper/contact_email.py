"""Find a spa's contact email on its website (no AI needed).

Looks at the given page first (mailto: links, Cloudflare-protected addresses,
addresses in the text, simple "info [at] spa.ch" obfuscation). If that finds
nothing on the spa's own domain, it follows the site's contact / legal-notice
pages (Kontakt, Impressum, Mentions légales, Contatti, …), where an email is
nearly always listed. Prefers addresses on the website's own domain.
"""

from __future__ import annotations

import re
from urllib.parse import unquote, urljoin, urlparse

from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}")
OBFUSCATED_RE = re.compile(
    r"([A-Za-z0-9._%+-]+)\s*(?:\[at\]|\(at\)|\{at\}|\s at\s|\[@\]|\(@\))\s*"
    r"([A-Za-z0-9-]+(?:\s*(?:\.|\[dot\]|\(dot\)|\s dot\s)\s*[A-Za-z0-9-]+)+)",
    re.I,
)
CONTACT_LINK_RE = re.compile(
    r"kontakt|contact|impressum|imprint|legal|mentions|contatt|note-legali|"
    r"anfahrt|about|ueber-uns|uber-uns|chi-siamo|qui-sommes|reserv|booking|buchen",
    re.I,
)
# Domains and local parts that are never the spa's own address.
JUNK_DOMAINS = (
    "example.", "sentry", "wixpress", "domain.", "email.", "yourdomain", "test.", "beispiel.",
    "godaddy", "jimdo", "squarespace", "wordpress", "w3.org", "schema.org", "googlemail.com.invalid",
)
JUNK_LOCAL = ("noreply", "no-reply", "donotreply", "webmaster", "postmaster", "abuse", "privacy",
              "datenschutz", "dsb", "gdpr", "rgpd", "dpo", "jobs", "career", "karriere", "bewerbung")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif")
# Rank of the local part: general addresses first, then spa/booking, then anything else.
GENERAL_LOCAL = ("info", "kontakt", "contact", "welcome", "hello", "hallo", "bonjour", "ciao", "office",
                 "mail", "hotel", "reservation", "reservierung", "reservations", "booking", "buchung",
                 "prenotazioni", "rezeption", "reception", "empfang")
SPA_LOCAL = ("spa", "wellness", "privatspa", "privat")
WEAK_LOCAL = ("development", "marketing", "press", "presse", "media", "hr", "personal", "events",
              "rechnung", "invoice", "billing", "buchhaltung", "accounting", "admin", "web", "it")


def _site_domain(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    parts = host.split(".")
    # keep e.g. "spa.co.uk"-style suffixes intact enough for matching
    return ".".join(parts[-3:]) if len(parts) > 2 and len(parts[-2]) <= 3 else ".".join(parts[-2:])


def _decode_cfemail(hexstr: str) -> str | None:
    try:
        key = int(hexstr[:2], 16)
        return "".join(chr(int(hexstr[i:i + 2], 16) ^ key) for i in range(2, len(hexstr), 2))
    except ValueError:
        return None


def _clean(email: str) -> str | None:
    e = unquote(email).strip().strip(".,;:()<>[]\"'").lower()
    e = e.split("?")[0]
    if not EMAIL_RE.fullmatch(e):
        return None
    local, _, domain = e.partition("@")
    if e.endswith(IMAGE_EXT) or any(j in domain for j in JUNK_DOMAINS):
        return None
    if any(local.startswith(j) for j in JUNK_LOCAL) or len(local) > 40:
        return None
    return e


def emails_in_html(html: str) -> list[str]:
    """All plausible email addresses in a page, in order of appearance."""
    soup = BeautifulSoup(html, "lxml")
    found: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().startswith("mailto:"):
            for part in href[7:].split(","):
                found.append(part)
        if "/cdn-cgi/l/email-protection#" in href:
            found.append(_decode_cfemail(href.split("#", 1)[1]) or "")
    for tag in soup.select("[data-cfemail]"):
        found.append(_decode_cfemail(tag["data-cfemail"]) or "")
    text = soup.get_text(" ", strip=True)
    found += EMAIL_RE.findall(text)
    for local, domain in OBFUSCATED_RE.findall(text):
        domain = re.sub(r"\s*(?:\[dot\]|\(dot\)|\s dot\s)\s*", ".", domain, flags=re.I).replace(" ", "")
        found.append(f"{local}@{domain}")
    out: list[str] = []
    for f in found:
        c = _clean(f or "")
        if c and c not in out:
            out.append(c)
    return out


def pick_best(emails: list[str], site_url: str) -> str | None:
    if not emails:
        return None
    domain = _site_domain(site_url)
    root = domain.split(".")[0]

    def score(e: str) -> tuple:
        local, _, edomain = e.partition("@")
        own = edomain == domain or edomain.endswith("." + domain)
        related = bool(root) and len(root) > 3 and root in edomain
        starts = lambda words: any(local == w or local.startswith(w) for w in words)  # noqa: E731
        rank = 3 if starts(GENERAL_LOCAL) else 2 if starts(SPA_LOCAL) else 0 if starts(WEAK_LOCAL) else 1
        return (own, related, rank)

    best = max(emails, key=lambda e: score(e))  # max keeps the first among equals
    # Only weak addresses (development@, marketing@, …): better no contact than a wrong one.
    return None if score(best)[2] == 0 else best


def _is_own(email: str, site_url: str) -> bool:
    """An address on the site's own domain that is a sensible contact (not e.g. development@)."""
    domain = _site_domain(site_url)
    local, _, edomain = email.partition("@")
    if any(local == w or local.startswith(w) for w in WEAK_LOCAL):
        return False
    return edomain == domain or edomain.endswith("." + domain)


def contact_links(html: str, url: str, limit: int = 4) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    host = (urlparse(url).hostname or "").removeprefix("www.")
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"]).split("#")[0]
        p = urlparse(href)
        if p.scheme not in ("http", "https") or (p.hostname or "").removeprefix("www.") != host:
            continue
        if CONTACT_LINK_RE.search(f"{a.get_text(' ', strip=True)} {p.path}") and href not in links:
            links.append(href)
    # contact/legal pages first, booking/about later
    links.sort(key=lambda h: 0 if re.search(r"kontakt|contact|impressum|imprint|mentions|legal|contatt", h, re.I) else 1)
    return links[:limit]


def find_contact_email(url: str, html: str | None = None, fetch=None) -> str | None:
    """Best contact email for the site at `url`. `fetch(url) -> html` is used for extra pages."""
    if fetch is None:
        from scrape_spa import fetch_with_httpx as fetch
    pages_seen: set[str] = set()
    emails: list[str] = []

    def visit(page_url: str, page_html: str | None = None) -> str | None:
        if page_url in pages_seen:
            return page_html
        pages_seen.add(page_url)
        if page_html is None:
            try:
                page_html = fetch(page_url)
            except Exception:  # noqa: BLE001 - a missing page just means no email there
                return None
        for e in emails_in_html(page_html):
            if e not in emails:
                emails.append(e)
        return page_html

    first = visit(url, html)
    if any(_is_own(e, url) for e in emails):
        return pick_best(emails, url)
    # A subpage (e.g. /private-spa) may lack the footer links: also look at the home page.
    home = f"{urlparse(url).scheme}://{urlparse(url).netloc}/"
    candidates = contact_links(first, url) if first else []
    if home.rstrip("/") != url.rstrip("/"):
        home_html = visit(home)
        if home_html:
            candidates += [l for l in contact_links(home_html, home) if l not in candidates]
    for link in candidates[:4]:
        if any(_is_own(e, url) for e in emails):
            break
        visit(link)
    if not emails:
        # Sites built in the browser show nothing to a plain request: try a real browser once.
        try:
            from scrape_spa import fetch_with_playwright

            pages_seen.discard(home)
            rendered = fetch_with_playwright(home)
            visit(home, rendered)
            for link in contact_links(rendered, home)[:2]:
                if emails:
                    break
                try:
                    visit(link, fetch_with_playwright(link))
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            pass
    return pick_best(emails, url)
