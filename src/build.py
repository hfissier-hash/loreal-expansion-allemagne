"""Pipeline : sources brutes -> modèle en étoile (Gold) -> KPIs et business case.

Commande : python -m src.build
Écrit data/gold/*.csv et docs/kpis.json, et s'arrête si un contrôle échoue.
"""
import json
import math
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, GOLD = ROOT / "data" / "raw", ROOT / "data" / "gold"
EXT, INT = RAW / "externe", RAW / "interne"


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def load():
    h = pd.read_csv(INT / "hypotheses.csv").set_index("parameter")["value"].astype(float).to_dict()
    return {
        "marche": pd.read_csv(EXT / "marche_pays.csv"),
        "categories": pd.read_csv(EXT / "categories_pays.csv"),
        "prix": pd.read_csv(EXT / "prix_taxes.csv").set_index("country_code"),
        "villes": pd.read_csv(EXT / "villes_de.csv"),
        "concurrents": pd.read_csv(EXT / "concurrents_de.csv"),
        "hubs": pd.read_csv(EXT / "hubs_loreal.csv").set_index("hub"),
        "reglementation": pd.read_csv(EXT / "reglementation.csv"),
        "sources": pd.read_csv(RAW / "sources.csv"),
        "boutiques": pd.read_csv(INT / "boutiques_france.csv"),
        "catalogue": pd.read_csv(INT / "catalogue_france.csv"),
        "h": h,
    }


def build(d):
    h = d["h"]
    m25 = d["marche"][d["marche"].year == 2025].set_index("country_code")
    prix = d["prix"]

    # --- Dimensions
    dim_pays = m25[["country"]].join(prix[["vat_standard_pct", "price_level_index_eu100"]]).reset_index()
    dim_categorie = pd.DataFrame({"category": sorted(d["categories"].category.unique())})
    dim_emplacement = pd.DataFrame({
        "location": ["Rue commerçante 1a (médiane)", "Artère n°1 (flagship)"],
        "rent_source": ["IW 2026, médiane 1a 2024/25", "Cushman & Wakefield 2025, loyer prime"],
    })
    dim_scenario = pd.DataFrame({
        "scenario": ["Pessimiste", "Réaliste", "Optimiste"],
        "revenue_factor": [h["scenario_pessimiste"], 1.0, h["scenario_optimiste"]],
    })
    kar = d["hubs"].loc["Karlsruhe"]
    ram = d["hubs"].loc["Rambouillet"]
    dim_ville = d["villes"].copy()
    dim_ville["distance_karlsruhe_km"] = dim_ville.apply(lambda r: round(haversine_km(r.lat, r.lon, kar.lat, kar.lon) * h["facteur_route"]), axis=1)
    dim_ville["distance_rambouillet_km"] = dim_ville.apply(lambda r: round(haversine_km(r.lat, r.lon, ram.lat, ram.lon) * h["facteur_route"]), axis=1)
    dim_source = d["sources"]

    # --- Fait marché : pays x catégorie
    cat = d["categories"].copy()
    fr_share = cat[cat.country_code == "FR"].set_index("category").share_pct
    cat["penetration_index_vs_fr"] = (cat.share_pct / cat.category.map(fr_share)).round(2)
    fact_marche = cat

    # --- Référence France (base interne simulée)
    b = d["boutiques"]
    store = b.groupby(["store_id", "city"], as_index=False).agg(revenue_ttc=("revenue_ttc_eur", "sum"), surface=("surface_m2", "first"))
    regions = store[store.city != "Paris"]  # Paris surpondère la densité : on prend les boutiques de région comme base
    density_fr = regions.revenue_ttc.sum() / regions.surface.sum()
    b["gm_ht"] = b.revenue_ttc_eur / (1 + prix.loc["FR", "vat_standard_pct"] / 100) * b.gross_margin_rate_ht
    b["ca_ht"] = b.revenue_ttc_eur / (1 + prix.loc["FR", "vat_standard_pct"] / 100)
    gm_rate_fr = b.gm_ht.sum() / b.ca_ht.sum()

    # Dépense par habitant en SOINS DE LA PEAU (le concept ne vend que du soin)
    pop = m25.market_value_bn_eur * 1e9 / m25.spend_per_capita_eur
    skin = d["categories"][d["categories"].category == "Soins de la peau"].set_index("country_code").value_bn_eur * 1e9
    skin_pc = skin / pop
    market_factor = skin_pc["DE"] / skin_pc["FR"]
    price_factor = prix.loc["DE", "price_level_index_eu100"] / prix.loc["FR", "price_level_index_eu100"]
    vat_de = prix.loc["DE", "vat_standard_pct"] / 100

    # --- Fait business case : ville x scénario
    surf = h["surface_boutique_m2"]
    capex = h["capex_amenagement_eur_m2"] * surf + h["capex_appareils_diagnostic_eur"] + h["frais_ouverture_eur"]
    staff = h["etp_par_boutique"] * h["cout_etp_eur"]
    rows = []
    for _, v in dim_ville.iterrows():
      for loc in dim_emplacement.location:
        if loc.startswith("Artère") and pd.isna(v.rent_prime_street_eur_m2_year):
            continue  # pas de loyer prime publié pour cette ville
        for _, s in dim_scenario.iterrows():
            ca_ttc = density_fr * surf * market_factor * price_factor * v.purchasing_power_index / 100 * s.revenue_factor
            ca_ht = ca_ttc / (1 + vat_de)
            gm = ca_ht * gm_rate_fr
            rent = (v.rent_prime_street_eur_m2_year if loc.startswith("Artère") else v.rent_1a_eur_m2_month * 12) * surf
            other = ca_ht * h["autres_charges_pct_ca_ht"] / 100
            logi_pct = h["logistique_pct_ca_ht_base"] + h["logistique_pct_par_100km"] * v.distance_karlsruhe_km / 100
            logi = ca_ht * logi_pct / 100
            ebitda = gm - rent - staff - other - logi
            ramp = [h["montee_en_charge_annee1"], h["montee_en_charge_annee2"], h["montee_en_charge_annee3"]]
            ebitda_3y = sum(gm * r - rent - staff - (other + logi) * r for r in ramp)
            var_rate = gm_rate_fr - h["autres_charges_pct_ca_ht"] / 100 - logi_pct / 100
            breakeven_ht = (rent + staff) / var_rate
            rows.append({
                "city": v.city, "location": loc, "scenario": s.scenario,
                "revenue_ttc_eur": ca_ttc, "revenue_ht_eur": ca_ht, "gross_margin_eur": gm,
                "rent_eur": rent, "staff_eur": staff, "other_costs_eur": other, "logistics_eur": logi,
                "ebitda_eur": ebitda, "ebitda_margin_pct": ebitda / ca_ht * 100,
                "ebitda_3y_eur": ebitda_3y, "capex_eur": capex,
                "payback_years": capex / ebitda if ebitda > 0 else None,
                "breakeven_revenue_ttc_eur": breakeven_ht * (1 + vat_de),
                "rent_pct_ca_ht": rent / ca_ht * 100,
            })
    fact_bc = pd.DataFrame(rows).round(2)

    # --- Sélection des villes pilotes : meilleur EBITDA en scénario réaliste
    base = fact_bc[fact_bc.location == dim_emplacement.location[0]]
    real = base[base.scenario == "Réaliste"].sort_values("ebitda_eur", ascending=False)
    n_pilot = int(h["deploiement_2027"])
    pilots = real.head(n_pilot).city.tolist()
    dim_ville["pilot_rank"] = dim_ville.city.map({c: i + 1 for i, c in enumerate(real.city)})
    dim_ville["is_pilot"] = dim_ville.city.isin(pilots)

    # --- Assortiment
    catal = d["catalogue"]
    eligible_pct = (~catal.france_only).mean() * 100

    # --- Concurrence
    pop_de = m25.loc["DE", "market_value_bn_eur"] * 1e9 / m25.loc["DE", "spend_per_capita_eur"]
    stores_compet = d["concurrents"].stores_de.sum()

    pilot_bc = base[base.city.isin(pilots)]
    flag = fact_bc[(fact_bc.location == dim_emplacement.location[1]) & (fact_bc.scenario == "Réaliste")]
    by_scen = pilot_bc.groupby("scenario").agg(revenue_ttc=("revenue_ttc_eur", "sum"), ebitda=("ebitda_eur", "sum"), ebitda_3y=("ebitda_3y_eur", "sum"), capex=("capex_eur", "sum"))
    kpis = {
        "marche": {
            "de_market_bn": float(m25.loc["DE", "market_value_bn_eur"]), "fr_market_bn": float(m25.loc["FR", "market_value_bn_eur"]),
            "de_growth_pct": float(m25.loc["DE", "growth_pct"]), "fr_growth_pct": float(m25.loc["FR", "growth_pct"]),
            "de_spend_per_capita": float(m25.loc["DE", "spend_per_capita_eur"]), "fr_spend_per_capita": float(m25.loc["FR", "spend_per_capita_eur"]),
            "dm_share_drugstore_pct": 46.8, "drugstore_channel_share_pct": 53.0,
            "pilot_revenue_share_of_market_pct": float(by_scen.loc["Réaliste", "revenue_ttc"] / (m25.loc["DE", "market_value_bn_eur"] * 1e9) * 100),
        },
        "prix": {
            "relative_price_index_de_vs_fr": round(float(price_factor * 100), 1),
            "vat_de": float(prix.loc["DE", "vat_standard_pct"]), "vat_fr": float(prix.loc["FR", "vat_standard_pct"]),
            "gross_margin_rate_fr_pct": round(gm_rate_fr * 100, 1),
            "gross_margin_rate_de_post_tax_pct": round(gm_rate_fr * 100, 1),
            "ht_gain_same_ttc_pct": round(((1 + prix.loc["FR", "vat_standard_pct"] / 100) / (1 + vat_de) - 1) * 100, 2),
        },
        "reseau": {
            "competitor_stores_per_100k": round(float(stores_compet / pop_de * 1e5), 1),
            "rent_min": float(dim_ville.rent_1a_eur_m2_month.min()), "rent_max": float(dim_ville.rent_1a_eur_m2_month.max()),
            "capex_per_store": capex, "pilots": pilots,
        },
        "logistique": {
            "avg_distance_karlsruhe_pilots_km": round(float(dim_ville[dim_ville.is_pilot].distance_karlsruhe_km.mean())),
            "avg_distance_rambouillet_pilots_km": round(float(dim_ville[dim_ville.is_pilot].distance_rambouillet_km.mean())),
            "customs_pct": 0,
        },
        "assortiment": {"catalogue_eligible_pct": round(float(eligible_pct), 1), "nb_sku": int(len(catal))},
        "pilote": {s: {k: round(float(v)) for k, v in by_scen.loc[s].items()} for s in by_scen.index},
        "flagship": {"cities": flag.city.tolist(), "ebitda_by_city": {r.city: round(float(r.ebitda_eur)) for r in flag.itertuples()},
                     "rent_pct_ca_ht": {r.city: round(float(r.rent_pct_ca_ht), 1) for r in flag.itertuples()}},
        "reference_fr": {"density_ttc_m2": round(density_fr), "nb_boutiques": int(h["nb_boutiques_france"])},
    }
    for s in kpis["pilote"]:
        p = kpis["pilote"][s]
        p["payback_years"] = round(p["capex"] / p["ebitda"], 1) if p["ebitda"] > 0 else None

    # --- Plan de déploiement 2027-2031 : 3 -> 8 -> 15 boutiques, montée en charge par cohorte
    order = real.city.tolist()
    n27, n28, n29 = int(h["deploiement_2027"]), int(h["deploiement_2028"]), int(h["deploiement_2029"])
    openings = [(c, 2027) for c in order[:n27]] + [(c, 2028) for c in order[n27:n28]] + [(c, 2029) for c in order[: n29 - n28]]
    ramp = {0: h["montee_en_charge_annee1"], 1: h["montee_en_charge_annee2"]}
    plan_rows = []
    for _, s in dim_scenario.iterrows():
        sb = base[base.scenario == s.scenario].set_index("city")
        cum = 0
        for year in range(2027, 2032):
            ca = gm = cost = ebitda = capex_y = 0
            n_open = 0
            for city, y0 in openings:
                if year < y0:
                    continue
                r = sb.loc[city]
                k = ramp.get(year - y0, 1.0)
                n_open += 1
                e = r.gross_margin_eur * k - r.rent_eur - r.staff_eur - (r.other_costs_eur + r.logistics_eur) * k
                ca += r.revenue_ttc_eur * k
                ebitda += e
                if year == y0:
                    capex_y += r.capex_eur
            cum += ebitda - capex_y
            plan_rows.append({"scenario": s.scenario, "year": year, "stores": n_open, "revenue_ttc_eur": round(ca),
                              "ebitda_eur": round(ebitda), "capex_eur": round(capex_y), "cumulative_cash_eur": round(cum)})
    fact_plan = pd.DataFrame(plan_rows)

    store_kpi = d["boutiques"].groupby("store_id").agg(diag=("diagnostics_per_year", "first"), conv=("diag_conversion_rate", "first"), rep=("repurchase_rate_6m", "first"))
    kpis["boutiques_fr"] = {"diagnostics_per_store": round(float(store_kpi.diag.mean())), "conversion_pct": round(float(store_kpi.conv.mean() * 100), 1),
                            "repurchase_6m_pct": round(float(store_kpi.rep.mean() * 100), 1)}
    kpis["marche"]["skin_per_capita_de"] = round(float(skin_pc["DE"]), 1)
    kpis["marche"]["skin_per_capita_fr"] = round(float(skin_pc["FR"]), 1)
    kpis["marche"]["skin_growth_de_pct"] = 11.1
    kpis["marche"]["skin_growth_fr_pct"] = 2.7
    kpis["plan"] = {s: fact_plan[fact_plan.scenario == s].drop(columns="scenario").to_dict("records") for s in fact_plan.scenario.unique()}
    for s in kpis["plan"]:
        be = next((r["year"] for r in kpis["plan"][s] if r["cumulative_cash_eur"] >= 0), None)
        kpis["plan"][s] = {"years": kpis["plan"][s], "cash_breakeven_year": be}
    kpis["reseau"]["openings"] = [{"city": c, "year": y} for c, y in openings]

    # --- Condition de passage à l'échelle : facteur de CA (vs scénario réaliste) qui rembourse le plan 15 boutiques fin 2031
    sb = base[base.scenario == "Réaliste"].set_index("city")

    def cash_2031(f):
        cum = 0
        for year in range(2027, 2032):
            for city, y0 in openings:
                if year < y0:
                    continue
                r, k = sb.loc[city], ramp.get(year - y0, 1.0)
                cum += r.gross_margin_eur * f * k - r.rent_eur - r.staff_eur - (r.other_costs_eur + r.logistics_eur) * f * k
                cum -= r.capex_eur if year == y0 else 0
        return cum

    lo, hi = 1.0, 3.0
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if cash_2031(mid) >= 0 else (mid, hi)
    pilots_density = sb.loc[pilots].revenue_ttc_eur.mean() / surf
    kpis["condition"] = {
        "revenue_factor_needed": round(hi, 2),
        "density_realistic_ttc_m2": round(float(pilots_density)),
        "density_needed_ttc_m2": round(float(pilots_density * hi), -2),
        "density_fr_regions_ttc_m2": round(float(density_fr)),
    }

    tables = {"dim_pays": dim_pays, "dim_ville": dim_ville, "dim_categorie": dim_categorie, "dim_scenario": dim_scenario, "dim_emplacement": dim_emplacement,
              "dim_source": dim_source, "fact_marche_categorie": fact_marche, "fact_business_case": fact_bc, "fact_plan_deploiement": fact_plan}
    return tables, kpis


def check(t, d):
    """Contrôles de cohérence : le pipeline s'arrête si l'un échoue."""
    bc, villes = t["fact_business_case"], t["dim_ville"]
    tests = {
        "chaque ville x emplacement a 3 scénarios": (bc.groupby(["city", "location"]).size() == 3).all(),
        "clés ville connues": bc.city.isin(villes.city).all(),
        "parts de catégories ≈ 100 % par pays": (t["fact_marche_categorie"].groupby("country_code").share_pct.sum().between(99.5, 100.5)).all(),
        "toutes les sources citées existent": set(";".join(pd.concat([d[k].source_id for k in ["marche", "categories", "villes", "concurrents", "reglementation"]])).split(";")) <= set(d["sources"].source_id),
        "nombre de boutiques France = hypothèse": d["boutiques"].store_id.nunique() == int(d["h"]["nb_boutiques_france"]),
        "plan : 15 boutiques ouvertes en 2029": int(t["fact_plan_deploiement"].query("year == 2029").stores.iloc[0]) == int(d["h"]["deploiement_2029"]),
        "CA pessimiste < réaliste < optimiste": (bc.pivot_table(index=["city", "location"], columns="scenario", values="revenue_ttc_eur").pipe(lambda p: (p["Pessimiste"] < p["Réaliste"]) & (p["Réaliste"] < p["Optimiste"]))).all(),
    }
    failed = [k for k, v in tests.items() if not v]
    if failed:
        raise AssertionError(f"Contrôles en échec : {failed}")
    return {k: True for k in tests}


def main():
    d = load()
    tables, kpis = build(d)
    kpis["controles"] = check(tables, d)
    GOLD.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(GOLD / f"{name}.csv", index=False)
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "kpis.json").write_text(json.dumps(kpis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(kpis, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
