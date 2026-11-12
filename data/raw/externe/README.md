# Données externes collectées

Une table par sujet, au format CSV (séparateur virgule, UTF-8). Chaque ligne indique sa source (`source_id`, détaillée dans `../sources.csv`) et sa date de collecte (`collected_at`). La colonne `status` signale ce qui reste à collecter.

| Fichier | Grain (1 ligne =) | Contenu | Source | Collecte |
|---|---|---|---|---|
| `marche_pays.csv` | pays × année | Valeur du marché beauté, croissance, dépense par habitant (colonne `note` : utiliser la croissance publiée, pas celle recalculée avec l'édition 2024) | Cosmetics Europe | Manuelle |
| `categories_pays.csv` | pays × catégorie | Valeur, part et croissance de chaque catégorie (dont soins de la peau) | Cosmetics Europe | Manuelle |
| `parts_de_marche.csv` | pays × acteur | Parts de marché des drogeries et des canaux de vente | Handelsdaten, IKW | Manuelle |
| `concurrents_nationaux.csv` | enseigne | Nombre de magasins en Allemagne et chiffre d'affaires | Sonko Consulting, Douglas (486 magasins sur Allemagne, Autriche, Suisse, Pays-Bas) | Manuelle |
| `panels_marche.csv` | source × pays × indicateur | Chiffres publics des panels NielsenIQ et Circana (beauté prestige, soin, e-commerce) + bilan IKW 2025 | Circana, NIQ, IKW | Manuelle (publications gratuites ; données détaillées payantes) |
| `concurrents_villes.csv` | ville × enseigne | Nombre de magasins par ville et densité pour 100 000 habitants | OpenStreetMap | Script `src/collect/collect_osm.py` (5 villes mesurées, 3 estimées : colonne `status`) |
| `villes_de.csv` | ville | Population, pouvoir d'achat, coordonnées | Destatis, NIQ-GfK | Manuelle (population officielle au 31/12/2025) |
| `loyers_villes.csv` | ville × emplacement | Loyer commercial en rue 1a et sur l'artère n°1 | IW Köln (rue 1a), BNP Paribas Real Estate (artère n°1, 8 villes) | Manuelle |
| `prix_taxes.csv` | pays | Niveau des prix (UE = 100), TVA, droits de douane | Eurostat, législations | Manuelle (script Eurostat possible) |
| `releve_prix_soins.csv` | produit | Prix de 6 soins L'Oréal en Allemagne et en France, prix au litre et ratio DE/FR (prix pratiqué et prix public conseillé FR) | dm.de, redcare-pharmacie.fr, kiehls.de/.fr | Relevé manuel le 12/11/2026 |
| `hubs_loreal.csv` | site | Usines L'Oréal : Karlsruhe (DE), Rambouillet, La Roche-Posay et Vichy (FR, dermocosmétique) | Rapports annuels et site L'Oréal | Manuelle |
| `reglementation.csv` | sujet | Douane, TVA, règlement cosmétique, étiquetage, emballages | UE, IHK | Manuelle |

**Unités** : montants en euros ; loyers en €/m²/mois (rue 1a) ou €/m²/an (artère n°1), indiqué dans la colonne `unit` ; parts et croissances en %.
