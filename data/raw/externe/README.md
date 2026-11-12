# Données externes collectées

Une table par sujet, au format CSV (séparateur virgule, UTF-8). Chaque ligne indique sa source (`source_id`, détaillée dans `../sources.csv`) et sa date de collecte (`collected_at`). La colonne `status` signale ce qui reste à collecter.

| Fichier | Grain (1 ligne =) | Contenu | Source | Collecte |
|---|---|---|---|---|
| `marche_pays.csv` | pays × année | Valeur du marché beauté, croissance, dépense par habitant | Cosmetics Europe | Manuelle |
| `categories_pays.csv` | pays × catégorie | Valeur, part et croissance de chaque catégorie (dont soins de la peau) | Cosmetics Europe | Manuelle |
| `parts_de_marche.csv` | pays × acteur | Parts de marché des drogeries et des canaux de vente | Handelsdaten, IKW | Manuelle |
| `concurrents_nationaux.csv` | enseigne | Nombre de magasins en Allemagne et chiffre d'affaires | Sonko Consulting, Douglas | Manuelle |
| `concurrents_villes.csv` | ville × enseigne | Nombre de magasins par ville et densité pour 100 000 habitants | OpenStreetMap | **Script, à faire** |
| `villes_de.csv` | ville | Population, pouvoir d'achat, coordonnées | Destatis, NIQ-GfK | Manuelle (population : script à faire) |
| `loyers_villes.csv` | ville × emplacement | Loyer commercial en rue 1a et sur l'artère n°1 | IW Köln, Cushman & Wakefield | Manuelle |
| `prix_taxes.csv` | pays | Niveau des prix (UE = 100), TVA, droits de douane | Eurostat, législations | Manuelle (script Eurostat possible) |
| `releve_prix_soins.csv` | produit | Prix de 6 soins L'Oréal en Allemagne et en France | dm.de, site français | **Relevé manuel, optionnel** |
| `hubs_loreal.csv` | site | Usines L'Oréal de référence et coordonnées | Rapports annuels L'Oréal | Manuelle |
| `reglementation.csv` | sujet | Douane, TVA, règlement cosmétique, étiquetage, emballages | UE, IHK | Manuelle |

**Unités** : montants en euros ; loyers en €/m²/mois (rue 1a) ou €/m²/an (artère n°1), indiqué dans la colonne `unit` ; parts et croissances en %.
