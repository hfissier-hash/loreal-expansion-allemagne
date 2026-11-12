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
    return f"[out:json][timeout:90];{area}{counts}"


def run_query(query: str) -> list[int]:
    """Renvoie les comptes, en passant au serveur suivant si la réponse est vide ou invalide."""
    last_error = None
    for server in SERVERS:
        try:
            r = requests.post(server, data={"data": query}, headers=HEADERS, timeout=100)
            if r.status_code != 200:
                last_error = f"{server} -> HTTP {r.status_code}"
            else:
                totals = [int(e["tags"]["total"]) for e in r.json()["elements"] if e.get("type") == "count"]
                if len(totals) != len(CONCURRENTS):
                    last_error = f"{server} -> {len(totals)} comptes au lieu de {len(CONCURRENTS)}"
                elif sum(totals) == 0:
                    # Une grande ville sans aucun magasin = zone de la ville introuvable sur ce serveur
                    last_error = f"{server} -> zone de la ville introuvable (tout à 0)"
                else:
                    return totals
        except (requests.RequestException, ValueError) as e:
            last_error = f"{server} -> {e}"
        time.sleep(5)
    raise RuntimeError(f"Aucun serveur Overpass n'a donné de résultat valide ({last_error})")


# Population officielle au 31/12/2025 (Destatis), utilisée si le script tourne hors du dépôt
VILLES_PAR_DEFAUT = {
    "München": 1505036, "Düsseldorf": 619444, "Frankfurt am Main": 760656,
    "Stuttgart": 609365, "Hamburg": 1869473, "Köln": 1025523,
    "Berlin": 3700577, "Leipzig": 615932,
}


def main() -> None:
    global OUT
    if VILLES.exists():
        villes = pd.read_csv(VILLES)
    else:  # lancé seul, hors du dépôt : on écrit le CSV à côté du script
        villes = pd.DataFrame(VILLES_PAR_DEFAUT.items(), columns=["city", "population"])
        OUT = Path.cwd() / "concurrents_villes.csv"

    # Reprise : on garde les villes déjà collectées lors d'un lancement précédent
    deja = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame()
    if not deja.empty and "status" in deja:
        deja = deja[deja["status"] == "collecté"]
        # Une ville enregistrée avec 0 magasin partout est fausse : on la refait
        vides = deja.groupby("city")["store_count"].sum().loc[lambda s: s == 0].index
        deja = deja[~deja["city"].isin(vides)]
    faites = set(deja["city"]) if not deja.empty else set()

    echecs = []
    for _, v in villes.iterrows():
        if v["city"] in faites:
            print(f"{v['city']:<18} déjà collectée, on passe")
            continue
        try:
            totals = run_query(build_query(v["city"]))
        except Exception as e:
            print(f"{v['city']:<18} ÉCHEC ({e}) : relance le script plus tard")
            echecs.append(v["city"])
            continue
        rows = [{
            "city": v["city"],
            "competitor": name,
            "store_count": n,
            "stores_per_100k": round(n / v["population"] * 100_000, 2),
            "source_id": "OSM",
            "status": "collecté",
            "collected_at": date.today().isoformat(),
        } for name, n in zip(CONCURRENTS, totals)]
        deja = pd.concat([deja, pd.DataFrame(rows)], ignore_index=True)
        deja.to_csv(OUT, index=False)  # sauvegarde après chaque ville
        print(f"{v['city']:<18} " + "  ".join(f"{k.split()[0]}={n}" for k, n in zip(CONCURRENTS, totals)))
        time.sleep(10)  # politesse envers le serveur public

    print(f"\n{deja['city'].nunique()} villes sur {len(villes)} dans {OUT}")
    if echecs:
        print("Villes à reprendre (relance simplement le script) :", ", ".join(echecs))
    else:
        zero = deja.groupby("city")["store_count"].sum().loc[lambda s: s == 0]
        if not zero.empty:
            print("ATTENTION, aucune boutique trouvée pour :", ", ".join(zero.index))


if __name__ == "__main__":
    main()
