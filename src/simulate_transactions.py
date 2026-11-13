"""Détaille la base interne SIMULÉE au grain transactionnel : diagnostics, ventes, rachats.

Part des agrégats de `simulate_internal.py` (boutiques_france.csv, catalogue_france.csv)
et les respecte boutique par boutique : nombre de diagnostics, taux de conversion,
taux de rachat sous 6 mois, CA TTC par marque, taux de marge. Les KPIs du business case
ne changent donc pas ; le détail permet de les recalculer et de les expliquer.

Sorties (data/raw/interne/, non versionnées car régénérées à l'identique) :
  produits_attributs.csv, clientes.csv, diagnostics.csv, ventes.csv
Commande : python -m src.simulate_transactions   (Python standard, sans dépendance)
"""
import csv
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

INT = Path(__file__).resolve().parents[1] / "data" / "raw" / "interne"
SEED = 2027
YEAR = 2025
VAT_FR = 0.20

# Fourchettes de prix TTC par marque (SIMULÉ, ordre de grandeur des prix publics)
PRICE_RANGE = {"La Roche-Posay": (11, 40), "CeraVe": (9, 24), "Vichy": (14, 45),
               "SkinCeuticals": (60, 180), "Kiehl's": (24, 60), "Lancôme Skincare": (40, 120)}
CONCERNS = [("imperfections", 0.20), ("sensibilité", 0.20), ("sécheresse", 0.22),
            ("signes de l'âge", 0.22), ("éclat", 0.10), ("protection solaire", 0.06)]
CONCERNS_BY_AGE = {
    "18-24": [("imperfections", 0.55), ("sensibilité", 0.20), ("sécheresse", 0.15), ("éclat", 0.10)],
    "25-34": [("imperfections", 0.30), ("sensibilité", 0.25), ("sécheresse", 0.20), ("éclat", 0.15), ("signes de l'âge", 0.10)],
    "35-44": [("sensibilité", 0.20), ("sécheresse", 0.20), ("éclat", 0.20), ("signes de l'âge", 0.35), ("imperfections", 0.05)],
    "45-54": [("signes de l'âge", 0.55), ("sécheresse", 0.25), ("sensibilité", 0.15), ("éclat", 0.05)],
    "55+": [("signes de l'âge", 0.60), ("sécheresse", 0.30), ("sensibilité", 0.10)],
}
AGE_BANDS = [("18-24", 0.16), ("25-34", 0.27), ("35-44", 0.22), ("45-54", 0.19), ("55+", 0.16)]
GENDERS = [("F", 0.78), ("M", 0.22)]
SKIN_TYPES = [("mixte", 0.30), ("sèche", 0.22), ("sensible", 0.20), ("grasse", 0.15), ("normale", 0.13)]
# Tailles de panier calées sur l'hypothèse de l'équipe (Gaspard) : ≈ 56 € TTC après diagnostic,
# ≈ 35 € sans diagnostic (décision du 13/11/2026). Vérifié par tests/test_warehouse.py.
BASKET_SIZE = [(1, 0.30), (2, 0.45), (3, 0.20), (4, 0.05)]   # routine conseillée après diagnostic
WALKIN_SIZE = [(1, 0.76), (2, 0.24)]                        # achat sans diagnostic
REPURCHASE_FIRST_DELAY = (30, 180)                          # « revenue sous 6 mois »
REPURCHASE_CHAIN_RATE, REPURCHASE_CHAIN_DELAY = 0.40, (45, 120)
WEEKDAY_FACTOR = {0: 0.80, 1: 0.85, 2: 0.95, 3: 1.00, 4: 1.10, 5: 1.40}   # fermé le dimanche
MONTH_FACTOR = {7: 0.85, 8: 0.80, 11: 1.10, 12: 1.30}


def pick(rng, pairs):
    values, weights = zip(*pairs)
    return rng.choices(values, weights=weights)[0]


def read(name):
    with open(INT / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write(name, rows):
    with open(INT / name, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    rng = random.Random(SEED)
    stores = defaultdict(dict)   # store_id -> attributs + revenus et marges par marque
    for r in read("boutiques_france.csv"):
        s = stores[r["store_id"]]
        s.update(city=r["city"], diagnostics=int(r["diagnostics_per_year"]),
                 conversion=float(r["diag_conversion_rate"]), repurchase=float(r["repurchase_rate_6m"]))
        s.setdefault("target", {})[r["brand"]] = float(r["revenue_ttc_eur"])
        s.setdefault("margin", {})[r["brand"]] = float(r["gross_margin_rate_ht"])

    # attributs produits simulés (prix, besoin couvert) pour le catalogue existant
    products = []
    for p in read("catalogue_france.csv"):
        low, high = PRICE_RANGE[p["brand"]]
        products.append({"sku": p["sku"], "brand": p["brand"], "skin_concern": pick(rng, CONCERNS),
                          "list_price_ttc": round(rng.uniform(low, high)) - 0.1})
    by_brand, by_brand_concern = defaultdict(list), defaultdict(list)
    for p in products:
        by_brand[p["brand"]].append(p)
        by_brand_concern[p["brand"], p["skin_concern"]].append(p)
    avg_price = {b: sum(p["list_price_ttc"] for p in ps) / len(ps) for b, ps in by_brand.items()}

    open_days = [date(YEAR, 1, 1) + timedelta(days=i) for i in range(365)]
    open_days = [d for d in open_days if d.weekday() != 6]
    day_weight = [WEEKDAY_FACTOR[d.weekday()] * MONTH_FACTOR.get(d.month, 1.0) for d in open_days]
    year_end = date(YEAR, 12, 31)

    customers, diagnostics, sales = [], [], []
    ids = defaultdict(int)

    def ticket(day, store_id, customer, items, sale_type, diagnostic_id=""):
        ids["ticket"] += 1
        for p in items:
            ids["line"] += 1
            sales.append({"sale_line_id": ids["line"], "ticket_id": ids["ticket"], "date": day.isoformat(),
                          "store_id": store_id, "customer_code": customer, "sku": p["sku"],
                          "diagnostic_id": diagnostic_id, "sale_type": sale_type, "quantity": 1,
                          "unit_price_ttc": p["list_price_ttc"],
                          "gross_margin_rate_ht": stores[store_id]["margin"][p["brand"]]})
        return sum(p["list_price_ttc"] for p in items)

    for store_id in sorted(stores):
        s = stores[store_id]
        # marque d'un article : poids = part de CA / prix moyen (part en volume)
        brand_weights = [(b, s["target"][b] / avg_price[b]) for b in s["target"]]
        revenue = defaultdict(float)
        n = s["diagnostics"]
        dates = sorted(rng.choices(open_days, weights=day_weight, k=n))
        converted = set(rng.sample(range(n), round(n * s["conversion"])))
        returning = set(rng.sample(sorted(converted), round(len(converted) * s["repurchase"])))

        for i, day in enumerate(dates):
            ids["customer"] += 1
            code = f"C{ids['customer']:07d}"
            age = pick(rng, AGE_BANDS)
            customers.append({"customer_code": code, "gender": pick(rng, GENDERS), "age_band": age,
                              "skin_type": pick(rng, SKIN_TYPES), "home_store_id": store_id,
                              "first_visit_date": day.isoformat(),
                              "loyalty_member": int(i in converted and rng.random() < 0.6),
                              "returned_6m": int(i in returning)})
            concern = pick(rng, CONCERNS_BY_AGE[age])
            ids["diag"] += 1
            diagnostics.append({"diagnostic_id": ids["diag"], "date": day.isoformat(), "store_id": store_id,
                                "customer_code": code, "skin_type_detected": customers[-1]["skin_type"],
                                "main_concern": concern, "duration_min": rng.randint(15, 30),
                                "nb_products_recommended": rng.randint(2, 4), "converted": int(i in converted)})
            if i not in converted:
                continue
            items = []
            for _ in range(pick(rng, BASKET_SIZE)):
                brand = pick(rng, brand_weights)
                items.append(rng.choice(by_brand_concern.get((brand, concern)) or by_brand[brand]))
            for p in items:
                revenue[p["brand"]] += p["list_price_ttc"]
            ticket(day, store_id, code, items, "apres_diagnostic", ids["diag"])
            if i in returning:
                when = day + timedelta(days=rng.randint(*REPURCHASE_FIRST_DELAY))
                while when <= year_end:
                    when += timedelta(days=when.weekday() == 6)
                    again = [p for p in items if rng.random() < 0.7] or [rng.choice(items)]
                    for p in again:
                        revenue[p["brand"]] += p["list_price_ttc"]
                    ticket(when, store_id, code, again, "rachat")
                    if rng.random() >= REPURCHASE_CHAIN_RATE:
                        break
                    when += timedelta(days=rng.randint(*REPURCHASE_CHAIN_DELAY))

        # achats sans diagnostic (clients de passage) : complètent le CA de chaque marque
        for brand, target in s["target"].items():
            while target - revenue[brand] > avg_price[brand] / 2:
                day = rng.choices(open_days, weights=day_weight)[0]
                items = [rng.choice(by_brand[brand]) for _ in range(pick(rng, WALKIN_SIZE))]
                revenue[brand] += ticket(day, store_id, "C0000000", items, "sans_diagnostic")

    write("produits_attributs.csv", products)
    write("clientes.csv", customers)
    write("diagnostics.csv", diagnostics)
    write("ventes.csv", sales)
    print(f"{len(stores)} boutiques : {len(diagnostics)} diagnostics, {ids['ticket']} tickets, "
          f"{len(sales)} lignes de vente, {len(customers)} clientes.")


if __name__ == "__main__":
    main()
