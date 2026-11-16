"""Crawl regions: the 26 Swiss cantons with their bounding boxes.

Bounding boxes come from OpenStreetMap (Nominatim). They are rectangles, so
they overlap neighbouring cantons; that is fine because every result is
deduplicated and assigned to its real canton from Google's address data.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Region:
    id: str
    name: str  # German name, as used on privatespa.com
    code: str  # official two-letter canton code
    south: float
    west: float
    north: float
    east: float


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

REGIONS_BY_ID = {r.id: r for r in CANTON_REGIONS}
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
