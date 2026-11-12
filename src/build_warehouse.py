"""Construit l'entrepôt en constellation (sql/schema.sql) à partir des données brutes,
de la base interne détaillée et des résultats du business case.

Entrées : data/raw/externe, data/raw/interne (dont les sorties de simulate_transactions),
          data/raw/sources.csv, data/gold (fact_business_case, fact_plan_deploiement, dim_scenario)
Sorties : data/warehouse/<table>.csv, data/warehouse/warehouse.sqlite (clés étrangères
          vérifiées), data/warehouse/rapport_qualite.md
Ordre : python -m src.simulate_transactions, python -m src.build, puis python -m src.build_warehouse
(Python standard, sans dépendance)
"""
import csv
import math
import sqlite3
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT, INT, GOLD = ROOT / "data/raw/externe", ROOT / "data/raw/interne", ROOT / "data/gold"
OUT, SCHEMA = ROOT / "data/warehouse", ROOT / "sql/schema.sql"

TARGET_CITIES_2027 = ["München", "Düsseldorf", "Frankfurt am Main"]
CITY_ALIASES = {"Munich": "München", "Dusseldorf": "Düsseldorf", "Frankfurt": "Frankfurt am Main",
                "Cologne": "Köln"}
# Villes des boutiques pilotes : (région, latitude, longitude du centre-ville)
FR_CITIES = {
    "Paris": ("Île-de-France", 48.857, 2.352), "Lyon": ("Auvergne-Rhône-Alpes", 45.764, 4.836),
    "Marseille": ("Provence-Alpes-Côte d'Azur", 43.296, 5.370), "Bordeaux": ("Nouvelle-Aquitaine", 44.838, -0.579),
    "Lille": ("Hauts-de-France", 50.629, 3.057), "Toulouse": ("Occitanie", 43.605, 1.444),
    "Nice": ("Provence-Alpes-Côte d'Azur", 43.710, 7.262), "Nantes": ("Pays de la Loire", 47.218, -1.554),
    "Strasbourg": ("Grand Est", 48.573, 7.752), "Montpellier": ("Occitanie", 43.611, 3.877),
}
# Libellés d'emplacement des différentes sources → code commun
LOCATIONS = {"Rue commerçante 1a": "rue_1a", "Rue commerçante 1a (médiane)": "rue_1a",
             "Artère n°1": "artere_n1", "Artère n°1 (flagship)": "artere_n1"}
LOCATION_NAMES = {"rue_1a": "Rue commerçante 1a (médiane)", "artere_n1": "Artère n°1 (flagship)"}
SKINCARE, TOTAL = "Soins de la peau", "Total marché"
VAT_FR = 0.20
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
          "septembre", "octobre", "novembre", "décembre"]
WEEKDAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [{k.strip(): clean(v) for k, v in r.items()} for r in csv.DictReader(f)]


def clean(v):
    if v is None:
        return None
    v = " ".join(v.split())
    return None if v in ("", "[site français]") else v


def num(v):
    return None if v is None else float(v.replace(" ", "").replace(",", "."))


def integer(v):
    n = num(v)
    return None if n is None else int(round(n))


def city(v):
    return CITY_ALIASES.get(v, v)


def dkey(iso):
    return int(iso.replace("-", "")) if iso else None


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def keyed(rows, key):
    for i, r in enumerate(rows, start=1):
        r[key] = i
    return rows


def build():
    ext = {n: read(EXT / f"{n}.csv") for n in [
        "villes_de", "marche_pays", "categories_pays", "parts_de_marche", "concurrents_nationaux",
        "concurrents_villes", "loyers_villes", "prix_taxes", "releve_prix_soins", "hubs_loreal", "reglementation"]}
    intern = {n: read(INT / f"{n}.csv") for n in [
        "boutiques_france", "catalogue_france", "hypotheses", "produits_attributs", "clientes", "diagnostics", "ventes"]}
    gold = {n: read(GOLD / f"{n}.csv") for n in ["fact_business_case", "fact_plan_deploiement", "dim_scenario"]}
    hyp = {h["parameter"]: num(h["value"]) for h in intern["hypotheses"]}
    t = {}

    # --- dimensions ---
    d, rows = date(2024, 1, 1), []
    while d <= date(2031, 12, 31):
        rows.append({"date_key": dkey(d.isoformat()), "full_date": d.isoformat(), "year": d.year,
                     "quarter": (d.month - 1) // 3 + 1, "month": d.month, "month_name": MONTHS[d.month - 1],
                     "iso_week": d.isocalendar()[1], "weekday": d.isoweekday(),
                     "weekday_name": WEEKDAYS[d.weekday()], "is_weekend": int(d.weekday() >= 5)})
        d += timedelta(days=1)
    t["dim_date"] = rows

    names = {r["country_code"]: r["country"] for r in ext["marche_pays"]}
    t["dim_country"] = [{"country_code": r["country_code"], "country_name": names.get(r["country_code"]),
                         "vat_standard_pct": num(r["vat_standard_pct"]),
                         "customs_duty_intra_eu_pct": num(r["customs_duty_intra_eu_pct"]),
                         "price_level_index_eu100": num(r["price_level_index_eu100"]),
                         "pli_year": integer(r["pli_year"]), "source_ids": r["source_id"]} for r in ext["prix_taxes"]]

    cities = [{"city_name": city(r["city"]), "region": r["state"], "country_code": "DE",
               "city_role": "cible_2027" if city(r["city"]) in TARGET_CITIES_2027 else "comparaison_de",
               "population": integer(r["population"]), "population_year": integer(r["population_year"]),
               "population_status": r["population_status"],
               "purchasing_power_eur_per_capita": num(r["purchasing_power_eur_per_capita"]),
               "purchasing_power_index": num(r["purchasing_power_index"]),
               "purchasing_power_year": integer(r["purchasing_power_year"]),
               "lat": num(r["lat"]), "lon": num(r["lon"]), "source_ids": r["source_id"]} for r in ext["villes_de"]]
    fr_cities = sorted({r["city"] for r in intern["boutiques_france"]})
    unknown = [c for c in fr_cities if c not in FR_CITIES]
    if unknown:
        raise ValueError(f"Coordonnées manquantes dans FR_CITIES : {unknown}")
    cities += [{"city_name": c, "region": FR_CITIES[c][0], "country_code": "FR", "city_role": "pilote_fr",
                "population": None, "population_year": None, "population_status": None,
                "purchasing_power_eur_per_capita": None, "purchasing_power_index": None,
                "purchasing_power_year": None, "lat": FR_CITIES[c][1], "lon": FR_CITIES[c][2],
                "source_ids": "INTERNE"} for c in fr_cities]
    t["dim_city"] = keyed(cities, "city_key")
    city_key = {c["city_name"]: c["city_key"] for c in cities}

    t["dim_location"] = [{"location_key": i, "location_code": code, "location_name": name}
                         for i, (code, name) in enumerate(LOCATION_NAMES.items(), start=1)]
    location_key = {r["location_code"]: r["location_key"] for r in t["dim_location"]}

    t["dim_scenario"] = keyed([{"scenario_name": r["scenario"], "revenue_factor": num(r["revenue_factor"])}
                               for r in gold["dim_scenario"]], "scenario_key")
    scenario_key = {r["scenario_name"]: r["scenario_key"] for r in t["dim_scenario"]}

    stores, seen = [], set()
    for r in intern["boutiques_france"]:
        if r["store_id"] not in seen:
            seen.add(r["store_id"])
            stores.append({"store_code": r["store_id"], "store_name": f"{r['city']} {r['store_id']}",
                           "city_key": city_key[r["city"]], "store_status": "pilote_fr",
                           "surface_m2": num(r["surface_m2"]), "opening_year": None, "is_simulated": 1})
    stores += [{"store_code": f"DE{i:02d}", "store_name": c, "city_key": city_key[c], "store_status": "projet_de",
                "surface_m2": hyp.get("surface_boutique_m2"), "opening_year": 2027, "is_simulated": 0}
               for i, c in enumerate(TARGET_CITIES_2027, start=1)]
    t["dim_store"] = keyed(stores, "store_key")
    store_key = {s["store_code"]: s["store_key"] for s in stores}

    cats = [TOTAL] + sorted({r["category"] for r in ext["categories_pays"]})
    t["dim_category"] = [{"category_key": i, "category_name": c} for i, c in enumerate(cats)]
    category_key = {c: i for i, c in enumerate(cats)}

    attrs = {p["sku"]: p for p in intern["produits_attributs"]}
    t["dim_product"] = keyed([{
        "sku": p["sku"], "brand": p["brand"], "category_key": category_key[p["category"]],
        "skin_concern": attrs[p["sku"]]["skin_concern"], "list_price_fr_ttc": num(attrs[p["sku"]]["list_price_ttc"]),
        "eligible_de": int(p["france_only"] != "True"), "is_simulated": 1,
    } for p in intern["catalogue_france"]], "product_key")
    product_key = {p["sku"]: p["product_key"] for p in t["dim_product"]}
    brand_of = {p["sku"]: p["brand"] for p in t["dim_product"]}

    customers = [{"customer_key": 0, "customer_code": "C0000000", "gender": None, "age_band": None,
                  "skin_type": None, "home_store_key": None, "first_visit_date_key": None,
                  "loyalty_member": None, "returned_6m": None}]
    customers += [{"customer_key": i, "customer_code": c["customer_code"], "gender": c["gender"],
                   "age_band": c["age_band"], "skin_type": c["skin_type"],
                   "home_store_key": store_key[c["home_store_id"]],
                   "first_visit_date_key": dkey(c["first_visit_date"]),
                   "loyalty_member": integer(c["loyalty_member"]), "returned_6m": integer(c["returned_6m"])}
                  for i, c in enumerate(intern["clientes"], start=1)]
    t["dim_customer"] = customers
    customer_key = {c["customer_code"]: c["customer_key"] for c in customers}

    retailers = {r["retailer"]: {"retailer_name": r["retailer"], "segment": r["segment"],
                                 "stores_de": integer(r["stores_de"]), "revenue_bn_eur": num(r["revenue_bn_eur"]),
                                 "revenue_scope": r["revenue_scope"], "source_ids": r["source_id"],
                                 "status": r["status"]} for r in ext["concurrents_nationaux"]}
    for r in ext["concurrents_villes"]:
        retailers.setdefault(r["competitor"], {"retailer_name": r["competitor"], "segment": "Autre point de vente soin",
                                               "stores_de": None, "revenue_bn_eur": None, "revenue_scope": None,
                                               "source_ids": None, "status": None})
    t["dim_retailer"] = keyed(list(retailers.values()), "retailer_key")
    retailer_key = {r["retailer_name"]: r["retailer_key"] for r in t["dim_retailer"]}

    t["dim_hub"] = keyed([{"hub_name": r["hub"], "country_code": r["country_code"], "hub_type": r["type"],
                           "lat": num(r["lat"]), "lon": num(r["lon"]), "source_ids": r["source_id"]}
                          for r in ext["hubs_loreal"]], "hub_key")

    t["dim_source"] = [{"source_id": r["source_id"], "source_name": r["name"], "publisher": r["publisher"],
                        "url": r["url"], "source_type": r["type"], "reliability": r["reliability"]}
                       for r in read(ROOT / "data/raw/sources.csv")]

    # --- faits internes (simulés) ---
    t["fact_diagnostic"] = [{
        "diagnostic_id": integer(r["diagnostic_id"]), "date_key": dkey(r["date"]), "store_key": store_key[r["store_id"]],
        "customer_key": customer_key[r["customer_code"]], "skin_type_detected": r["skin_type_detected"],
        "main_concern": r["main_concern"], "duration_min": integer(r["duration_min"]),
        "nb_products_recommended": integer(r["nb_products_recommended"]), "converted": integer(r["converted"]),
    } for r in intern["diagnostics"]]

    sales = []
    for r in intern["ventes"]:
        qty, price = integer(r["quantity"]), num(r["unit_price_ttc"])
        ttc = round(qty * price, 2)
        ht = round(ttc / (1 + VAT_FR), 2)
        margin = round(ht * num(r["gross_margin_rate_ht"]), 2)
        sales.append({"sale_line_id": integer(r["sale_line_id"]), "ticket_id": integer(r["ticket_id"]),
                      "date_key": dkey(r["date"]), "store_key": store_key[r["store_id"]],
                      "customer_key": customer_key[r["customer_code"]], "product_key": product_key[r["sku"]],
                      "diagnostic_id": integer(r["diagnostic_id"]), "sale_type": r["sale_type"], "quantity": qty,
                      "unit_price_ttc": price, "revenue_ttc": ttc, "revenue_ht": ht,
                      "cogs_ht": round(ht - margin, 2), "gross_margin_ht": margin})
    t["fact_sales"] = sales

    # --- faits externes ---
    year_of = {r["source_id"]: integer(r["year"]) for r in ext["marche_pays"]}
    t["fact_market"] = [{"country_code": r["country_code"], "year": integer(r["year"]), "category_key": 0,
                         "value_bn_eur": num(r["market_value_bn_eur"]),
                         "share_pct": 100.0 if r["market_value_bn_eur"] else None, "growth_pct": num(r["growth_pct"]),
                         "spend_per_capita_eur": num(r["spend_per_capita_eur"]), "source_ids": r["source_id"]}
                        for r in ext["marche_pays"]]
    t["fact_market"] += [{"country_code": r["country_code"], "year": year_of.get(r["source_id"], 2025),
                          "category_key": category_key[r["category"]], "value_bn_eur": num(r["value_bn_eur"]),
                          "share_pct": num(r["share_pct"]), "growth_pct": num(r["growth_pct"]),
                          "spend_per_capita_eur": None, "source_ids": r["source_id"]} for r in ext["categories_pays"]]

    t["fact_market_share"] = [{"country_code": r["country_code"], "scope": r["scope"], "player": r["player"],
                               "year": integer(r["year"]), "market_share_pct": num(r["market_share_pct"]),
                               "source_ids": r["source_id"], "status": r["status"]} for r in ext["parts_de_marche"]]

    population = {c["city_key"]: c["population"] for c in cities}
    competition = []
    for r in ext["concurrents_villes"]:
        ck, count, density = city_key[city(r["city"])], integer(r["store_count"]), num(r["stores_per_100k"])
        if density is None and count is not None and population.get(ck):
            density = round(count / population[ck] * 100_000, 2)
        competition.append({"city_key": ck, "retailer_key": retailer_key[r["competitor"]], "store_count": count,
                            "stores_per_100k": density, "source_ids": r["source_id"], "status": r["status"]})
    t["fact_competition"] = competition

    t["fact_rent"] = [{"city_key": city_key[city(r["city"])], "location_key": location_key[LOCATIONS[r["location"]]],
                       "rent_eur_m2_month": round(num(r["rent_eur_m2"]) / (12 if r["unit"] == "€/m²/an" else 1), 2),
                       "rent_raw": num(r["rent_eur_m2"]), "unit_raw": r["unit"], "period": r["period"],
                       "trend_pct_pa": num(r["trend_pct_pa"]), "source_ids": r["source_id"]} for r in ext["loyers_villes"]]

    vat = {c["country_code"]: c["vat_standard_pct"] for c in t["dim_country"]}
    prices = []
    for r in ext["releve_prix_soins"]:
        for cc, pcol, rcol in (("DE", "price_de_eur", "retailer_de"), ("FR", "price_fr_eur", "retailer_fr")):
            ttc = num(r[pcol])
            prices.append({"product_name": r["product"], "brand": r["brand"], "size": r["size"], "country_code": cc,
                           "retailer": r[rcol] or "à préciser", "price_ttc": ttc,
                           "price_ht": None if ttc is None else round(ttc / (1 + vat[cc] / 100), 2),
                           "collected_at": r["collected_at"], "status": r["status"]})
    t["fact_price"] = prices

    road = hyp.get("facteur_route", 1.25)
    t["fact_hub_distance"] = [{"hub_key": h["hub_key"], "city_key": c["city_key"],
                               "distance_km_vol_oiseau": round(haversine_km(h["lat"], h["lon"], c["lat"], c["lon"]), 1),
                               "distance_km_route_estimee": round(haversine_km(h["lat"], h["lon"], c["lat"], c["lon"]) * road)}
                              for h in t["dim_hub"] for c in cities]

    t["fact_business_case"] = [dict(
        {"city_key": city_key[r["city"]], "location_key": location_key[LOCATIONS[r["location"]]],
         "scenario_key": scenario_key[r["scenario"]]},
        **{k: num(r[k]) for k in ["revenue_ttc_eur", "revenue_ht_eur", "gross_margin_eur", "rent_eur", "staff_eur",
                                  "other_costs_eur", "logistics_eur", "ebitda_eur", "ebitda_margin_pct", "capex_eur",
                                  "payback_years", "breakeven_revenue_ttc_eur"]}) for r in gold["fact_business_case"]]

    t["fact_deployment_plan"] = [{"scenario_key": scenario_key[r["scenario"]], "year": integer(r["year"]),
                                  "date_key": integer(r["year"]) * 10000 + 1231, "stores": integer(r["stores"]),
                                  "revenue_ttc_eur": num(r["revenue_ttc_eur"]), "ebitda_eur": num(r["ebitda_eur"]),
                                  "capex_eur": num(r["capex_eur"]), "cumulative_cash_eur": num(r["cumulative_cash_eur"])}
                                 for r in gold["fact_plan_deploiement"]]

    t["ref_hypotheses"] = [{"parameter": r["parameter"], "value": num(r["value"]), "unit": r["unit"],
                            "rationale": r["rationale"]} for r in intern["hypotheses"]]
    t["ref_reglementation"] = [{"topic": r["topic"], "france": r["france"], "allemagne": r["allemagne"],
                                "impact": r["impact"], "source_ids": r["source_id"]} for r in ext["reglementation"]]
    return t, ext, intern


ORDER = ["dim_date", "dim_country", "dim_city", "dim_location", "dim_scenario", "dim_store", "dim_category",
         "dim_product", "dim_customer", "dim_retailer", "dim_hub", "dim_source", "fact_diagnostic", "fact_sales",
         "fact_market", "fact_market_share", "fact_competition", "fact_rent", "fact_price", "fact_hub_distance",
         "fact_business_case", "fact_deployment_plan", "ref_hypotheses", "ref_reglementation"]


def write(t):
    OUT.mkdir(parents=True, exist_ok=True)
    db = OUT / "warehouse.sqlite"
    db.unlink(missing_ok=True)
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    for table in ORDER:
        cols = [c[1] for c in conn.execute(f"PRAGMA table_info({table})")]
        conn.executemany(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                         [[r[c] for c in cols] for r in t[table]])
        with open(OUT / f"{table}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(t[table])
    conn.commit()
    return conn


def report(conn, ext, intern):
    q = lambda sql: conn.execute(sql).fetchone()[0]  # noqa: E731
    fmt = lambda n: f"{n:,.0f}".replace(",", " ")     # noqa: E731
    lines = ["# Rapport qualité de l'entrepôt", "", "Généré par `src/build_warehouse.py`, ne pas modifier à la main.",
             "", "## Volumes", "", "| Table | Lignes |", "|---|---|"]
    lines += [f"| {tb} | {fmt(q(f'SELECT COUNT(*) FROM {tb}'))} |" for tb in ORDER]

    target = {}
    for r in intern["boutiques_france"]:
        target[r["store_id"]] = target.get(r["store_id"], 0) + float(r["revenue_ttc_eur"])
    actual = dict(conn.execute("SELECT st.store_code, SUM(revenue_ttc) FROM fact_sales JOIN dim_store st USING (store_key) GROUP BY 1"))
    gap = max(abs(actual[s] - target[s]) / target[s] * 100 for s in target)
    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    lines += ["", "## Contrôles", "",
              f"- Clés étrangères orphelines : {len(fk)}",
              f"- Écart maximal entre le CA détaillé et le CA agrégé de boutiques_france.csv : {gap:.2f} %",
              f"- Ventes « après diagnostic » sans diagnostic converti : "
              f"{q('''SELECT COUNT(*) FROM fact_sales s LEFT JOIN fact_diagnostic d USING (diagnostic_id)
                      WHERE s.sale_type = 'apres_diagnostic' AND COALESCE(d.converted, 0) = 0''')}",
              f"- Ventes un dimanche : {q('SELECT COUNT(*) FROM fact_sales JOIN dim_date USING (date_key) WHERE weekday = 7')}"]

    lines += ["", "## Données encore manquantes", ""]
    for name, rows in ext.items():
        todo = [r for r in rows if (r.get("status") or "").startswith(("à collecter", "non publié"))]
        if todo:
            lines.append(f"- `{name}.csv` : {len(todo)} ligne(s) « {todo[0]['status']} »")

    conv, rep = conn.execute("""SELECT AVG(converted),
        (SELECT AVG(returned_6m) FROM dim_customer c JOIN fact_diagnostic d USING (customer_key) WHERE d.converted = 1)
        FROM fact_diagnostic""").fetchone()
    lines += ["", "## Repères de la base interne simulée (2025)", "",
              f"- Diagnostics : {fmt(q('SELECT COUNT(*) FROM fact_diagnostic'))} ; conversion {conv * 100:.1f} % ; "
              f"rachat sous 6 mois {rep * 100:.1f} % des clientes converties",
              f"- CA TTC : {q('SELECT SUM(revenue_ttc) FROM fact_sales') / 1e6:.2f} M€, "
              f"soit {q('SELECT SUM(revenue_ttc) FROM fact_sales') / 20 / 1e3:.0f} k€ par boutique"]
    for sale_type, share in conn.execute("""SELECT sale_type, SUM(revenue_ttc) * 100.0 / (SELECT SUM(revenue_ttc) FROM fact_sales)
                                            FROM fact_sales GROUP BY 1 ORDER BY 2 DESC"""):
        lines.append(f"- Part du CA « {sale_type} » : {share:.1f} %")
    (OUT / "rapport_qualite.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return fk


def main():
    t, ext, intern = build()
    conn = write(t)
    fk = report(conn, ext, intern)
    conn.close()
    print((OUT / "rapport_qualite.md").read_text(encoding="utf-8"))
    if fk:
        raise SystemExit("Clés étrangères orphelines : voir le rapport.")


if __name__ == "__main__":
    main()
