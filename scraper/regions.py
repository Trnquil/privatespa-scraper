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

# Italy: one crawl unit per region (name = the German region name spas are filed under).
# France: one crawl unit per département; spas are filed under their région
# (from Google's address data), so the unit name shows both.
IT_FR_REGIONS: list[Region] = [
    Region("it-abruzzo", "Abruzzen", "Abruzzo", south=41.682, west=13.019, north=42.8951, east=14.7839, country="IT"),
    Region("it-basilicata", "Basilikata", "Basilicata", south=39.8958, west=15.335, north=41.1395, east=16.867, country="IT"),
    Region("it-calabria", "Kalabrien", "Calabria", south=37.9158, west=15.6298, north=40.1449, east=17.2064, country="IT"),
    Region("it-campania", "Kampanien", "Campania", south=39.9905, west=13.7624, north=41.5081, east=15.8064, country="IT"),
    Region("it-emilia-romagna", "Emilia-Romagna", "Emilia-Romagna", south=43.7308, west=9.1979, north=45.1395, east=12.7559, country="IT"),
    Region("it-friuli-venezia-giulia", "Friaul-Julisch Venetien", "Friuli-Venezia Giulia", south=45.5809, west=12.3214, north=46.648, east=13.9187, country="IT"),
    Region("it-lazio", "Latium", "Lazio", south=40.7849, west=11.4492, north=42.8387, east=14.0276, country="IT"),
    Region("it-liguria", "Ligurien", "Liguria", south=43.7757, west=7.4952, north=44.6764, east=10.0715, country="IT"),
    Region("it-lombardia", "Lombardei", "Lombardia", south=44.6799, west=8.4979, north=46.6354, east=11.4276, country="IT"),
    Region("it-marche", "Marken", "Marche", south=42.6872, west=12.1855, north=43.9716, east=13.9163, country="IT"),
    Region("it-molise", "Molise", "Molise", south=41.3641, west=13.9411, north=42.0703, east=15.1617, country="IT"),
    Region("it-piemonte", "Piemont", "Piemonte", south=44.0597, west=6.6273, north=46.4643, east=9.2142, country="IT"),
    Region("it-puglia", "Apulien", "Puglia", south=39.7896, west=14.9342, north=42.2265, east=18.5205, country="IT"),
    Region("it-sardegna", "Sardinien", "Sardegna", south=38.8591, west=8.1308, north=41.3131, east=9.8293, country="IT"),
    Region("it-sicilia", "Sizilien", "Sicilia", south=35.493, west=11.9259, north=38.8177, east=15.6531, country="IT"),
    Region("it-toscana", "Toskana", "Toscana", south=42.2376, west=9.6868, north=44.4725, east=12.3723, country="IT"),
    Region("it-trentino-alto-adige", "Trentino-Südtirol", "Trentino-Alto Adige", south=45.6729, west=10.3818, north=47.0921, east=12.478, country="IT"),
    Region("it-umbria", "Umbrien", "Umbria", south=42.3648, west=11.892, north=43.6173, east=13.2642, country="IT"),
    Region("it-valle-d-aosta", "Aostatal", "Valle d'Aosta", south=45.467, west=6.8015, north=45.9877, east=7.9395, country="IT"),
    Region("it-veneto", "Venetien", "Veneto", south=44.7923, west=10.6231, north=46.6806, east=13.1021, country="IT"),
    Region("fr-01", "Ain (Auvergne-Rhône-Alpes)", "01", south=45.6109, west=4.7279, north=46.5199, east=6.1701, country="FR"),
    Region("fr-02", "Aisne (Hauts-de-France)", "02", south=48.8372, west=2.958, north=50.0694, east=4.2557, country="FR"),
    Region("fr-03", "Allier (Auvergne-Rhône-Alpes)", "03", south=45.9307, west=2.2768, north=46.8042, east=4.0056, country="FR"),
    Region("fr-04", "Alpes-de-Haute-Provence (Provence-Alpes-Côte d'Azur)", "04", south=43.6682, west=5.4964, north=44.6599, east=6.9691, country="FR"),
    Region("fr-05", "Hautes-Alpes (Provence-Alpes-Côte d'Azur)", "05", south=44.1864, west=5.4184, north=45.1266, east=7.0771, country="FR"),
    Region("fr-06", "Alpes-Maritimes (Provence-Alpes-Côte d'Azur)", "06", south=43.4801, west=6.6352, north=44.3625, east=7.719, country="FR"),
    Region("fr-07", "Ardèche (Auvergne-Rhône-Alpes)", "07", south=44.2643, west=3.8611, north=45.3662, east=4.8862, country="FR"),
    Region("fr-08", "Ardennes (Grand Est)", "08", south=49.2269, west=4.0246, north=50.1693, east=5.3941, country="FR"),
    Region("fr-09", "Ariège (Okzitanien)", "09", south=42.5732, west=0.8268, north=43.3163, east=2.1758, country="FR"),
    Region("fr-10", "Aube (Grand Est)", "10", south=47.9235, west=3.3836, north=48.7167, east=4.8651, country="FR"),
    Region("fr-11", "Aude (Okzitanien)", "11", south=42.6486, west=1.6887, north=43.46, east=3.2404, country="FR"),
    Region("fr-12", "Aveyron (Okzitanien)", "12", south=43.6907, west=1.8397, north=44.9412, east=3.452, country="FR"),
    Region("fr-13", "Bouches-du-Rhône (Provence-Alpes-Côte d'Azur)", "13", south=43.1574, west=4.2301, north=43.9246, east=5.8135, country="FR"),
    Region("fr-14", "Calvados (Normandie)", "14", south=48.7517, west=-1.1598, north=49.4299, east=0.4466, country="FR"),
    Region("fr-15", "Cantal (Auvergne-Rhône-Alpes)", "15", south=44.6159, west=2.0629, north=45.4836, east=3.3713, country="FR"),
    Region("fr-16", "Charente (Nouvelle-Aquitaine)", "16", south=45.1925, west=-0.4631, north=46.1409, east=0.947, country="FR"),
    Region("fr-17", "Charente-Maritime (Nouvelle-Aquitaine)", "17", south=45.089, west=-1.5627, north=46.3715, east=0.006, country="FR"),
    Region("fr-18", "Cher (Centre-Val de Loire)", "18", south=46.4205, west=1.7739, north=47.6291, east=3.0792, country="FR"),
    Region("fr-19", "Corrèze (Nouvelle-Aquitaine)", "19", south=44.9205, west=1.227, north=45.7653, east=2.5287, country="FR"),
    Region("fr-2a", "Corse-du-Sud (Korsika)", "2A", south=41.3332, west=8.5347, north=42.3823, east=9.408, country="FR"),
    Region("fr-2b", "Haute-Corse (Korsika)", "2B", south=41.8322, west=8.5743, north=43.0277, east=9.56, country="FR"),
    Region("fr-21", "Côte-d'Or (Bourgogne-Franche-Comté)", "21", south=46.8999, west=4.0654, north=48.0312, east=5.5189, country="FR"),
    Region("fr-22", "Côtes-d'Armor (Bretagne)", "22", south=48.0324, west=-3.6659, north=49.1133, east=-1.9091, country="FR"),
    Region("fr-23", "Creuse (Nouvelle-Aquitaine)", "23", south=45.6634, west=1.3725, north=46.4553, east=2.6115, country="FR"),
    Region("fr-24", "Dordogne (Nouvelle-Aquitaine)", "24", south=44.571, west=-0.0419, north=45.7148, east=1.4481, country="FR"),
    Region("fr-25", "Doubs (Bourgogne-Franche-Comté)", "25", south=46.554, west=5.6988, north=47.58, east=7.0624, country="FR"),
    Region("fr-26", "Drôme (Auvergne-Rhône-Alpes)", "26", south=44.1152, west=4.6469, north=45.344, east=5.8303, country="FR"),
    Region("fr-27", "Eure (Normandie)", "27", south=48.6664, west=0.2962, north=49.4848, east=1.8029, country="FR"),
    Region("fr-28", "Eure-et-Loir (Centre-Val de Loire)", "28", south=47.954, west=0.7557, north=48.941, east=1.9945, country="FR"),
    Region("fr-29", "Finistère (Bretagne)", "29", south=47.7013, west=-5.144, north=48.7572, east=-3.3867, country="FR"),
    Region("fr-30", "Gard (Okzitanien)", "30", south=43.4602, west=3.2619, north=44.4597, east=4.8455, country="FR"),
    Region("fr-31", "Haute-Garonne (Okzitanien)", "31", south=42.6892, west=0.4419, north=43.9216, east=2.0483, country="FR"),
    Region("fr-32", "Gers (Okzitanien)", "32", south=43.3108, west=-0.2824, north=44.08, east=1.2033, country="FR"),
    Region("fr-33", "Gironde (Nouvelle-Aquitaine)", "33", south=44.1939, west=-1.265, north=45.6019, east=0.3146, country="FR"),
    Region("fr-34", "Hérault (Okzitanien)", "34", south=43.2102, west=2.5396, north=43.9728, east=4.1946, country="FR"),
    Region("fr-35", "Ille-et-Vilaine (Bretagne)", "35", south=47.6314, west=-2.289, north=48.722, east=-1.0157, country="FR"),
    Region("fr-36", "Indre (Centre-Val de Loire)", "36", south=46.3472, west=0.8671, north=47.2773, east=2.2045, country="FR"),
    Region("fr-37", "Indre-et-Loire (Centre-Val de Loire)", "37", south=46.7367, west=0.0528, north=47.7098, east=1.3659, country="FR"),
    Region("fr-38", "Isère (Auvergne-Rhône-Alpes)", "38", south=44.6959, west=4.7416, north=45.8836, east=6.3591, country="FR"),
    Region("fr-39", "Jura (Bourgogne-Franche-Comté)", "39", south=46.261, west=5.252, north=47.3058, east=6.2074, country="FR"),
    Region("fr-40", "Landes (Nouvelle-Aquitaine)", "40", south=43.4875, west=-1.5237, north=44.5324, east=0.1366, country="FR"),
    Region("fr-41", "Loir-et-Cher (Centre-Val de Loire)", "41", south=47.1862, west=0.5806, north=48.1334, east=2.248, country="FR"),
    Region("fr-42", "Loire (Auvergne-Rhône-Alpes)", "42", south=45.2311, west=3.6884, north=46.2765, east=4.7608, country="FR"),
    Region("fr-43", "Haute-Loire (Auvergne-Rhône-Alpes)", "43", south=44.7438, west=3.0821, north=45.4276, east=4.4905, country="FR"),
    Region("fr-44", "Loire-Atlantique (Pays de la Loire)", "44", south=46.8603, west=-2.6282, north=47.8359, east=-0.9467, country="FR"),
    Region("fr-45", "Loiret (Centre-Val de Loire)", "45", south=47.4831, west=1.5122, north=48.345, east=3.1286, country="FR"),
    Region("fr-46", "Lot (Okzitanien)", "46", south=44.2033, west=0.9812, north=45.0466, east=2.2113, country="FR"),
    Region("fr-47", "Lot-et-Garonne (Nouvelle-Aquitaine)", "47", south=43.9727, west=-0.1406, north=44.7657, east=1.0785, country="FR"),
    Region("fr-48", "Lozère (Okzitanien)", "48", south=44.1093, west=2.9823, north=44.9758, east=3.9984, country="FR"),
    Region("fr-49", "Maine-et-Loire (Pays de la Loire)", "49", south=46.9689, west=-1.3542, north=47.8097, east=0.2344, country="FR"),
    Region("fr-50", "Manche (Normandie)", "50", south=48.4558, west=-1.9551, north=49.728, east=-0.7348, country="FR"),
    Region("fr-51", "Marne (Grand Est)", "51", south=48.5153, west=3.3959, north=49.4074, east=5.0401, country="FR"),
    Region("fr-52", "Haute-Marne (Grand Est)", "52", south=47.5767, west=4.6275, north=48.6892, east=5.891, country="FR"),
    Region("fr-53", "Mayenne (Pays de la Loire)", "53", south=47.7338, west=-1.2389, north=48.5683, east=-0.049, country="FR"),
    Region("fr-54", "Meurthe-et-Moselle (Grand Est)", "54", south=48.3489, west=5.4261, north=49.5633, east=7.1232, country="FR"),
    Region("fr-55", "Meuse (Grand Est)", "55", south=48.4091, west=4.8885, north=49.6169, east=5.8542, country="FR"),
    Region("fr-56", "Morbihan (Bretagne)", "56", south=47.2778, west=-3.7351, north=48.2108, east=-2.0354, country="FR"),
    Region("fr-57", "Moselle (Grand Est)", "57", south=48.5266, west=5.8918, north=49.5149, east=7.6388, country="FR"),
    Region("fr-58", "Nièvre (Bourgogne-Franche-Comté)", "58", south=46.651, west=2.8445, north=47.5883, east=4.2318, country="FR"),
    Region("fr-59", "Nord (Hauts-de-France)", "59", south=49.9689, west=2.0798, north=51.089, east=4.2312, country="FR"),
    Region("fr-60", "Oise (Hauts-de-France)", "60", south=49.0605, west=1.6889, north=49.7637, east=3.1658, country="FR"),
    Region("fr-61", "Orne (Normandie)", "61", south=48.1794, west=-0.8606, north=48.9727, east=0.9766, country="FR"),
    Region("fr-62", "Pas-de-Calais (Hauts-de-France)", "62", south=50.0199, west=1.5556, north=51.0088, east=3.1882, country="FR"),
    Region("fr-63", "Puy-de-Dôme (Auvergne-Rhône-Alpes)", "63", south=45.2871, west=2.388, north=46.2563, east=3.9856, country="FR"),
    Region("fr-64", "Pyrénées-Atlantiques (Nouvelle-Aquitaine)", "64", south=42.7775, west=-1.791, north=43.5968, east=0.0303, country="FR"),
    Region("fr-65", "Hautes-Pyrénées (Okzitanien)", "65", south=42.6742, west=-0.3273, north=43.6134, east=0.6461, country="FR"),
    Region("fr-66", "Pyrénées-Orientales (Okzitanien)", "66", south=42.3328, west=1.7214, north=42.9186, east=3.1779, country="FR"),
    Region("fr-67", "Bas-Rhin (Grand Est)", "67", south=48.1203, west=6.9406, north=49.0778, east=8.2326, country="FR"),
    Region("fr-68", "Haut-Rhin (Grand Est)", "68", south=47.4203, west=6.8413, north=48.3113, east=7.622, country="FR"),
    Region("fr-69", "Rhône (Auvergne-Rhône-Alpes)", "69", south=45.454, west=4.2436, north=46.3065, east=5.1603, country="FR"),
    Region("fr-70", "Haute-Saône (Bourgogne-Franche-Comté)", "70", south=47.2526, west=5.367, north=48.0241, east=6.8255, country="FR"),
    Region("fr-71", "Saône-et-Loire (Bourgogne-Franche-Comté)", "71", south=46.156, west=3.6223, north=47.1554, east=5.4654, country="FR"),
    Region("fr-72", "Sarthe (Pays de la Loire)", "72", south=47.5684, west=-0.4481, north=48.485, east=0.9166, country="FR"),
    Region("fr-73", "Savoie (Auvergne-Rhône-Alpes)", "73", south=45.0516, west=5.6218, north=45.9383, east=7.1859, country="FR"),
    Region("fr-74", "Haute-Savoie (Auvergne-Rhône-Alpes)", "74", south=45.6817, west=5.8051, north=46.4564, east=7.0445, country="FR"),
    Region("fr-75", "Paris (Île-de-France)", "75", south=48.8156, west=2.2241, north=48.9022, east=2.4698, country="FR"),
    Region("fr-76", "Seine-Maritime (Normandie)", "76", south=49.2507, west=0.0658, north=50.0722, east=1.7908, country="FR"),
    Region("fr-77", "Seine-et-Marne (Île-de-France)", "77", south=48.1201, west=2.3923, north=49.1179, east=3.5592, country="FR"),
    Region("fr-78", "Yvelines (Île-de-France)", "78", south=48.4386, west=1.4462, north=49.0854, east=2.2292, country="FR"),
    Region("fr-79", "Deux-Sèvres (Nouvelle-Aquitaine)", "79", south=45.9697, west=-0.9035, north=47.1084, east=0.2204, country="FR"),
    Region("fr-80", "Somme (Hauts-de-France)", "80", south=49.5718, west=1.3798, north=50.3663, east=3.2028, country="FR"),
    Region("fr-81", "Tarn (Okzitanien)", "81", south=43.3828, west=1.5353, north=44.2015, east=2.9373, country="FR"),
    Region("fr-82", "Tarn-et-Garonne (Okzitanien)", "82", south=43.7674, west=0.7378, north=44.3939, east=2.0009, country="FR"),
    Region("fr-83", "Var (Provence-Alpes-Côte d'Azur)", "83", south=42.982, west=5.656, north=43.8087, east=6.9332, country="FR"),
    Region("fr-84", "Vaucluse (Provence-Alpes-Côte d'Azur)", "84", south=43.6587, west=4.6486, north=44.4316, east=5.7584, country="FR"),
    Region("fr-85", "Vendée (Pays de la Loire)", "85", south=46.2665, west=-2.4006, north=47.085, east=-0.5381, country="FR"),
    Region("fr-86", "Vienne (Nouvelle-Aquitaine)", "86", south=46.0483, west=-0.105, north=47.1759, east=1.2132, country="FR"),
    Region("fr-87", "Haute-Vienne (Nouvelle-Aquitaine)", "87", south=45.4366, west=0.6293, north=46.4015, east=1.9104, country="FR"),
    Region("fr-88", "Vosges (Grand Est)", "88", south=47.8137, west=5.3936, north=48.5137, east=7.1984, country="FR"),
    Region("fr-89", "Yonne (Bourgogne-Franche-Comté)", "89", south=47.3104, west=2.8485, north=48.4001, east=4.3401, country="FR"),
    Region("fr-90", "Territoire de Belfort (Bourgogne-Franche-Comté)", "90", south=47.4333, west=6.7565, north=47.8251, east=7.1433, country="FR"),
    Region("fr-91", "Essonne (Île-de-France)", "91", south=48.2846, west=1.9145, north=48.7761, east=2.5853, country="FR"),
    Region("fr-92", "Hauts-de-Seine (Île-de-France)", "92", south=48.7293, west=2.1457, north=48.9511, east=2.337, country="FR"),
    Region("fr-93", "Seine-Saint-Denis (Île-de-France)", "93", south=48.8073, west=2.2883, north=49.0123, east=2.6033, country="FR"),
    Region("fr-94", "Val-de-Marne (Île-de-France)", "94", south=48.6876, west=2.3087, north=48.8614, east=2.6158, country="FR"),
    Region("fr-95", "Val-d'Oise (Île-de-France)", "95", south=48.9087, west=1.6078, north=49.2414, east=2.595, country="FR"),
]

REGIONS: list[Region] = CANTON_REGIONS + STATE_REGIONS + IT_FR_REGIONS
REGIONS_BY_ID = {r.id: r for r in REGIONS}
COUNTRY_NAMES = {"CH": "Schweiz", "DE": "Deutschland", "AT": "Österreich", "IT": "Italien", "FR": "Frankreich"}
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
    if country in ("IT", "FR"):
        from regions_it_fr import normalize_it_fr

        return normalize_it_fr(country, str(value))
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
