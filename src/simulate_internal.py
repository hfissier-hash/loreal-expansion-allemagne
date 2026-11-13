"""Génère la base interne SIMULÉE : boutiques diagnostic de peau en France et catalogue soin.

Ces données n'existent pas publiquement (L'Oréal ne publie pas le détail de ses
boutiques). Elles sont générées avec une graine fixe pour être reproductibles,
et doivent être remplacées par les vraies données internes.
Commande : python -m src.simulate_internal
"""
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "interne"
rng = np.random.default_rng(2027)

VILLES = {"Paris": 6, "Lyon": 2, "Marseille": 2, "Bordeaux": 2, "Lille": 2,
          "Toulouse": 2, "Nice": 1, "Nantes": 1, "Strasbourg": 1, "Montpellier": 1}
# Ventes par marque de soin (la boutique ne vend que des soins de la peau)
MIX = {"La Roche-Posay": 0.26, "CeraVe": 0.22, "Vichy": 0.16, "SkinCeuticals": 0.14,
       "Kiehl's": 0.12, "Lancôme Skincare": 0.10}
# Le concept garde 5 marques (décision d'équipe du 13/11/2026). Les tirages aléatoires gardent
# les 6 marques d'origine pour ne changer aucun autre chiffre simulé ; Lancôme est retiré ensuite
# et son CA réparti sur les 5 marques au prorata (CA par boutique inchangé).
EXCLUDED_BRANDS = {"Lancôme Skincare"}


def boutiques():
    rows, i = [], 1
    for ville, n in VILLES.items():
        for _ in range(n):
            surface = float(np.clip(rng.normal(90, 12), 65, 120))
            densite = rng.normal(8500, 800) * (1.2 if ville == "Paris" else 1.0)  # CA TTC / m² / an
            ca_ttc = surface * densite
            diagnostics = int(rng.normal(5200, 600) * surface / 90)  # diagnostics de peau réalisés par an
            conversion = float(np.clip(rng.normal(0.62, 0.05), 0.45, 0.8))  # part des diagnostics suivis d'un achat
            rachat = float(np.clip(rng.normal(0.41, 0.06), 0.25, 0.6))  # part des clients revenus sous 6 mois
            for brand, part in MIX.items():
                rows.append({
                    "store_id": f"FR{i:03d}", "city": ville, "surface_m2": round(surface),
                    "brand": brand, "category": "Soins de la peau",
                    "revenue_ttc_eur": round(ca_ttc * part * rng.normal(1, 0.06), 2),
                    "gross_margin_rate_ht": round(float(np.clip(rng.normal(0.70, 0.03), 0.62, 0.78)), 3),
                    "diagnostics_per_year": diagnostics, "diag_conversion_rate": round(conversion, 3),
                    "repurchase_rate_6m": round(rachat, 3), "year": 2025,
                })
            i += 1
    df = pd.DataFrame(rows)
    excluded = df["brand"].isin(EXCLUDED_BRANDS)
    removed = df[excluded].groupby("store_id")["revenue_ttc_eur"].sum()
    df = df[~excluded].copy()
    kept = df.groupby("store_id")["revenue_ttc_eur"].transform("sum")
    df["revenue_ttc_eur"] = (df["revenue_ttc_eur"] * (1 + df["store_id"].map(removed) / kept)).round(2)
    return df.reset_index(drop=True)


def catalogue():
    rows = []
    for k in range(480):
        brand = rng.choice(list(MIX), p=list(MIX.values()))
        rows.append({
            "sku": f"SKU{k + 1:05d}", "brand": brand, "category": "Soins de la peau",
            # gammes exclusivement françaises (packaging non traduisible, licences locales)
            "france_only": bool(rng.random() < 0.06),
        })
    df = pd.DataFrame(rows)
    return df[~df["brand"].isin(EXCLUDED_BRANDS)].reset_index(drop=True)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    boutiques().to_csv(OUT / "boutiques_france.csv", index=False)
    catalogue().to_csv(OUT / "catalogue_france.csv", index=False)
    print("Base interne simulée écrite dans", OUT)
