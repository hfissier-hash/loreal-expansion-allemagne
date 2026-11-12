"""Compte les points de vente concurrents par ville via OpenStreetMap (API Overpass).

Usage (depuis la racine du repo) :
    pip install requests pandas
    python -m src.collect.collect_osm

Sortie : data/raw/externe/concurrents_villes.csv
  - store_count     : nombre de points de vente trouvés dans les limites de la ville
  - stores_per_100k : densité pour 100 000 habitants (population de villes_de.csv)

Limite : OSM est collaboratif. Les grandes enseignes y sont bien recensées en
Allemagne, mais les comptes restent un ordre de grandeur (contrôle en fin de script).
"""
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
VILLES = ROOT / "data/raw/externe/villes_de.csv"
OUT = ROOT / "data/raw/externe/concurrents_villes.csv"

# Plusieurs serveurs Overpass publics : on passe au suivant si l'un refuse ou est saturé.
SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
HEADERS = {"User-Agent": "eugenia-school-student-project/1.0 (data analytics course)"}

# Concurrent -> filtre OSM
CONCURRENTS = {
    "Douglas": 'nwr["brand"="Douglas"]["shop"]',
    "dm-drogerie markt": 'nwr["brand"="dm"]["shop"="chemist"]',
    "Rossmann": 'nwr["brand"="Rossmann"]["shop"="chemist"]',
    "Müller": 'nwr["brand"="Müller"]["shop"]',
    "Sephora": 'nwr["brand"="Sephora"]["shop"]',
    "Pharmacies": 'nwr["amenity"="pharmacy"]',
    "Instituts de beauté": 'nwr["shop"="beauty"]',
}


def build_query(city: str) -> str:
    """Une seule requête par ville : un 'out count' par concurrent, dans l'ordre."""
    area = (f'area["name"="{city}"]["boundary"="administrative"]'
            f'["admin_level"~"^(4|6)$"]->.a;')
    counts = "".join(f"({flt}(area.a););out count;" for flt in CONCURRENTS.values())
    return f"[out:json][timeout:120];{area}{counts}"


def run_query(query: str) -> dict:
    last_error = None
    for server in SERVERS:
        try:
            r = requests.post(server, data={"data": query}, headers=HEADERS, timeout=180)
            if r.status_code == 200:
                return r.json()
            last_error = f"{server} -> HTTP {r.status_code}"
        except requests.RequestException as e:
            last_error = f"{server} -> {e}"
        time.sleep(5)
    raise RuntimeError(f"Aucun serveur Overpass n'a répondu ({last_error})")


def main() -> None:
    villes = pd.read_csv(VILLES)
    rows = []
    for _, v in villes.iterrows():
        data = run_query(build_query(v["city"]))
        totals = [int(e["tags"]["total"]) for e in data["elements"] if e.get("type") == "count"]
        if len(totals) != len(CONCURRENTS):
            raise ValueError(f"{v['city']} : {len(totals)} comptes reçus au lieu de {len(CONCURRENTS)}")
        for name, n in zip(CONCURRENTS, totals):
            rows.append({
                "city": v["city"],
                "competitor": name,
                "store_count": n,
                "stores_per_100k": round(n / v["population"] * 100_000, 2),
                "source_id": "OSM",
                "status": "collecté",
                "collected_at": date.today().isoformat(),
            })
        print(f"{v['city']:<18} " + "  ".join(f"{k.split()[0]}={n}" for k, n in zip(CONCURRENTS, totals)))
        time.sleep(10)  # politesse envers le serveur public

    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    print(f"\n{len(df)} lignes écrites dans {OUT.relative_to(ROOT)}")

    # Contrôle de cohérence : villes sans aucun résultat = zone mal trouvée
    zero = df.groupby("city")["store_count"].sum().loc[lambda s: s == 0]
    if not zero.empty:
        print("ATTENTION, aucune boutique trouvée pour :", ", ".join(zero.index))


if __name__ == "__main__":
    main()
