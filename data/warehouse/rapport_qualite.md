# Rapport qualité de l'entrepôt

Généré par `src/build_warehouse.py`, ne pas modifier à la main.

## Volumes

| Table | Lignes |
|---|---|
| dim_date | 2 922 |
| dim_country | 4 |
| dim_city | 18 |
| dim_location | 2 |
| dim_scenario | 3 |
| dim_store | 23 |
| dim_category | 6 |
| dim_product | 480 |
| dim_customer | 105 026 |
| dim_retailer | 8 |
| dim_hub | 4 |
| dim_source | 28 |
| fact_diagnostic | 105 025 |
| fact_sales | 571 987 |
| fact_market | 14 |
| fact_market_share | 7 |
| fact_market_indicator | 16 |
| fact_competition | 56 |
| fact_rent | 16 |
| fact_price | 12 |
| fact_hub_distance | 72 |
| fact_business_case | 48 |
| fact_deployment_plan | 15 |
| ref_hypotheses | 19 |
| ref_reglementation | 5 |

## Contrôles

- Clés étrangères orphelines : 0
- Écart maximal entre le CA détaillé et le CA agrégé de boutiques_france.csv : 0.02 %
- Ventes « après diagnostic » sans diagnostic converti : 0
- Ventes un dimanche : 0

## Données encore manquantes

- `parts_de_marche.csv` : 3 ligne(s) « à collecter (payant) »

## Repères de la base interne simulée (2025)

- Diagnostics : 105 025 ; conversion 60.6 % ; rachat sous 6 mois 42.5 % des clientes converties
- CA TTC : 16.14 M€, soit 807 k€ par boutique
- Part du CA « sans_diagnostic » : 65.6 %
- Part du CA « apres_diagnostic » : 26.7 %
- Part du CA « rachat » : 7.7 %
