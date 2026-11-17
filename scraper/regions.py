"""Crawl regions: the 26 Swiss cantons, 16 German and 9 Austrian states, with bounding boxes.

Bounding boxes come from OpenStreetMap (Nominatim). They are rectangles, so
they overlap neighbouring cantons; that is fine because every result is
deduplicated and assigned to its real canton from Google's address data.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Region:
    id: str
    name: str  # German name, as used on privatespa.com (stored in the spa's `canton` field)
    code: str  # official region code (ZH, BY, Tirol…), as Google reports it
    south: float
    west: float
    north: float
    east: float
    country: str = "CH"


CANTON_REGIONS: list[Region] = [
    Region("zh", "Zürich", "ZH", south=47.1594, west=8.3577, north=47.6945, east=8.985),
    Region("be", "Bern", "BE", south=46.3265, west=6.8615, north=47.3453, east=8.4552),
    Region("lu", "Luzern", "LU", south=46.775, west=7.8364, north=47.2872, east=8.5141),
    Region("ur", "Uri", "UR", south=46.5276, west=8.3974, north=46.9934, east=8.9578),
    Region("sz", "Schwyz", "SZ", south=46.8853, west=8.3888, north=47.2226, east=9.0047),
    Region("ow", "Obwalden", "OW", south=46.7532, west=8.0422, north=46.9804, east=8.5069),
    Region("nw", "Nidwalden", "NW", south=46.7715, west=8.2181, north=47.02, east=8.575),
    Region("gl", "Glarus", "GL", south=46.7965, west=8.8712, north=47.174, east=9.2526),
    Region("zg", "Zug", "ZG", south=47.081, west=8.3948, north=47.2484, east=8.7012),
    Region("fr", "Freiburg", "FR", south=46.4379, west=6.7419, north=47.0068, east=7.3802),
    Region("so", "Solothurn", "SO", south=47.0743, west=7.3404, north=47.5027, east=8.0314),
    Region("bs", "Basel-Stadt", "BS", south=47.5193, west=7.5547, north=47.6009, east=7.6938),
    Region("bl", "Basel-Landschaft", "BL", south=47.3379, west=7.3252, north=47.5644, east=7.9618),
    Region("sh", "Schaffhausen", "SH", south=47.5524, west=8.4046, north=47.8085, east=8.8762),
    Region("ar", "Appenzell Ausserrhoden", "AR", south=47.247, west=9.1911, north=47.469, east=9.631),
    Region("ai", "Appenzell Innerrhoden", "AI", south=47.234, west=9.3097, north=47.4437, east=9.6184),
    Region("sg", "St. Gallen", "SG", south=46.8729, west=8.7956, north=47.5497, east=9.6741),
    Region("gr", "Graubünden", "GR", south=46.1691, west=8.6511, north=47.0651, east=10.4922),
    Region("ag", "Aargau", "AG", south=47.1375, west=7.7135, north=47.6211, east=8.4551),
    Region("tg", "Thurgau", "TG", south=47.3759, west=8.668, north=47.6954, east=9.5069),
    Region("ti", "Tessin", "TI", south=45.818, west=8.3822, north=46.6325, east=9.1597),
    Region("vd", "Waadt", "VD", south=46.1871, west=6.0639, north=46.9869, east=7.2492),
    Region("vs", "Wallis", "VS", south=45.8582, west=6.7706, north=46.654, east=8.4785),
    Region("ne", "Neuenburg", "NE", south=46.8466, west=6.4327, north=47.1657, east=7.0877),
    Region("ge", "Genf", "GE", south=46.1286, west=5.9559, north=46.3646, east=6.3103),
    Region("ju", "Jura", "JU", south=47.1504, west=6.8407, north=47.5045, east=7.5583),
]

# German and Austrian federal states
STATE_REGIONS: list[Region] = [
    Region("de-bw", "Baden-Württemberg", "BW", south=47.5324, west=7.5117, north=49.7913, east=10.4956, country="DE"),
    Region("de-by", "Bayern", "BY", south=47.2701, west=8.9764, north=50.5647, east=13.8396, country="DE"),
    Region("de-be", "Berlin", "BE", south=52.3382, west=13.0883, north=52.6755, east=13.7612, country="DE"),
    Region("de-bb", "Brandenburg", "BB", south=51.359, west=11.2658, north=53.5591, east=14.7658, country="DE"),
    Region("de-hb", "Bremen", "HB", south=53.0112, west=8.4816, north=53.6102, east=8.9908, country="DE"),
    Region("de-hh", "Hamburg", "HH", south=53.3951, west=8.1045, north=54.0277, east=10.3253, country="DE"),
    Region("de-he", "Hessen", "HE", south=49.3953, west=7.7725, north=51.6578, east=10.2364, country="DE"),
    Region("de-mv", "Mecklenburg-Vorpommern", "MV", south=53.1104, west=10.5936, north=54.885, east=14.4122, country="DE"),
    Region("de-ni", "Niedersachsen", "NI", south=51.2951, west=6.3459, north=54.1378, east=11.5983, country="DE"),
    Region("de-nw", "Nordrhein-Westfalen", "NW", south=50.3227, west=5.8663, north=52.5315, east=9.4617, country="DE"),
    Region("de-rp", "Rheinland-Pfalz", "RP", south=48.9664, west=6.1123, north=50.9423, east=8.5083, country="DE"),
    Region("de-sl", "Saarland", "SL", south=49.112, west=6.3558, north=49.6394, east=7.4048, country="DE"),
    Region("de-sn", "Sachsen", "SN", south=50.1713, west=11.8715, north=51.685, east=15.0419, country="DE"),
    Region("de-st", "Sachsen-Anhalt", "ST", south=50.9378, west=10.5608, north=53.0418, east=13.1868, country="DE"),
    Region("de-sh", "Schleswig-Holstein", "SH", south=53.3598, west=7.5212, north=55.0992, east=11.6724, country="DE"),
    Region("de-th", "Thüringen", "TH", south=50.2043, west=9.877, north=51.6493, east=12.6539, country="DE"),
    Region("at-b", "Burgenland", "Burgenland", south=46.8306, west=15.9962, north=48.1187, east=17.1608, country="AT"),
    Region("at-k", "Kärnten", "Kärnten", south=46.3723, west=12.6568, north=47.1313, east=15.0652, country="AT"),
    Region("at-n", "Niederösterreich", "Niederösterreich", south=47.4222, west=14.4526, north=49.0205, east=17.0688, country="AT"),
    Region("at-o", "Oberösterreich", "Oberösterreich", south=47.4611, west=12.7492, north=48.7726, east=14.9922, country="AT"),
    Region("at-s", "Salzburg", "Salzburg", south=46.9439, west=12.0761, north=48.0415, east=13.9961, country="AT"),
    Region("at-st", "Steiermark", "Steiermark", south=46.612, west=13.5633, north=47.8279, east=16.1718, country="AT"),
    Region("at-t", "Tirol", "Tirol", south=46.6514, west=10.0978, north=47.743, east=12.966, country="AT"),
    Region("at-v", "Vorarlberg", "Vorarlberg", south=46.8409, west=9.5307, north=47.5961, east=10.2372, country="AT"),
    Region("at-w", "Wien", "Wien", south=48.1179, west=16.1818, north=48.3227, east=16.5775, country="AT"),
]

REGIONS: list[Region] = CANTON_REGIONS + STATE_REGIONS
REGIONS_BY_ID = {r.id: r for r in REGIONS}
COUNTRY_NAMES = {"CH": "Schweiz", "DE": "Deutschland", "AT": "Österreich"}
CANTON_NAME_BY_CODE = {r.code: r.name for r in CANTON_REGIONS}

# Names the AI or Google may return, mapped to the German name the site uses.
_CANTON_ALIASES = {
    "zurich": "Zürich", "zuerich": "Zürich",
    "berne": "Bern",
    "lucerne": "Luzern", "lucerna": "Luzern",
    "fribourg": "Freiburg",
    "soleure": "Solothurn",
    "bale-ville": "Basel-Stadt", "basel-city": "Basel-Stadt", "basel stadt": "Basel-Stadt",
    "bale-campagne": "Basel-Landschaft", "basel-country": "Basel-Landschaft", "basel land": "Basel-Landschaft", "baselland": "Basel-Landschaft",
    "schaffhouse": "Schaffhausen",
    "appenzell outer rhodes": "Appenzell Ausserrhoden",
    "appenzell inner rhodes": "Appenzell Innerrhoden",
    "saint-gall": "St. Gallen", "st gallen": "St. Gallen", "sankt gallen": "St. Gallen", "st. gall": "St. Gallen",
    "grisons": "Graubünden", "grigioni": "Graubünden", "grischun": "Graubünden", "graubuenden": "Graubünden",
    "argovie": "Aargau",
    "thurgovie": "Thurgau",
    "ticino": "Tessin",
    "vaud": "Waadt",
    "valais": "Wallis",
    "neuchatel": "Neuenburg", "neuchâtel": "Neuenburg",
    "geneva": "Genf", "geneve": "Genf", "genève": "Genf", "ginevra": "Genf",
}

# English and alternative names of German and Austrian states.
_STATE_ALIASES = {
    "DE": {
        "bavaria": "Bayern", "free state of bavaria": "Bayern", "freistaat bayern": "Bayern",
        "hesse": "Hessen", "lower saxony": "Niedersachsen", "north rhine-westphalia": "Nordrhein-Westfalen",
        "nrw": "Nordrhein-Westfalen", "rhineland-palatinate": "Rheinland-Pfalz", "saxony": "Sachsen",
        "freistaat sachsen": "Sachsen", "saxony-anhalt": "Sachsen-Anhalt", "thuringia": "Thüringen",
        "freistaat thüringen": "Thüringen", "thueringen": "Thüringen", "mecklenburg-western pomerania": "Mecklenburg-Vorpommern",
        "baden-wuerttemberg": "Baden-Württemberg", "baden-wurttemberg": "Baden-Württemberg",
        "freie hansestadt bremen": "Bremen", "freie und hansestadt hamburg": "Hamburg",
    },
    "AT": {
        "carinthia": "Kärnten", "kaernten": "Kärnten", "lower austria": "Niederösterreich",
        "niederoesterreich": "Niederösterreich", "upper austria": "Oberösterreich",
        "oberoesterreich": "Oberösterreich", "styria": "Steiermark", "tyrol": "Tirol", "vienna": "Wien",
    },
}


def normalize_region(country: str | None, value: str | None) -> str | None:
    """Map a region name or code (any language) to the site's German name, within one country.

    Codes are only unique per country ("BE" is Bern in CH but Berlin in DE).
    Without a country, Swiss cantons are tried first (backwards compatible).
    """
    if not value:
        return None
    country = (country or "CH").upper()
    if country == "CH":
        return normalize_canton(value)
    text = str(value).strip()
    key = text.lower().removeprefix("bundesland ").removeprefix("land ").strip()
    for r in STATE_REGIONS:
        if r.country != country:
            continue
        if r.code.lower() == key or r.name.lower() == key:
            return r.name
    return _STATE_ALIASES.get(country, {}).get(key)


def normalize_canton(value: str | None) -> str | None:
    """Map a canton name or code in any language to the site's German name."""
    if not value:
        return None
    text = str(value).strip()
    if text.upper() in CANTON_NAME_BY_CODE:
        return CANTON_NAME_BY_CODE[text.upper()]
    key = text.lower().removeprefix("kanton ").removeprefix("canton de ").removeprefix("canton du ").removeprefix("canton ").removeprefix("cantone ").strip()
    for region in CANTON_REGIONS:
        if region.name.lower() == key:
            return region.name
    return _CANTON_ALIASES.get(key)
