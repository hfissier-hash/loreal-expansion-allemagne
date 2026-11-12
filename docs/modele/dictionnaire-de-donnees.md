# Dictionnaire de données de l'entrepôt

Tables construites par `src/build_warehouse.py` dans `data/warehouse/`. Schéma : `sql/schema.sql` ; choix du modèle : [`schema.md`](schema.md). Les tables de restitution `data/gold/` sont décrites dans le README (§ 2).

## 1. Termes métier

| Terme | Définition retenue |
|---|---|
| Boutique pilote | Boutique L'Oréal de diagnostic de peau en France (FR001 à FR020). **Fictive** : ses données sont simulées (consigne : « bases internes simulées »). |
| Boutique projet | Boutique prévue en Allemagne (DE01 à DE03 en 2027 : München, Düsseldorf, Frankfurt am Main). Pas d'activité, seulement des attributs d'implantation. |
| Diagnostic | Analyse de peau d'environ 20 minutes en boutique : type de peau, besoin principal, soins recommandés. |
| Conversion | Un diagnostic est converti s'il est suivi d'un achat le jour même. |
| Rachat | Nouvel achat d'une cliente convertie, sans nouveau diagnostic. « Revenue sous 6 mois » = premier rachat dans les 180 jours. |
| Achat sans diagnostic | Achat d'un client de passage, non identifié (clé client 0). |
| Ville cible | Ville allemande de la vague 2027. Les 5 autres villes allemandes servent de comparaison. |
| Rue 1a | Rue commerçante de premier rang (IW Köln), loyer médian en €/m²/mois. |
| Artère n°1 | Rue la plus chère de la ville (Cushman & Wakefield), loyer publié en €/m²/an. |
| Scénario | Pessimiste (CA × 0,80), réaliste (× 1,00), optimiste (× 1,15). |
| Drogerie | Chaîne de type dm ou Rossmann, premier canal de vente des cosmétiques en Allemagne (53 % en 2025, IKW). |

## 2. Règles de gestion

1. **Traçabilité** : chaque donnée externe garde `source_ids` (identifiants de `dim_source`, séparés par `;`) et son `status` de collecte. Une valeur absente reste vide, jamais estimée en silence.
2. **Données simulées signalées** : `is_simulated = 1` sur les boutiques pilotes et les produits, source `INTERNE`. Graines fixes (`2027`) : la base se régénère à l'identique.
3. **Calage du détail sur les agrégats** : pour chaque boutique, le nombre de diagnostics, le taux de conversion, le taux de rachat sous 6 mois et le CA TTC par marque de `boutiques_france.csv` sont respectés. Les achats sans diagnostic complètent le CA de chaque marque jusqu'à la cible (écart contrôlé : moins de 0,5 %).
4. **Montants de vente** : `revenue_ttc = quantity × unit_price_ttc` ; `revenue_ht = revenue_ttc / 1,20` ; `gross_margin_ht = revenue_ht × taux de marge` de la boutique et de la marque ; `cogs_ht = revenue_ht − gross_margin_ht`.
5. **Loyers en €/m²/mois** : un loyer publié en €/m²/an est divisé par 12 ; valeur et unité d'origine conservées (`rent_raw`, `unit_raw`).
6. **Emplacements conformes** : les libellés des sources (« Rue commerçante 1a », « Rue commerçante 1a (médiane) ») sont ramenés à un code unique (`rue_1a`, `artere_n1`).
7. **Prix relevés** : `price_ht = price_ttc / (1 + TVA du pays)`, TVA lue dans `dim_country` (19 % DE, 20 % FR).
8. **Densité concurrentielle** : si la collecte OSM ne la fournit pas, `stores_per_100k = store_count / population × 100 000`.
9. **Distance aux hubs** : vol d'oiseau (haversine) entre l'usine et le centre-ville ; distance routière estimée = vol d'oiseau × `facteur_route` (1,25, `hypotheses.csv`).
10. **Catégories conformes** : tout le catalogue relève de « Soins de la peau », ce qui relie les ventes internes au marché par `dim_category`. La clé 0 « Total marché » porte les totaux pays.
11. **Boutiques fermées le dimanche** : aucune activité simulée ce jour-là.
12. **Éligibilité au marché allemand** : `eligible_de = 0` pour les gammes réservées à la France (`france_only`).

## 3. Dimensions

| Table | Grain | Colonnes principales |
|---|---|---|
| dim_date | un jour, 2024 à 2031 | date_key (AAAAMMJJ), year, quarter, month, month_name, iso_week, weekday (1 = lundi), is_weekend |
| dim_country | un pays ou une zone | country_code, country_name, geo_level (`pays` : DE, FR ; `zone` : EU, GLOBAL, pour les panels), vat_standard_pct, customs_duty_intra_eu_pct, price_level_index_eu100 |
| dim_city | une ville | city_name, region, country_code, city_role (`cible_2027`, `comparaison_de`, `pilote_fr`), population, purchasing_power_eur_per_capita, purchasing_power_index, lat, lon |
| dim_location | un type d'emplacement | location_code (`rue_1a`, `artere_n1`), location_name |
| dim_scenario | un scénario | scenario_name, revenue_factor |
| dim_store | une boutique | store_code, city_key, store_status (`pilote_fr`, `projet_de`), surface_m2, opening_year, is_simulated |
| dim_category | une catégorie Cosmetics Europe | category_name (0 = Total marché) |
| dim_product | une référence du catalogue | sku, brand, category_key, skin_concern, list_price_fr_ttc (simulé), eligible_de |
| dim_customer | une cliente identifiée | customer_code, gender, age_band, skin_type, home_store_key, first_visit_date_key, loyalty_member, returned_6m (0 = client de passage) |
| dim_retailer | une enseigne concurrente | retailer_name, segment, stores_de, revenue_bn_eur, revenue_scope |
| dim_hub | un site logistique L'Oréal | hub_name (Karlsruhe, Rambouillet, La Roche-Posay, Vichy), country_code, hub_type, lat, lon |
| dim_source | une source | source_id, source_name, publisher, url, source_type, reliability |

## 4. Faits

| Table | Grain | Mesures |
|---|---|---|
| fact_diagnostic | un diagnostic | duration_min, nb_products_recommended, converted ; skin_type_detected, main_concern |
| fact_sales | une ligne de ticket | quantity, unit_price_ttc, revenue_ttc, revenue_ht, cogs_ht, gross_margin_ht ; sale_type (`apres_diagnostic`, `rachat`, `sans_diagnostic`) |
| fact_market | pays × année × catégorie | value_bn_eur, share_pct, growth_pct, spend_per_capita_eur |
| fact_market_share | pays × périmètre × acteur × année | market_share_pct |
| fact_market_indicator | source × zone × périmètre × indicateur × période | value, unit (indicateurs hétérogènes des panels NielsenIQ, Circana, IKW : croissance, taille, part) |
| fact_competition | ville × enseigne | store_count, stores_per_100k |
| fact_rent | ville × emplacement | rent_eur_m2_month, trend_pct_pa |
| fact_price | produit relevé × pays × enseigne | price_ttc, price_ht |
| fact_hub_distance | hub × ville | distance_km_vol_oiseau, distance_km_route_estimee |
| fact_business_case | ville × emplacement × scénario | revenue_ttc_eur, revenue_ht_eur, gross_margin_eur, rent_eur, staff_eur, other_costs_eur, logistics_eur, ebitda_eur, ebitda_margin_pct, capex_eur, payback_years, breakeven_revenue_ttc_eur |
| fact_deployment_plan | scénario × année | stores, revenue_ttc_eur, ebitda_eur, capex_eur, cumulative_cash_eur |
| ref_hypotheses | une hypothèse | value, unit, rationale (hors étoile) |
| ref_reglementation | un sujet réglementaire | texte France / Allemagne / impact (hors étoile) |

## 5. KPIs de la consigne et tables qui les portent

| Axe | KPI | Calcul dans l'entrepôt |
|---|---|---|
| Marché & potentiel | Croissance annuelle du secteur | `fact_market.growth_pct` (DE, total ou Soins de la peau) |
| | Part de marché d'un concurrent | `fact_market_share` (dm : 46,8 % des drogeries) |
| | Tendances des panels (prestige, milieu de gamme, e-commerce) | `fact_market_indicator` filtré par `scope` et `metric` |
| Prix & marges | Indice prix relatif DE / FR | relevé `releve_prix_soins.csv` : moyenne par marque du ratio des prix au litre (prix public conseillé FR), pondérée par le CA des pilotes ; repli sur `dim_country.price_level_index_eu100` si le relevé est vide |
| | Marge brute post-taxe | `SUM(gross_margin_ht) / SUM(revenue_ht)` sur `fact_sales`, ou `fact_business_case` |
| Réseau & implantation | Densité concurrentielle | `fact_competition.stores_per_100k` par ville cible |
| | Coût moyen au m² | `fact_rent.rent_eur_m2_month` par ville et emplacement |
| Opérations & logistique | Distance moyenne aux hubs | `AVG(fact_hub_distance.distance_km_route_estimee)`, Karlsruhe → villes cibles |
| | Douane et taxes | `dim_country`, `ref_reglementation` |
| Assortiment | Pénétration des catégories | `fact_market.share_pct` DE vs FR |
| | % du catalogue éligible | `AVG(dim_product.eligible_de)` |
| Pilotes (interne) | Conversion, rachat, CA par m², part du CA après diagnostic | `fact_diagnostic`, `fact_sales`, `dim_store.surface_m2`, `dim_customer.returned_6m` |
| Rentabilité | EBITDA, payback, trésorerie cumulée | `fact_business_case`, `fact_deployment_plan` |
