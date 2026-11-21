"""Italian regions and French régions/départements for crawling and region matching.

Spas are filed under the German region name (like all other countries).
Italy is crawled per region; France per département (96, metropolitan),
because its 13 régions are too large for Google's top-20 results per search,
while each spa is still filed under its région.
"""

from __future__ import annotations

import unicodedata

# (stored German name, other names Google or the AI may return)
IT_REGIONS: list[tuple[str, list[str]]] = [
    ("Abruzzen", ["Abruzzo", "Abruzzi"]),
    ("Basilikata", ["Basilicata"]),
    ("Kalabrien", ["Calabria"]),
    ("Kampanien", ["Campania"]),
    ("Emilia-Romagna", ["Emilia Romagna"]),
    ("Friaul-Julisch Venetien", ["Friuli-Venezia Giulia", "Friuli Venezia Giulia", "Friuli"]),
    ("Latium", ["Lazio"]),
    ("Ligurien", ["Liguria"]),
    ("Lombardei", ["Lombardia", "Lombardy"]),
    ("Marken", ["Marche", "The Marches"]),
    ("Molise", []),
    ("Piemont", ["Piemonte", "Piedmont"]),
    ("Apulien", ["Puglia", "Apulia"]),
    ("Sardinien", ["Sardegna", "Sardinia"]),
    ("Sizilien", ["Sicilia", "Sicily"]),
    ("Toskana", ["Toscana", "Tuscany"]),
    ("Trentino-Südtirol", ["Trentino-Alto Adige", "Trentino-Alto Adige/Südtirol", "Trentino-South Tyrol",
                           "Südtirol", "Alto Adige", "South Tyrol", "Trentino", "Bolzano", "Trento"]),
    ("Umbrien", ["Umbria"]),
    ("Aostatal", ["Valle d'Aosta", "Vallée d'Aoste", "Aosta Valley", "Aosta"]),
    ("Venetien", ["Veneto"]),
]

FR_REGIONS: list[tuple[str, list[str]]] = [
    ("Auvergne-Rhône-Alpes", ["Auvergne Rhône-Alpes", "ARA"]),
    ("Bourgogne-Franche-Comté", ["Burgund-Franche-Comté", "BFC"]),
    ("Bretagne", ["Brittany"]),
    ("Centre-Val de Loire", ["Centre", "CVL"]),
    ("Korsika", ["Corse", "Corsica"]),
    ("Grand Est", ["GES"]),
    ("Hauts-de-France", ["HDF"]),
    ("Île-de-France", ["Ile-de-France", "IDF"]),
    ("Normandie", ["Normandy"]),
    ("Nouvelle-Aquitaine", ["NAQ"]),
    ("Okzitanien", ["Occitanie", "Occitania"]),
    ("Pays de la Loire", ["PDL"]),
    ("Provence-Alpes-Côte d'Azur", ["Provence-Alpes-Côte d’Azur", "PACA", "Provence", "Côte d'Azur"]),
]

# (code, département, région as stored)
FR_DEPARTEMENTS: list[tuple[str, str, str]] = [
    ("01", "Ain", "Auvergne-Rhône-Alpes"), ("02", "Aisne", "Hauts-de-France"), ("03", "Allier", "Auvergne-Rhône-Alpes"),
    ("04", "Alpes-de-Haute-Provence", "Provence-Alpes-Côte d'Azur"), ("05", "Hautes-Alpes", "Provence-Alpes-Côte d'Azur"),
    ("06", "Alpes-Maritimes", "Provence-Alpes-Côte d'Azur"), ("07", "Ardèche", "Auvergne-Rhône-Alpes"),
    ("08", "Ardennes", "Grand Est"), ("09", "Ariège", "Okzitanien"), ("10", "Aube", "Grand Est"), ("11", "Aude", "Okzitanien"),
    ("12", "Aveyron", "Okzitanien"), ("13", "Bouches-du-Rhône", "Provence-Alpes-Côte d'Azur"), ("14", "Calvados", "Normandie"),
    ("15", "Cantal", "Auvergne-Rhône-Alpes"), ("16", "Charente", "Nouvelle-Aquitaine"), ("17", "Charente-Maritime", "Nouvelle-Aquitaine"),
    ("18", "Cher", "Centre-Val de Loire"), ("19", "Corrèze", "Nouvelle-Aquitaine"), ("2A", "Corse-du-Sud", "Korsika"),
    ("2B", "Haute-Corse", "Korsika"), ("21", "Côte-d'Or", "Bourgogne-Franche-Comté"), ("22", "Côtes-d'Armor", "Bretagne"),
    ("23", "Creuse", "Nouvelle-Aquitaine"), ("24", "Dordogne", "Nouvelle-Aquitaine"), ("25", "Doubs", "Bourgogne-Franche-Comté"),
    ("26", "Drôme", "Auvergne-Rhône-Alpes"), ("27", "Eure", "Normandie"), ("28", "Eure-et-Loir", "Centre-Val de Loire"),
    ("29", "Finistère", "Bretagne"), ("30", "Gard", "Okzitanien"), ("31", "Haute-Garonne", "Okzitanien"), ("32", "Gers", "Okzitanien"),
    ("33", "Gironde", "Nouvelle-Aquitaine"), ("34", "Hérault", "Okzitanien"), ("35", "Ille-et-Vilaine", "Bretagne"),
    ("36", "Indre", "Centre-Val de Loire"), ("37", "Indre-et-Loire", "Centre-Val de Loire"), ("38", "Isère", "Auvergne-Rhône-Alpes"),
    ("39", "Jura", "Bourgogne-Franche-Comté"), ("40", "Landes", "Nouvelle-Aquitaine"), ("41", "Loir-et-Cher", "Centre-Val de Loire"),
    ("42", "Loire", "Auvergne-Rhône-Alpes"), ("43", "Haute-Loire", "Auvergne-Rhône-Alpes"), ("44", "Loire-Atlantique", "Pays de la Loire"),
    ("45", "Loiret", "Centre-Val de Loire"), ("46", "Lot", "Okzitanien"), ("47", "Lot-et-Garonne", "Nouvelle-Aquitaine"),
    ("48", "Lozère", "Okzitanien"), ("49", "Maine-et-Loire", "Pays de la Loire"), ("50", "Manche", "Normandie"),
    ("51", "Marne", "Grand Est"), ("52", "Haute-Marne", "Grand Est"), ("53", "Mayenne", "Pays de la Loire"),
    ("54", "Meurthe-et-Moselle", "Grand Est"), ("55", "Meuse", "Grand Est"), ("56", "Morbihan", "Bretagne"),
    ("57", "Moselle", "Grand Est"), ("58", "Nièvre", "Bourgogne-Franche-Comté"), ("59", "Nord", "Hauts-de-France"),
    ("60", "Oise", "Hauts-de-France"), ("61", "Orne", "Normandie"), ("62", "Pas-de-Calais", "Hauts-de-France"),
    ("63", "Puy-de-Dôme", "Auvergne-Rhône-Alpes"), ("64", "Pyrénées-Atlantiques", "Nouvelle-Aquitaine"),
    ("65", "Hautes-Pyrénées", "Okzitanien"), ("66", "Pyrénées-Orientales", "Okzitanien"), ("67", "Bas-Rhin", "Grand Est"),
    ("68", "Haut-Rhin", "Grand Est"), ("69", "Rhône", "Auvergne-Rhône-Alpes"), ("70", "Haute-Saône", "Bourgogne-Franche-Comté"),
    ("71", "Saône-et-Loire", "Bourgogne-Franche-Comté"), ("72", "Sarthe", "Pays de la Loire"), ("73", "Savoie", "Auvergne-Rhône-Alpes"),
    ("74", "Haute-Savoie", "Auvergne-Rhône-Alpes"), ("75", "Paris", "Île-de-France"), ("76", "Seine-Maritime", "Normandie"),
    ("77", "Seine-et-Marne", "Île-de-France"), ("78", "Yvelines", "Île-de-France"), ("79", "Deux-Sèvres", "Nouvelle-Aquitaine"),
    ("80", "Somme", "Hauts-de-France"), ("81", "Tarn", "Okzitanien"), ("82", "Tarn-et-Garonne", "Okzitanien"),
    ("83", "Var", "Provence-Alpes-Côte d'Azur"), ("84", "Vaucluse", "Provence-Alpes-Côte d'Azur"), ("85", "Vendée", "Pays de la Loire"),
    ("86", "Vienne", "Nouvelle-Aquitaine"), ("87", "Haute-Vienne", "Nouvelle-Aquitaine"), ("88", "Vosges", "Grand Est"),
    ("89", "Yonne", "Bourgogne-Franche-Comté"), ("90", "Territoire de Belfort", "Bourgogne-Franche-Comté"),
    ("91", "Essonne", "Île-de-France"), ("92", "Hauts-de-Seine", "Île-de-France"), ("93", "Seine-Saint-Denis", "Île-de-France"),
    ("94", "Val-de-Marne", "Île-de-France"), ("95", "Val-d'Oise", "Île-de-France"),
]


def _key(text: str) -> str:
    """Accent-, case-, apostrophe- and dash-insensitive form for matching."""
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    for ch in "'’`-_/":
        t = t.replace(ch, " ")
    return " ".join(t.split())


_LOOKUP: dict[str, dict[str, str]] = {"IT": {}, "FR": {}}
for _country, _table in (("IT", IT_REGIONS), ("FR", FR_REGIONS)):
    for _name, _aliases in _table:
        for _alias in [_name, *_aliases]:
            _LOOKUP[_country][_key(_alias)] = _name
# A French département name also identifies its région.
for _code, _dep, _region in FR_DEPARTEMENTS:
    _LOOKUP["FR"].setdefault(_key(_dep), _region)
    _LOOKUP["FR"].setdefault(_key(_code), _region)


def normalize_it_fr(country: str, value: str) -> str | None:
    table = _LOOKUP.get(country.upper())
    if not table or not value:
        return None
    key = _key(value).removeprefix("regione ").removeprefix("region ").removeprefix("region of ")
    if key in table:
        return table[key]
    # e.g. "Trentino-Alto Adige/Südtirol" or "Région Île-de-France"
    for alias, name in table.items():
        if len(alias) > 3 and (alias in key or key in alias):
            return name
    return None
